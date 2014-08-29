import logging
import controllers.module as module
import cherrypy
import splunk.entity as en

import json
import traceback

logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.modules.LogReviewConfig')

def output_if_true(boolean, value_if_true, value_if_false=""):
    
    if boolean:
        return value_if_true
    else:
        return value_if_false

def str_to_bool(str):
    """
    Converts the given string to a boolean; raises a ValueError if the str cannot be converted to a boolean.
        
    Arguments:
    str -- the string that needs to be converted to a boolean.
    """
        
    bool_str = str.strip().lower()
        
    if bool_str in ["t", "true", "1"]:
        return True
    elif bool_str in ["f", "false", "0"]:
        return False
    else:
        raise False



class LogReviewConfig(module.ModuleHandler):

    DEFAULT_NAMESPACE = 'SA-ThreatIntelligence'
    DEFAULT_OWNER = 'nobody'
    LOG_REVIEW_REST_URL = '/alerts/log_review/'
    
    @staticmethod
    def canEdit(user, sessionKey):
        
        ## Get Capabilities
        capabilities = LogReviewConfig.getCapabilities4User(user, sessionKey)
      
        if 'edit_log_review_settings' in capabilities:
            return True
        else:
            return False
    
    @staticmethod
    def getCapabilities4User(user, sessionKey):
        roles = []
        capabilities = []
      
        ## Get user info              
        if user is not None:
            logger.info('Retrieving role(s) for current user: %s' % (user))
            userDict = en.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=sessionKey)
      
            for stanza, settings in userDict.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            logger.info('Successfully retrieved role(s) for user: %s' % (user))
                            roles = val
           
            ## Get capabilities
            for role in roles:
                logger.info('Retrieving capabilities for current user: %s' % (user))
                roleDict = en.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=sessionKey)
              
                for stanza, settings in roleDict.items():
                    if stanza == role:
                        for key, val in settings.items():
                            if key == 'capabilities' or key =='imported_capabilities':
                                logger.info('Successfully retrieved %s for user: %s' % (key, user))
                                capabilities.extend(val)
          
        return capabilities
    
    @staticmethod
    def getNotableEditingEntity():

        # Get the configuration from the log_review endpoint
        return en.getEntity(LogReviewConfig.LOG_REVIEW_REST_URL, 'notable_editing', namespace = LogReviewConfig.DEFAULT_NAMESPACE, owner = LogReviewConfig.DEFAULT_OWNER, count=-1)
    
    @staticmethod
    def getDefaultEntity():

        # Get the configuration from the log_review endpoint
        return en.getEntity(LogReviewConfig.LOG_REVIEW_REST_URL, 'default', namespace = LogReviewConfig.DEFAULT_NAMESPACE, owner = LogReviewConfig.DEFAULT_OWNER, count=-1)
    
    @staticmethod
    def isUrgencyOverrideAllowed():
        
        notable_en = LogReviewConfig.getNotableEditingEntity()
        
        if 'allow_urgency_override' in notable_en:
            return str_to_bool( notable_en['allow_urgency_override'] )
        else:
            return True
    
    @staticmethod
    def getCommentEntity():

        # Get the configuration from the log_review endpoint
        return en.getEntity(LogReviewConfig.LOG_REVIEW_REST_URL, 'comment', namespace = LogReviewConfig.DEFAULT_NAMESPACE, owner = LogReviewConfig.DEFAULT_OWNER, count=-1)
    
    def generateResults(self, minimum_comment_length, is_required=False, allow_urgency_override=False, **args):
        
        # Prepare a response
        response = {}
        
        # Save the correlation search
        try:
            
            # Validate the argument
            try:
                minimum_comment_length = int(minimum_comment_length)
                
                # Make sure the value is not zero
                if minimum_comment_length == 0:
                    response["message"] = "The comment length must be greater than 0"
                    response["success"] = False
                    
                    return json.dumps(response)
                
                # Make sure the value is positive
                if minimum_comment_length < 0:
                    response["message"] = "The comment length must be a positive integer"
                    response["success"] = False
                    
                    return json.dumps(response)
                
            except ValueError:
                response["message"] = "The comment length must be a valid integer"
                response["success"] = False
                
                return json.dumps(response)
            
            # Set the attribute for the comment stanza
            comment_en = LogReviewConfig.getCommentEntity()
    
            comment_en['minimum_length'] = minimum_comment_length
            comment_en['is_required'] = is_required
            
            en.setEntity(comment_en)
            
            # Set the notable editing stanza
            notable_en = LogReviewConfig.getNotableEditingEntity()
            
            notable_en['allow_urgency_override'] = allow_urgency_override
            
            en.setEntity(notable_en)
            
            # Settings changed successfully, return a message accordingly
            response["message"] = "Incident review settings successfully changed"
            response["success"] = True

        except Exception, e :
            
            tb = traceback.format_exc()
            
            response["message"] = str(e)
            response["trace"] = tb
            response["success"] = False

        # Return 
        return json.dumps(response)