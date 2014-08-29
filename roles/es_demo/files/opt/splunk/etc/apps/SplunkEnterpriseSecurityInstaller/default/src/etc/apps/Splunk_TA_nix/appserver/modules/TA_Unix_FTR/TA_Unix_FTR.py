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

import json
import logging
import os
import shutil

import cherrypy
import splunk
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib import util as app_util
import controllers.module as module

from splunk.models.app import App

logger = logging.getLogger('splunk.module.TA_Unix_FTR')

CONFLICT_APPS = ['unix', 'unix_new']
STATIC_APP = 'Splunk_TA_nix'

class TA_Unix_FTR(module.ModuleHandler):

    def generateResults(self, **kwargs):

        app_name = kwargs.get('client_app', STATIC_APP)
        legacy_setup = os.path.join(app_util.get_apps_dir(), app_name,
                                    'default', 'setup.xml')
                                    
        if os.path.exists(legacy_setup):
            shutil.move(legacy_setup, legacy_setup + '.bak')
            logger.info('disabled legacy setup.xml for %s' % app_name)
            
        for app in App.all():
            if app.name in CONFLICT_APPS and not app.is_disabled:
                return self.render_json({'is_conflict': True, 'app_label': app.label})

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

