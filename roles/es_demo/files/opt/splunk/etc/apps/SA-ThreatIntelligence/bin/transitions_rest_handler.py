'''
Copyright (C) 2005 - 2011 Splunk Inc. All Rights Reserved.
'''
import datetime
import logging
import logging.handlers
import os
import random
import re
import splunk.admin as admin
import splunk.entity as entity
import splunk.rest as rest
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('transitions_rest_handler')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'transitions_rest_handler.log']), maxBytes=25000000, backupCount=5)
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


class MissingTransitionException(InvalidConfigException):
    """
    Describes a capability that is missing.
    """
    def __init__(self, transitions):
        self.transitions = transitions
        super(InvalidConfigException, self).__init__( "Missing transition detected")
    
    
def _getFieldValue(args, name, default_value=None, max_length=None):
    """
    Get the field value from the argument list.
    """
    
    ## Get the value if defined or the default value if not defined
    value = args[name][0] or default_value if name in args else default_value
    
    ## Check the length
    if value and max_length and len(value) > max_length:
        raise admin.ArgValidationException(i18n.ungettext('App %(name)s cannot be longer than %(max_length)s character.', 
                                                          'App %(name)s cannot be longer than %(max_length)s characters.',
                                                          max_length) % {'name' : name, 'max_length' : max_length})
    ## return the value
    return value
    

def _addToDictIfNonNull(dict, name, value):
      """
      Add the given name and value to the dictionary if the value is not none.
      
      Arguments:
      dict -- the dictionary to add to
      name -- the name of the object to add
      value -- the value of the object to add (if not none)
      """
      
      if value is not None:
          dict[name] = value

          
class Transitions(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  ## admin.py constants
  REQUESTED_ACTIONS = { '1': 'ACTION_CREATE', '2': 'ACTION_LIST', '4': 'ACTION_EDIT', '8': 'ACTION_REMOVE', '16': 'ACTION_MEMBERS', '32': 'ACTION_RELOAD' }  

  ## Defaults
  PARAM_DISABLED = 'disabled'
  
  VALID_PARAMS = [PARAM_DISABLED]
  REQUIRED_PARAMS = [PARAM_DISABLED]
  
  transitionRE = re.compile('^capability::transition_reviewstatus-\d+_to_\d+$')
  
  def setup(self):
      logger.info('Setting up transitions_rest_handler')
       
      if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:         
          ## Fill required params
          for arg in Transitions.REQUIRED_PARAMS:
              self.supportedArgs.addReqArg(arg)
              
          ## Fill valid params
          for arg in Transitions.VALID_PARAMS:
              if arg not in Transitions.REQUIRED_PARAMS:
                  self.supportedArgs.addOptArg(arg)
  
  def handleList(self, confInfo):      
      """
      Handles listing of a transition
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Transitions.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Transitions.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      self.handleReload()
       
      ## Get the configurations from authorize.conf
      authorizeDict = self.readConf('authorize')
      
      ## Get all transitions and provide the relevant options
      if authorizeDict != None:
          ## Check each conf
          for stanza, settings in authorizeDict.items():
              logger.info(stanza)
              transitionMatch = Transitions.transitionRE.match(stanza)
              
              if transitionMatch:
                  try:
                      ## Check config
                      Transitions.checkConf(settings, stanza, confInfo)
                          
                  except InvalidConfigException as e:
                      logger.error("The configuration for transition '%s' is invalid: %s" % ( stanza, str(e)) )                  
      
      logger.info('%s completed successfully' % (actionStr))
         
  def handleReload(self, confInfo=None):
      """
      Handles refresh/reload of the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Transitions.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Transitions.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))

      logger.info('Refreshing authorize configurations via properties endpoint')
      try:
          refreshInfo = entity.refreshEntities('properties/authorize', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh authorize configurations via properties endpoint: %s' % str(e))
       
      logger.info('%s completed successfully' % (actionStr))
  
  def handleRemove(self, confInfo):
      pass        
  
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
  def checkConf(settings, stanza=None, confInfo=None, throwExceptionOnError=False):
      """
      Checks the settings and raises an exception if the configuration is invalid.
      """ 
      ## Below is a list of the required fields. The entries in this list will be removed as they
      ## are observed. An empty list at the end of the config check indicates that all necessary
      ## fields where provided.
      required_fields = Transitions.REQUIRED_PARAMS[:]
      
      if stanza is not None and confInfo is not None:
          # Add each of the settings
          for key, val in settings.items():
              ## Set val to empty if None
              if val is None:
                  val = ''
                  
              if key in Transitions.VALID_PARAMS:
                  confInfo[stanza].append(key, val)
                          
              ## Key is eai; userName/appName
              elif key.startswith('eai') and key != 'eai:acl':
                  confInfo[stanza].append(key, val)
                  
              ## Key is eai; Set meta  
              elif key.startswith('eai'):
                  confInfo[stanza].setMetadata(key, val)
                  
              ## Key is not proper
              else:
                  pass
          
      ## Check each of the settings individually
      logger.info("Checking general settings for the '%s' transition" % (stanza))
      for key, val in settings.items():
          ## Set val to empty if None
          if val is None:
              val = ''
          
          ## Check the disabled/selected value
          if key == Transitions.PARAM_DISABLED:
              try:
                  Transitions.str_to_bool(val)
                  
                  ## Remove the field from the list of required fields
                  try:
                      required_fields.remove(key)
                      
                  except ValueError:
                      pass # Field not available, probably because it is not required
                      
              except ValueError:
                  raise InvalidParameterValueException(key, val, "must be a valid boolean")
                  
          elif key in Transitions.REQUIRED_PARAMS:
              ## Remove the field from the list of required fields
              try:
                  required_fields.remove(key)
                      
              except ValueError:
                  pass # Field not available, probably because it is not required
                      
          elif key in Transitions.VALID_PARAMS:
              pass
                                 
          ## Key is eai
          elif key.startswith('eai'):
              pass
               
          ## Key is not proper
          else:
              if throwExceptionOnError:
                  raise UnsupportedParameterException()
              
              else:
                  logger.warn("The configuration for '%s' contains an unsupported parameter: %s" % (stanza, key))

      ## Error if some of the required fields were not provided
      if len(required_fields) > 0:
          raise InvalidConfigException('The following fields must be defined in the configuration but were not: ' + ', '.join(required_fields).strip())
      
                          
# initialize the handler
admin.init(Transitions, admin.CONTEXT_APP_AND_USER)