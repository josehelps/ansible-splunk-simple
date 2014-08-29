# Copyright 2011 Splunk, Inc.                                                                       
#                                                                                                        
#   Licensed under the Apache License, Version 2.0 (the "License");                                      
#   you may not use this file except in compliance with the License.                                     
#   You may obtain a copy of the License at                                                              
#                                                                                                        
#       http://www.apache.org/licenses/LICENSE-2.0                                                       
#                                                                                                        
#   Unless required by applicable law or agreed to in writing, software                                  
#   distributed under the License is distributed on an "AS IS" BASIS,                                    
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.                             
#   See the License for the specific language governing permissions and                                  
#   limitations under the License.    

from distutils.version import LooseVersion
import logging
import os
import sys

import cherrypy

import splunk
import splunk.auth as auth
import splunk.entity as entity
from splunk.util import normalizeBoolean as normBool 
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util

from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.models.app import App

logger = logging.getLogger('splunk.ta_nix_setup')

dir = os.path.join(util.get_apps_dir(), __file__.split('.')[-2], 'bin')
if not dir in sys.path:
    sys.path.append(dir)
    
from ta_unix.models.input import MonitorInput, ScriptedInput
from ta_unix.decorators import host_app

class TAUnixSetup(controllers.BaseController):
    '''TA Unix Setup Controller'''
 
    @route('/:app/:action=setup')
    @expose_page(must_login=True, methods=['GET']) 
    @host_app
    def setup(self, app, action, host_app=None, **kwargs):
        ''' show the setup page '''

        user = cherrypy.session['user']['name'] 
        
        if not self.is_app_admin(host_app, user):
            raise cherrypy.HTTPRedirect(self._redirect(host_app, app, 'unauthorized'))

        mon = MonitorInput.all()
        mon = mon.filter_by_app(app)
  
        scripted = ScriptedInput.all()
        scripted = scripted.filter_by_app(app)
        
        system = (not(sys.platform.startswith('win')))
   
        return self.render_template('/%s:/templates/setup_show.html' % host_app, 
                                    dict(system=system, mon=mon, scripted=scripted, app=app))

    @route('/:app/:action=success')
    @expose_page(must_login=True, methods=['GET']) 
    @host_app
    def success(self, app, action, host_app=None, **kwargs):
        ''' render the success page '''

        return self.render_template('/%s:/templates/setup_success.html' \
                                    % host_app,
                                    dict(app=app))

    @route('/:app/:action=failure')
    @expose_page(must_login=True, methods=['GET']) 
    @host_app
    def failure(self, app, action, host_app=None, **kwargs):
        ''' render the failure page '''

        return self.render_template('/%s:/templates/setup_failure.html' \
                                    % host_app,
                                    dict(app=app))

    @route('/:app/:action=unauthorized')
    @expose_page(must_login=True, methods=['GET'])
    @host_app
    def unauthorized(self, app, action, host_app=None, **kwargs):
        ''' render the unauthorized page '''

        return self.render_template('/%s:/templates/setup_403.html' \
                                    % host_app,
                                    dict(app=app))

    @route('/:app/:action=save')
    @expose_page(must_login=True, methods=['POST'])
    @host_app
    def save(self, app, action, host_app=None, **params):
        ''' save the posted setup content '''

        user = cherrypy.session['user']['name'] 

        mon = MonitorInput.all()
        mon = mon.filter_by_app(app)
  
        scripted = ScriptedInput.all()
        scripted = scripted.filter_by_app(app)
            
        for m in mon:
            disabled = normBool(params.get(m.name + '.disabled'))
            if disabled:
                m.disable()
            else:
                m.enable()
            m.share_global()

        for s in scripted:
            disabled = normBool(params.get(s.name + '.disabled'))
            if disabled:
                s.disable()
            else:
                s.enable()
            s.share_global()
            interval = params.get(s.name + '.interval')
            if interval:
                s.interval = interval
                try:
                    if not s.passive_save():
                        logger.error(m.errors)
                        return self.render_template(
                            '/%s:/templates/setup_show.html' \
                                % host_app,
                            dict(app=app, 
                                 errors=s,
                                 scripted=scripted, 
                                 mon=mon)
                        )
                except splunk.AuthorizationFailed:
                    raise cherrypy.HTTPRedirect(self._redirect(host_app, app, 'unauthorized'))
                except Exception, ex:
                    logger.info(ex)
                    raise cherrypy.HTTPRedirect(self._redirect(host_app, app, 'failure'))

        logger.debug('Splunk Version = %s' % self._get_version())
        if self._get_version() <= LooseVersion('4.2.2'):
            import splunk.bundle as bundle
            temp_app = bundle.getConf('app', namespace=host_app, owner='nobody') 
            temp_app['install']['is_configured'] = 'true'
        else:
            this_app = App.get(App.build_id(host_app, host_app, user))
            this_app.is_configured = True
            this_app.passive_save()

        logger.info('%s - App setup successful' % host_app)

        raise cherrypy.HTTPRedirect(self._redirect(host_app, app, 'success'))

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
        
    def _redirect(self, host_app, app, endpoint):
        return self.make_url(['custom', host_app, 'taunixsetup', app, endpoint])

    def _get_version(self):
        try:
            return LooseVersion(entity.getEntity('server/info', 'server-info')['version'])
        except:
            return LooseVersion('0.0')
