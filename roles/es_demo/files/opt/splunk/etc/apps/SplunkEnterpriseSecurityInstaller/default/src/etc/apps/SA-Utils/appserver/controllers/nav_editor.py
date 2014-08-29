import cgi
import logging
import json
import os
import sys
import re

import cherrypy
import mako

import splunk
import splunk.util
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
import splunk.entity as entity
import splunk.auth as auth

from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

logger = logging.getLogger('splunk')
TEMPLATE_ERROR = 'An error occurred while rendering the page template.  See web_service.log for more details'

from models.navs import Nav

try:
    import xml.etree.cElementTree as ET
except:
    import xml.etree.ElementTree as ET

class NavEditor(controllers.BaseController):
    '''Nav Editor Controller '''

    # The list below defines the capabilities that will be checked for particular applications.
    # Hard-coding these is necessary because the permissions defined cannot be defined as 
    # arguments to the module in the view since these are only communicated to the python
    # code through the browser; this means that the users could manipulate them to change
    # which permissions are checked.
    CAPABILITIES_TO_CHECK = {
                                'SplunkEnterpriseSecuritySuite' : ['edit_es_navigation'],
                                'SplunkPCIComplianceSuite' : ['edit_pci_navigation']
                             }
    
    # By default, the following capabilities will be checked
    DEFAULT_CAPABILITIES_TO_CHECK = ['edit_navigation']

    @staticmethod
    def hasCapabilitiesByApp( user, session_key, app ):
        """
        Determine if the user has the capabilities. Which capabilities are to be checked will be checked is 
        determined based on what app is requesting the check. See NavEditor.CAPABILITIES_TO_CHECK
        
        Arguments:
        user -- The user to be checked
        session_key -- The session to use when checking permissions
        app -- The app whose navigation is to be updated
        """
        
        required_capabilities = NavEditor.DEFAULT_CAPABILITIES_TO_CHECK
        
        # Get the app specific capabilities to check
        if app in NavEditor.CAPABILITIES_TO_CHECK:
            required_capabilities = NavEditor.CAPABILITIES_TO_CHECK[app]
        
        logger.info(required_capabilities)
        # Check the capabilities
        return NavEditor.hasCapabilities( user, session_key, required_capabilities)
    
    @staticmethod
    def hasCapabilities( user, session_key, required_capabilities ):
        """
        Determine if the user has the capabilities.
        
        Arguments:
        user -- The user to be checked
        session_key -- The session to use when checking permissions
        required_capabilities -- The list of capabilities that that user must have
        """
        
        roles = []
        capabilities = []
        
        # Default to 'admin_all_objects'
        if required_capabilities is None:
            required_capabilities = ["admin_all_objects"]
        
        # Get the user entity info
        user_entity = entity.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
    
        # Find the user information
        for stanza, settings in user_entity.items():
            
            if stanza == user:
                
                # Find the roles information
                for key, val in settings.items():
                    if key == 'roles':
                        roles = val
             
        # Get capabilities
        for role in roles:
            
            role_entity = entity.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
            
            # Get the imported capabilities
            for stanza, settings in role_entity.items():
                
                # Populate the list of capabilities
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            capabilities.extend(val)
                            
            
        # Make sure the user has the required_capabilities
        for capability in required_capabilities:
            
            # Indicate that the user does not have permission if they do not have a given capability
            if capability not in capabilities:
                return False
            
        # All capabilities matched, return true indicating that they have permission
        return True

    @route('/:app/:action=render')
    @expose_page(must_login=True, methods=['GET']) 
    def render(self, app, action, **kwargs):
        ''' render workspace '''
        user = auth.getCurrentUser()['name']
        session_key  = cherrypy.session['sessionKey']
        host_app = cherrypy.request.path_info.split('/')[3]

        if NavEditor.hasCapabilitiesByApp( user, session_key, app) == True:
            return self.render_template('/%s:/templates/nav_editor.html' % host_app, template_args=dict(host_app=host_app, app=app))
        else:
            return self.render_template('/%s:/templates/nav_editor_denied.html' % host_app)

    @route(':app/:action=create_nav')
    @expose_page(must_login=True, methods=['POST'])
    def create_nav(self, app, action, **params):
        ''' create new nav '''

        user = cherrypy.session['user']['name']
        host_app = cherrypy.request.path_info.split('/')[3]
        name = params.get('name')

        logger.info("Creating new nav %s in app %s" % (name, app))

        nav = Nav(app, user, name)
        nav.data = params.get('data')

        if not nav.passive_save():
            logger.error('error saving nav %s: %s' % (name, nav.errors[0]))
            return self.render_json({
                'success': 'false',
                'error': nav.errors[0]
            })

        return self.render_json({'success': 'true'})

    @route('/:app/:action=update_nav')
    @expose_page(must_login=True, methods=['POST'])
    def update_nav(self, app, action, **params):
        ''' update nav '''
        logger.info("update nav")
        user = cherrypy.session['user']['name']
        host_app = cherrypy.request.path_info.split('/')[3]
        name = params.get('name')
        validate = self.validateInputs(params.get('data'))

        if validate.get('success') == "false":
            return self.render_json(validate)

        try:
            nav = Nav.get(Nav.build_id(name, app, user))
        except Exception, ex:
            logger.debug(ex)
            logger.warn('problem retrieving nav %s' % name)
            return self.render_json({'success': 'false', 'error': 'problem in getting the nav.'})

        logger.info("nav: %s" % nav)
        nav.update(params)
        
        if not nav.passive_save():
            logger.error('error updating nav %s: %s' % (name, nav.errors[0]))
            return self.render_json({'success': 'false', 'error': nav.errors[0]})

        return self.render_json({'success': 'true'})

    def validateInputs(self, data):
        doc = ET.fromstring(data)
        regex = re.compile("[A-Za-z0-9 _-]+$")
        for c in doc.iter('collection'):
            label = c.get('label')
            if not label or len(label) > 256:
                error = "collection labels must be non-empty and less than 256 characters."
                return {'success': 'false', 'error': error}
            elif not regex.match(label):
                error = "collection labels are limited to alphanumeric and underscore characters." 
                return {'success': 'false', 'error': error}
        for a in doc.iter('a'):
            href = a.get('href')
            text = a.text
            if not text or len(text) > 256:
                error = "link texts must be non-empty and less than 256 characters."
                return {'success': 'false', 'error': error}
            elif not regex.match(text):
                error = "link texts are limited to alphanumeric and underscore characters."
                return {'success': 'false', 'error': error}
            elif not href or len(href) > 256:
                error = "links must have non-empty 'href' attributes."
                return {'success': 'false', 'error': error}
        return {'success': 'true'}

    def render_template(self, template_name, template_args=None):
        ''' overriding to properly handle 401 from template '''
        if template_args is None:
            template_args = {}
        template_args['make_url'] = self.make_url
        template_args['make_route'] = self.make_route
        template_args['h'] = cgi.escape
        template_args['attributes'] = {}
        template_args['controller'] = self
        
        try:
            mako_lookup = controllers.TemplateLookup(
                input_encoding='utf-8',
                directories=[
                    util.make_absolute(cherrypy.config.get(
                        'templates',
                        'share/splunk/search_mrsparkle/templates'
                    )),
                    util.make_absolute(cherrypy.config.get('module_dir'))
                ],
                imports=[
                    'import splunk',
                    'import cherrypy',
                    'from lib import i18n',
                    'from lib.util import json_html_safe as jsonify',
                    'from lib.util import json_decode',
                    'from lib.util import is_xhr, generateSelfHelpLink, extract_help_links'
                ]
            )
            templateInstance = mako_lookup.get_template(template_name)
        except Exception, e:
            logger.warn('unable to obtain template=%s' % template_name)
            raise controllers.TemplateRenderError(500, _(TEMPLATE_ERROR))
            
        try:
            return templateInstance.render(**template_args)
        except splunk.QuotaExceededException, e: 
            raise
        except splunk.AuthenticationFailed:
            # all that just for this
            cherrypy.session.delete()
            self.redirect_to_url('/account/login', 
                _qs=[('return_to', util.current_url_path())])
        except Exception, ex:
            logger.error('Mako failed to render: %s' \
              % mako.exceptions.text_error_template().render())
            raise controllers.TemplateRenderError(500, _(TEMPLATE_ERROR))