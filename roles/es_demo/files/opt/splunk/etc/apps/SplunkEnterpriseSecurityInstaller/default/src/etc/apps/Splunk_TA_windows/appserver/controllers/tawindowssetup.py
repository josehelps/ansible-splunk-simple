from distutils.version import LooseVersion
import logging
import os
import sys

import cherrypy

import splunk
import splunk.auth as auth
import splunk.entity as entity
import splunk.bundle as bundle
from splunk.util import normalizeBoolean as normBool 
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util

from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.models.app import App

from ta_windows.models.input import MonitorInput, WinEventLogInput, EventLogCannon

logger = logging.getLogger('splunk.ta_windows_setup')

class TAWindowsSetup(controllers.BaseController):
    '''TA Windows Setup Controller'''
 
    @route('/:app/:action=setup')
    @expose_page(must_login=True, methods=['GET']) 
    def setup(self, app, action, **kwargs):
        ''' show the setup page '''

        host_app = cherrypy.request.path_info.split('/')[3]
        user = cherrypy.session['user']['name'] 
        
        if not self.is_app_admin(host_app, user):
            raise cherrypy.HTTPRedirect(self._redirect(host_app, app, 'unauthorized'))

        mon = MonitorInput.all()
        mon = mon.filter_by_app(app)

        cannon = EventLogCannon.all()
        cannon = cannon.order_by('importance', sort_dir='asc')

        win = WinEventLogInput.all()
        win = win.search('name=localhost')

        system = (sys.platform.startswith("win"))
        optimize = bool(self.get_distsearch(host_app))

        return self.render_template('/%s:/templates/setup_show.html' % host_app, 
                                    dict(system=system, mon=mon, win=win, cannon=cannon, optimize=optimize, app=app))

    @route('/:app/:action=success')
    @expose_page(must_login=True, methods=['GET']) 
    def success(self, app, action, **kwargs):
        ''' render the success page '''

        host_app = cherrypy.request.path_info.split('/')[3]
        return self.render_template('/%s:/templates/setup_success.html' \
                                    % host_app,
                                    dict(app=app))

    @route('/:app/:action=failure')
    @expose_page(must_login=True, methods=['GET']) 
    def failure(self, app, action, **kwargs):
        ''' render the failure page '''

        host_app = cherrypy.request.path_info.split('/')[3]
        return self.render_template('/%s:/templates/setup_failure.html' \
                                    % host_app,
                                    dict(app=app))

    @route('/:app/:action=unauthorized')
    @expose_page(must_login=True, methods=['GET']) 
    def unauthorized(self, app, action, **kwargs):
        ''' render the unauthorized page '''

        host_app = cherrypy.request.path_info.split('/')[3]
        return self.render_template('/%s:/templates/setup_403.html' \
                                    % host_app,
                                    dict(app=app))

    @route('/:app/:action=save')
    @expose_page(must_login=True, methods=['POST']) 
    def save(self, app, action, **params):
        ''' save the posted setup content '''

        host_app = cherrypy.request.path_info.split('/')[3]
        user = cherrypy.session['user']['name'] 

        win = WinEventLogInput.get(WinEventLogInput.build_id('localhost', host_app, user))
        evt_logs = params.get('winevtlogs')

	if evt_logs:

            win.logs = evt_logs 

	    if normBool(win.disabled):
                win.enable()
	    try:
	        win.edit()
            except Exception, ex:
                logger.exception(ex)
	        raise cherrypy.HTTPRedirect(self._redirect(host_app, app, 'failure'))
	else:
            win.disable()

        mon = MonitorInput.all()
        mon = mon.filter_by_app(app)
  
        for m in mon:
            disabled = normBool(params.get(m.name + '.disabled'))
            if disabled:
                m.disable()
            else:
                m.enable()
            m.share_global()

        self.update_distsearch(host_app, normBool(params.get('optimize_dist_search')))

        logger.debug('Splunk Version = %s' % self._get_version())
        if self._get_version() <= LooseVersion('4.2.2'):
            temp_app = bundle.getConf('app', namespace=host_app, owner='nobody') 
            temp_app['install']['is_configured'] = 'true'
        else:
            this_app = App.get(App.build_id(host_app, host_app, user))
            this_app.is_configured = True 
            this_app.passive_save()

        logger.info('%s - App setup successful' % host_app)

        raise cherrypy.HTTPRedirect(self._redirect(host_app, app, 'success'))

    def get_distsearch(self, host_app):
        return bundle.getConf('distsearch', 
                               namespace=host_app, 
                               owner='nobody')['replicationBlacklist']['nontsyslogmappings'] 

    def is_app_admin(self, app_name, user):
        ''' 
        used to determine app administrator membership
        necessary because splunkd auth does not advertise inherited roles
        '''
        
        sub_roles = []
        app = App.get(App.build_id(app_name, app_name, user)) 
        admin_list = app.entity['eai:acl']['perms']['write'] 

        if '*' in admin_list:
            return True
        for role in auth.getUser(name=user)['roles']:
            if role in admin_list: 
                return True
            sub_roles.append(role)
        for role in sub_roles:
            for irole in auth.getRole(name=role)['imported_roles']:
                if irole in admin_list: 
                    return True
        return False
        
    def update_distsearch(self, host_app, enabled):
        temp = bundle.getConf('distsearch', namespace=host_app, owner='nobody') 
        if enabled:
            temp['replicationBlacklist']['nontsyslogmappings'] = os.path.join('apps', host_app, 
                                                                     'lookups', 'ntsyslog_mappings.csv')
        else:
            temp['replicationBlacklist']['nontsyslogmappings'] = ''

           
    def _redirect(self, host_app, app, endpoint):
        return self.make_url(['custom', host_app, 'tawindowssetup', app, endpoint])

    def _get_version(self):
        try:
            return LooseVersion(entity.getEntity('server/info', 'server-info')['version'])
        except:
            return LooseVersion('0.0')
