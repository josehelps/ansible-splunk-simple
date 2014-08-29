'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''

import controllers.module as module
import cherrypy
import logging
import json
from time import strftime, gmtime

class SelectAll(module.ModuleHandler):
    
    def generateResults(self, **args):
        # "status" - none of this is external so there arent any developer docs, but besides status="OK" 
        # there is also "ERROR" and "FIELD_ERRORS".  
        # However the logic on client to display these errors is built around different assumptions, foremost that
        # the form we are rendering in the first place is coming from our EAI system (the API that drives the entire 
        # admin section and saved-search-popups etc..)
        # "messages" -- also returning strings in the messages array wouldnt do anything here for now, for similar reasons. 
        response = {
            "success": True, 
            "messages": [], 
            "data": None,
            "status": "OK"
        }

        return json.dumps(response)
