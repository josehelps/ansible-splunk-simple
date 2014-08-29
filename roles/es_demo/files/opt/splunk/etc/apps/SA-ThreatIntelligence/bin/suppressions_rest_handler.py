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

from notable_event_suppression import NotableEventSuppression, UnauthorizedUserException
from splunk import ResourceNotFound
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('suppressions_rest_handler')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'suppressions_rest_handler.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()


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

          
class Suppressions(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  ## admin.py constants
  REQUESTED_ACTIONS = { '1': 'ACTION_CREATE', '2': 'ACTION_LIST', '4': 'ACTION_EDIT', '8': 'ACTION_REMOVE', '16': 'ACTION_MEMBERS', '32': 'ACTION_RELOAD' }  

  ## Permissions
  WRITE_CAPABILITY = 'edit_suppressions'

  ## Default Params
  PARAM_DISABLED = 'disabled'
  PARAM_SEARCH = 'search'
  PARAM_DESCRIPTION = 'description'
  
  VALID_PARAMS = [PARAM_DISABLED, PARAM_SEARCH, PARAM_DESCRIPTION]
  REQUIRED_PARAMS = [PARAM_DISABLED, PARAM_SEARCH]
  
  ## Default Vals
  DEFAULT_NAMESPACE = 'SA-ThreatIntelligence'
  DEFAULT_OWNER = 'nobody'

  DEFAULT_DISABLED = 0
  
  def setup(self):
      logger.info('Setting up suppressions_rest_handler')
      
      ## set write capability
      self.setWriteCapability(Suppressions.WRITE_CAPABILITY)            
       
      if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:         
          ## Fill required params
          for arg in Suppressions.REQUIRED_PARAMS:
              self.supportedArgs.addReqArg(arg)
              
          ## Fill valid params
          for arg in Suppressions.VALID_PARAMS:
              if arg not in Suppressions.REQUIRED_PARAMS:
                  self.supportedArgs.addOptArg(arg)
  
  def handleCreate(self, confInfo):
      """
      Handles creation of a suppression
      """
      
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Suppressions.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Suppressions.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload()
    
      name = self.callerArgs.id
      args = self.callerArgs.data
      
      # Make sure the name is not empty
      if not name or len(name) == 0:
          raise admin.ArgValidationException("The name of the suppression must not be empty")
      
      # Make sure the name follows the convention
      nameMatch = NotableEventSuppression.suppressionRE.match(name)
      
      if not nameMatch:
          raise admin.ArgValidationException("The name of the suppression must follow proper convention")
      
      # Make sure the item does not already exist
      if name in self.readConf('eventtypes'):
          raise admin.AlreadyExistsException("A suppression entry already exists for %s" % (name))
      
      ## Get the field values
      disabled = _getFieldValue(args, Suppressions.PARAM_DISABLED)
      search = _getFieldValue(args, Suppressions.PARAM_SEARCH)
      description = _getFieldValue(args, Suppressions.PARAM_DESCRIPTION)
      
      ## Add the field values to a configuration dictionary (that will be verified)
      conf = entity.getEntity('saved/eventtypes', '_new', sessionKey=self.getSessionKey())
      
      conf.namespace = self.appName # always save things to SOME app context.
      conf.owner = self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"
      
      conf['name'] = name
      
      _addToDictIfNonNull(conf, Suppressions.PARAM_DISABLED, disabled)
      _addToDictIfNonNull(conf, Suppressions.PARAM_SEARCH, search)
      _addToDictIfNonNull(conf, Suppressions.PARAM_DESCRIPTION, description)
      
      ## Check the configuration
      try:
          Suppressions.checkConf(conf, name)
      
      except InvalidConfigException as e:
          e = "The configuration for the new suppression '%s' is invalid and could not be created: %s" % (name, str(e))
          logger.error(e)
          raise admin.ArgValidationException(e)
    
      ## Write out an update to the eventtypes config file
      entity.setEntity(conf, sessionKey=self.getSessionKey())
      
      logger.info('Successfully added suppression: %s' % (name))
      
      ## Reload suppressions
      self.handleReload()
      
      logger.info('%s completed successfully' % (actionStr))
      
  def handleList(self, confInfo):      
      """
      Handles listing of a suppression
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Suppressions.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Suppressions.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      self.handleReload()
       
      ## Get the configurations from suppression.conf
      suppressionDict = self.readConfCtx('eventtypes')
      
      ## Get all suppressions and provide the relevant options
      if suppressionDict != None:
          ## Check each conf
          for stanza, settings in suppressionDict.items():
              stanzaMatch = NotableEventSuppression.suppressionRE.match(stanza)
              
              if stanzaMatch:
                  try:
                      ## Check config
                      Suppressions.checkConf(settings, stanza, confInfo)
                          
                  except InvalidConfigException as e:
                      logger.error("The configuration for suppression '%s' is invalid: %s" % ( stanza, str(e)) )                  
           
      logger.info('%s completed successfully' % (actionStr))
         
  def handleReload(self, confInfo=None, makeCSV=True):
      """
      Handles refresh/reload of the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Suppressions.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Suppressions.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))

      logger.info('Refreshing suppression configurations via properties endpoint')
      try:
          refreshInfo = entity.refreshEntities('properties/eventtypes', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh suppression configurations via properties endpoint: %s' % str(e))
       
      logger.info('%s completed successfully' % (actionStr))
  
  def handleEdit(self, confInfo):
      """
      Handles edits to the configuration options
      """
      
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Suppressions.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Suppressions.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))

      ## Refresh
      self.handleReload()
      
      name = self.callerArgs.id
      args = self.callerArgs
      
      if name is not None:
          # Make sure the name follows the convention
          nameMatch = NotableEventSuppression.suppressionRE.match(name)
          
          if not nameMatch:
              raise admin.ArgValidationException("The name of the suppression must follow proper convention")
      
          try:
              conf = entity.getEntity('saved/eventtypes', name, sessionKey=self.getSessionKey())
              
          except ResourceNotFound:
              raise admin.NotFoundException("A suppression configuration with the given name '%s' could not be found" % (name))
    
      else:
          # Stop if no name was provided
          raise admin.ArgValidationException("No name provided")
  
      # Create the resulting configuration that would be persisted if the settings provided are applied
      for key, val in conf.items():
          if key in args.data:
              
              # Set the value to a single space so that the field is set to a blank value
              new_value = args[key][0]
              
              if new_value in [None, '']:
                  new_value = ' '
              
              conf[key] = new_value
        
          if key == admin.EAI_ENTRY_ACL:
              if val.has_key('app') and val['app'] is not None and len(val['app']) > 0:
                  conf.namespace = val['app']
            
              if val.has_key('owner') and val['owner'] is not None and len(val['owner']) > 0:
                  conf.owner = val['owner']              
          
      if conf.namespace is None or len(conf.namespace) == 0:
          conf.namespace = Suppressions.DEFAULT_NAMESPACE
        
      if conf.owner is None or len(conf.owner) == 0:
          conf.owner = Suppressions.DEFAULT_OWNER
      
      try:
          ## Check config
          Suppressions.checkConf(conf, name)
               
      except InvalidConfigException as e:
          e = "The edit attempt for the suppression '%s' produced an invalid configuration: %s" % (name, str(e))
          logger.error(e)
          raise admin.ArgValidationException(e)
      
      ## Write out an update to the eventtypes config file
      entity.setEntity(conf, sessionKey=self.getSessionKey())
      
      # Log that the suppression was updated
      logger.info("Successfully updated the '%s' suppression" % (name))
      
      ## Reload suppressions
      self.handleReload()
      
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
      required_fields = Suppressions.REQUIRED_PARAMS[:]
      
      if stanza is not None and confInfo is not None:
          # Add each of the settings
          for key, val in settings.items():
              ## Set val to empty if None
              if val is None:
                  val = ''
                  
              if key in Suppressions.VALID_PARAMS:
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
          
      ## Check each of the settings individually
      logger.info("Checking general settings for the '%s' suppression" % (stanza))
      for key, val in settings.items():
          ## Set val to empty if None
          if val is None:
              val = ''
          
          ## Check the disabled/selected value
          if key == Suppressions.PARAM_DISABLED:
              try:
                  Suppressions.str_to_bool(val)
                  
                  ## Remove the field from the list of required fields
                  try:
                      required_fields.remove(key)
                      
                  except ValueError:
                      pass # Field not available, probably because it is not required
                      
              except ValueError:
                  raise InvalidParameterValueException(key, val, "must be a valid boolean")
                  
          elif key in Suppressions.REQUIRED_PARAMS:
              ## Remove the field from the list of required fields
              try:
                  required_fields.remove(key)
                      
              except ValueError:
                  pass # Field not available, probably because it is not required
                      
          elif key in Suppressions.VALID_PARAMS:
              pass
                                 
          ## Key is eai
          elif key.startswith(admin.EAI_META_PREFIX):
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
admin.init(Suppressions, admin.CONTEXT_APP_AND_USER)