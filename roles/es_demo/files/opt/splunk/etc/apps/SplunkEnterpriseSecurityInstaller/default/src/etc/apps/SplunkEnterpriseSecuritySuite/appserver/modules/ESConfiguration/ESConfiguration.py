import controllers.module as module
import logging
import splunk.entity as entity

logger = logging.getLogger('splunk.appserver.SplunkEnterpriseSecuritySuite.modules.ESConfiguration')

class ESConfiguration(module.ModuleHandler):
    
    
    @staticmethod
    def is43orLater(session_key=None):
        serverDict = entity.getEntity('server/info', 'server-info', sessionKey=session_key)
        version = serverDict['version']
        version_parsed = version.split(".")
        
        version_major = int(version_parsed[0])
        version_minor = int(version_parsed[1])
        
        if version_major > 4 or ( version_major == 4 and version_minor >= 3):
            return True
        else:
            return False
    
    
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