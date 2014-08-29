'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''

import logging
import controllers.module as module
import cherrypy

import json
import traceback

logger = logging.getLogger('splunk.appserver.SA-Utils.modules.SOLNKeyIndicators')

class SOLNKeyIndicators(module.ModuleHandler):

    def generateResults(self, **args):
        
        # Prepare a response
        response = {}
        
        # Save
        try:
            
            # Do something here...
            response["message"] = "No operation performed; this is a placeholder"
            response["success"] = False

        except Exception, e :
            
            tb = traceback.format_exc()
            
            response["message"] = str(e)
            response["trace"] = tb
            response["success"] = False

        # Return 
        return json.dumps(response)