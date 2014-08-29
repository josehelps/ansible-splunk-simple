import os
import logging
import logging.handlers
import splunk.admin as admin
import splunk.entity as entity
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('postprocess_base_class')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'postprocess_base_class.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()

class UnauthorizedUserException(Exception):
    pass


class InvalidConfigException(Exception):
    pass


class InvalidParameterValueException(InvalidConfigException):
    """
    Describes a config parameter that has an invalid value.
    """
    
    def __init__(self, field, value, value_must_be):
        message = "The value for the parameter '%s' is invalid: %s (was %s)" % (field, value_must_be, value)
        super(InvalidConfigException, self).__init__( message)
      
        
class UnsupportedParameterException(InvalidConfigException):
    """
    Describes a config parameter that is unsupported.
    """
    pass


class PostProcess:
    ## Defaults
    DEFAULT_NAMESPACE = 'SA-Utils'
    DEFAULT_OWNER = 'nobody'
    
    POSTPROCESS_REST_URL = 'saved/postprocess'
  
    PARAM_DISABLED = 'disabled'
    PARAM_SAVEDSEARCH = 'savedsearch'
    PARAM_POSTPROCESS = 'postprocess'
  
    VALID_PARAMS = [PARAM_DISABLED, PARAM_SAVEDSEARCH, PARAM_POSTPROCESS]
  
    REQUIRED_PARAMS = [PARAM_DISABLED, PARAM_SAVEDSEARCH, PARAM_POSTPROCESS]
    
    @staticmethod
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
            raise ValueError("The value is not a valid boolean")
                  
    @staticmethod
    def checkConf(settings, stanza=None, confInfo=None, savedsearches=[], throwExceptionOnError=False):
        """
        Checks the settings and raises an exception if the configuration is invalid.
        """ 
        ## Below is a list of the required fields. The entries in this list will be removed as they
        ## are observed. An empty list at the end of the config check indicates that all necessary
        ## fields where provided.
        required_fields = PostProcess.REQUIRED_PARAMS[:]
              
        if stanza is not None and confInfo is not None:
    
            # Add each of the settings
            for key, val in settings.items():
                ## Set val to empty if None
                if val is None:
                    val = ''
                    
                if key in PostProcess.VALID_PARAMS:
                    confInfo[stanza].append(key, val)
                
                 ## Key is eai; Set meta  
                elif key.startswith(admin.EAI_ENTRY_ACL):
                    confInfo[stanza].setMetadata(key, val)
                            
                ## Key is eai; userName/appName
                elif key.startswith(admin.EAI_META_PREFIX):
                    confInfo[stanza].append(key, val)
                    
                ## Key is not proper
                else:
                    pass
                    
        ## Check each of the settings
        logger.info("Checking general settings for the '%s' correlation search" % (stanza))
        for key, val in settings.items():
            if val is None:
                val = ''
            
            ## Check the disabled/selected value
            if key == PostProcess.PARAM_DISABLED:
                try:
                    PostProcess.str_to_bool(val)
                    
                    ## Remove the field from the list of required fields
                    try:
                        required_fields.remove(key)
                        
                    except ValueError:
                        pass # Field not available, probably because it is not required
                        
                except ValueError:
                    raise InvalidParameterValueException(key, val, "must be a valid boolean")
                
            ## Check the savedsearch
            elif key == PostProcess.PARAM_SAVEDSEARCH:
                if val not in savedsearches:
                    raise InvalidParameterValueException(key, val, "must be a valid saved search")
                
                ## Remove the field from the list of required fields
                try:
                    required_fields.remove(key)
                        
                except ValueError:
                    pass # Field not available, probably because it is not required
            
            elif key in PostProcess.REQUIRED_PARAMS:
                ## Remove the field from the list of required fields
                try:
                    required_fields.remove(key)
                        
                except ValueError:
                    pass # Field not available, probably because it is not required
    
            elif key in PostProcess.VALID_PARAMS:
                pass
                                   
            ## Key is eai
            elif key.startswith(admin.EAI_META_PREFIX):
                pass
                 
            ## Key is not proper
            else:
                if throwExceptionOnError:
                    raise UnsupportedParameterException()
                
                else:
                    logger.warn("The configuration for the '%s' post process contains an unsupported parameter: %s" % (stanza, key))
                        
        ## Warn if some of the required fields were not provided
        if len(required_fields) > 0:
            raise InvalidConfigException('The following fields must be defined in the configuration but were not: ' + ', '.join(required_fields).strip())
        
    @staticmethod
    def getCurrentUser(session_key):
        user = None
        
        logger.info('Retrieving context for current user')
        contextDict = entity.getEntities('authentication/current-context/context', count=-1, sessionKey=session_key)
            
        for stanza, settings in contextDict.items():
            for key,val in settings.items():
                if key == 'username':
                    logger.info('Successfully retrieved context for current user: %s' % (val))
                    user = val
        
        return user        
  
    @staticmethod
    def getPostProcesses(session_key, namespace=DEFAULT_NAMESPACE, owner=DEFAULT_OWNER, savedsearch=None, enabledOnly=True):
        postprocesses = {}
        
        ## Get entities
        if savedsearch is None:
            temp_postprocessDict = entity.getEntities(PostProcess.POSTPROCESS_REST_URL, count=-1, namespace=namespace, owner=owner, sessionKey=session_key)
        else:
            temp_postprocessDict = entity.getEntities(PostProcess.POSTPROCESS_REST_URL, count=-1, namespace=namespace, owner=owner, sessionKey=session_key, search=savedsearch)
        
        if temp_postprocessDict is None:
            return {}
        
        else:
            postprocessDict = {}
            
            if enabledOnly:    
                for stanza, settings in temp_postprocessDict.items():
                    for key, val in settings.items():
                        if val is None:
                            val = ''
                            
                        if key == PostProcess.PARAM_DISABLED:
                            try:
                                if not PostProcess.str_to_bool(val):
                                    postprocessDict[stanza] = settings
                                    
                            except:
                                pass
                            
                            break
            
            else:
                postprocessDict = temp_postprocessDict
                        
            ## If we aren't concerned w/ a specific savedsearch value
            if savedsearch is None:
                postprocesses = postprocessDict

            else:
                for stanza, settings in postprocessDict.items():
                    for key, val in settings.items():
                        if val is None:
                            val = ''
                        
                        if key == PostProcess.PARAM_SAVEDSEARCH and val == savedsearch:
                            postprocesses[stanza] = settings
                            break
        
        return postprocesses