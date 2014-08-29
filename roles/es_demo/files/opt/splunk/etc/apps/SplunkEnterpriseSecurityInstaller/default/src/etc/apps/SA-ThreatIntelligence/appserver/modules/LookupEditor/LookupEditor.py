import cherrypy
import controllers.module as module
import csv
import json
import logging
import lxml.etree as et
import os
import splunk.auth as auth
import splunk.clilib.bundle_paths as bp
import splunk.entity as entity

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.modules.LookupEditor')


class LookupEditor(module.ModuleHandler):
    
    baseCSVPath = os.path.join(bp.get_base_path(), '%s', 'lookups')
    
    def generateResults(self, app, **args):
        response = {}

        self.baseCSVPath = self.baseCSVPath % app

        try: 
    
            response["message"] = "Lookup updated successfully"
            response["success"] = True

        except Exception, e :
            response["message"] = str(e)
            response["success"] = False

        return json.dumps(response)
    
    ## get capabilities method    
    @staticmethod
    def getCapabilities4User(user=None, session_key=None):
        roles = []
        capabilities = []
        
        ## Get user info              
        if user is not None:
            logger.info('Retrieving role(s) for current user: %s' % (user))
            userDict = entity.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
        
            for stanza, settings in userDict.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            logger.info('Successfully retrieved role(s) for user: %s' % (user))
                            roles = val
             
        ## Get capabilities
        for role in roles:
            logger.info('Retrieving capabilities for current user: %s' % (user))
            roleDict = entity.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
            
            for stanza, settings in roleDict.items():
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            logger.info('Successfully retrieved %s for user: %s' % (key, user))
                            capabilities.extend(val)
            
        return capabilities    