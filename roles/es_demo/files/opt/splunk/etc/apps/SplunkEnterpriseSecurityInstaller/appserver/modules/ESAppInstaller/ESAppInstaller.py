import logging
import controllers.module as module
import json
logger = logging.getLogger('splunk.modules.AppInstaller')


class ESAppInstaller(module.ModuleHandler):
    
    def generateResults(self, app, **args):
        response = {}

        try: 
    
            response["message"] = "AppInstaller:Success"
            response["success"] = True

        except Exception, e :
            response["message"] = str(e)
            response["success"] = False

        return json.dumps(response)
        
