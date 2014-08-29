import json
import logging
import os
import shutil
import sys

import cherrypy
import splunk
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib import util as app_util
import controllers.module as module

from splunk.models.app import App

logger = logging.getLogger('splunk.module.TA_Windows_FTR')

STATIC_APP = 'Splunk_TA_windows'

class TA_Windows_FTR(module.ModuleHandler):

    def generateResults(self, **kwargs):

        if not (sys.platform.startswith("win")):
            return self.render_json({'is_windows': False})

        app_name = kwargs.get('client_app', STATIC_APP)
        app_dir = os.path.join(app_util.get_apps_dir(), app_name)

        legacy_js = os.path.join(app_dir, 'appserver', 'static', 'application.js')
        legacy_handler = os.path.join(app_dir, 'bin', 'setuphandler.py')
        legacy_restmap = os.path.join(app_dir, 'default', 'restmap.conf')
        legacy_setup = os.path.join(app_dir, 'default', 'setup.xml')
                                    
        for legacy in [legacy_js, legacy_handler, legacy_restmap, legacy_setup]:
            if os.path.exists(legacy):
                shutil.move(legacy, legacy + '.bak')
                logger.info('disabled legacy setup component %s for app %s' % (legacy, app_name))

        return self.render_json({})
      
    def render_json(self, response_data, set_mime='text/json'):
        ''' 
        clone of BaseController.render_json, which is
        not available to module controllers (SPL-43204)
        '''

        cherrypy.response.headers['Content-Type'] = set_mime

        if isinstance(response_data, jsonresponse.JsonResponse):
            response = response_data.toJson().replace("</", "<\\/")
        else:
            response = json.dumps(response_data).replace("</", "<\\/")

        # Pad with 256 bytes of whitespace for IE security issue. See SPL-34355
        return ' ' * 256  + '\n' + response
