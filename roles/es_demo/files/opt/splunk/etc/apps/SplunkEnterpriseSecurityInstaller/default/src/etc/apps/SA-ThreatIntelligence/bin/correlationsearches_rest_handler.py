'''
Copyright (C) 2005 - 2011 Splunk Inc. All Rights Reserved.
'''
import csv
import datetime
import logging
import logging.handlers
import os
import re
import splunk.admin as admin
import splunk.bundle as bundle
import splunk.entity as entity

from splunk import ResourceNotFound, AuthorizationFailed
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('correlationsearches_rest_handler')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'correlationsearches_rest_handler.log']), maxBytes=25000000, backupCount=5)
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


def _getFieldValue(args, name, default_value=None, max_length=None):
    """
    Get the field value from the argument list.
    """
    
    # Get the value if defined or the default value if not defined
    value = args[name][0] or default_value if name in args else default_value
    
    # Check the length
    if value and max_length and len(value) > max_length:
        raise admin.ArgValidationException(i18n.ungettext('App %(name)s cannot be longer than %(max_length)s character.', 
                                                          'App %(name)s cannot be longer than %(max_length)s characters.',
                                                          max_length) % {'name' : name, 'max_length' : max_length})
    # return the value
    return value
    

def _addToDictIfNonNull(dictval, name, value):
      """
      Add the given name and value to the dictionary if the value is not none.
      
      Arguments:
      dictval -- the dictionary to add to
      name    -- the name of the object to add
      value   -- the value of the object to add (if not none)
      """
      
      if value is not None:
          dictval[name] = value

          
class CorrelationSearches(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  ## admin.py constants
  REQUESTED_ACTIONS = { '1': 'ACTION_CREATE', '2': 'ACTION_LIST', '4': 'ACTION_EDIT', '8': 'ACTION_REMOVE', '16': 'ACTION_MEMBERS', '32': 'ACTION_RELOAD' }
  
  ## Permissions
  WRITE_CAPABILITY = 'edit_correlationsearches'

  ## Default Params
  PARAM_DISABLED         = 'disabled'
  PARAM_SAVEDSEARCH      = 'savedsearch'
  PARAM_SECURITY_DOMAIN  = 'security_domain'
  PARAM_SEVERITY         = 'severity'
  PARAM_RULE_NAME        = 'rule_name'
  PARAM_DESCRIPTION      = 'description'
  PARAM_RULE_TITLE       = 'rule_title'
  PARAM_RULE_DESCRIPTION = 'rule_description'
  PARAM_DRILLDOWN_NAME   = 'drilldown_name'
  PARAM_DRILLDOWN_SEARCH = 'drilldown_search'
  PARAM_DEFAULT_STATUS   = 'default_status'
  PARAM_DEFAULT_OWNER    = 'default_owner'
  
  PARAM_SEARCH           = 'search'
  
  VALID_PARAMS           = [
                            PARAM_SECURITY_DOMAIN,
                            PARAM_SEVERITY,
                            PARAM_RULE_NAME,
                            PARAM_DESCRIPTION,
                            PARAM_RULE_TITLE, 
                            PARAM_RULE_DESCRIPTION,
                            PARAM_DRILLDOWN_NAME,
                            PARAM_DRILLDOWN_SEARCH,
                            PARAM_DEFAULT_STATUS,
                            PARAM_DEFAULT_OWNER,
                            PARAM_SEARCH
                            ]
  
  REQUIRED_PARAMS        = [PARAM_RULE_NAME]
  
  IGNORED_PARAMS         = [PARAM_DISABLED]
  
  ## Default Vals
  DEFAULT_NAMESPACE      = 'SA-ThreatIntelligence'
  DEFAULT_OWNER          = 'nobody'
  
  ## Lookup file
  parent                 = os.path.dirname(os.path.dirname(__file__))
  correlationsFile       = os.path.join(parent, 'lookups', 'correlationsearches.csv')    

  def setup(self):
      logger.info('Setting up correlationsearches_rest_handler')
      
      ## set write capability
      self.setWriteCapability(CorrelationSearches.WRITE_CAPABILITY)
       
      if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:         
          ## Fill required params
          for arg in CorrelationSearches.REQUIRED_PARAMS:
              self.supportedArgs.addReqArg(arg)
              
          ## Fill valid params
          for arg in CorrelationSearches.VALID_PARAMS:
              if arg not in CorrelationSearches.REQUIRED_PARAMS:
                  self.supportedArgs.addOptArg(arg)

  def handleCreate(self, confInfo):
      """
      Handles creation of a correlation search
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if CorrelationSearches.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = CorrelationSearches.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload(makeCSV=False)
      
      ## Get list of valid review statuses
      reviewstatuses = self.getReviewStatuses()
      
      ## Get list of valid Splunk users
      users = self.getUsers()

      name = self.callerArgs.id
      args = self.callerArgs.data
      
      # Make sure the name is not empty
      if not name or len(name) == 0:
          raise admin.ArgValidationException("The name of the correlation search must not be empty")
      
      # Make sure the item does not already exist
      if name in self.readConf('correlationsearches'):
          raise admin.AlreadyExistsException("A correlation search entry already exists for %s" % (name))
      
      ## Get the field values (these are written to conf file)
      security_domain  = _getFieldValue(args, CorrelationSearches.PARAM_SECURITY_DOMAIN)
      severity         = _getFieldValue(args, CorrelationSearches.PARAM_SEVERITY)
      rule_name        = _getFieldValue(args, CorrelationSearches.PARAM_RULE_NAME)
      description      = _getFieldValue(args, CorrelationSearches.PARAM_DESCRIPTION)
      rule_title       = _getFieldValue(args, CorrelationSearches.PARAM_RULE_TITLE)
      rule_description = _getFieldValue(args, CorrelationSearches.PARAM_RULE_DESCRIPTION)
      drilldown_name   = _getFieldValue(args, CorrelationSearches.PARAM_DRILLDOWN_NAME)
      drilldown_search = _getFieldValue(args, CorrelationSearches.PARAM_DRILLDOWN_SEARCH)
      default_status   = _getFieldValue(args, CorrelationSearches.PARAM_DEFAULT_STATUS)
      default_owner    = _getFieldValue(args, CorrelationSearches.PARAM_DEFAULT_OWNER)
      search           = _getFieldValue(args, CorrelationSearches.PARAM_SEARCH)

      ## Add the field values to a configuration dictionary (that will be verified)
      conf = entity.getEntity('configs/conf-correlationsearches', '_new', sessionKey=self.getSessionKey())
      
      conf.namespace = self.appName # always save things to SOME app context.
      conf.owner = self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"
      
      conf['name'] = name
      
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_SECURITY_DOMAIN, security_domain)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_SEVERITY, severity)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_RULE_NAME, rule_name)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_DESCRIPTION, description)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_RULE_TITLE, rule_title)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_RULE_DESCRIPTION, rule_description)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_DRILLDOWN_NAME, drilldown_name)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_DRILLDOWN_SEARCH, drilldown_search)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_DEFAULT_STATUS, default_status)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_DEFAULT_OWNER, default_owner)
      _addToDictIfNonNull(conf, CorrelationSearches.PARAM_SEARCH, search)
    
      ## Check the configuration
      try:
          CorrelationSearches.checkConf(conf, name, users=users, reviewstatuses=reviewstatuses)
      
      except InvalidConfigException as e:
          e = "The configuration for the new correlation search '%s' is invalid and could not be created: %s" % (name, str(e))
          logger.error(e)
          raise admin.ArgValidationException(e)
    
      ## Write out an update to the reviewstatuses config file
      entity.setEntity(conf, sessionKey=self.getSessionKey())
      
      logger.info('Successfully added correlation search: %s' % (name))
      
      ## Reload correlationsearches (makeCSV)
      self.handleReload()
      
      logger.info('%s completed successfully' % (actionStr))
      
  def handleList(self, confInfo):      
      """
      Handles listing of a correlation search
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if CorrelationSearches.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = CorrelationSearches.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload(makeCSV=False)

      ## Get the configurations from correlationsearches.conf
      correlationsDict = self.readConfCtx('correlationsearches')
      
      ## Get list of valid review statuses
      reviewstatuses = self.getReviewStatuses()
      
      ## Get list of valid Splunk users
      users = self.getUsers()
      
      ## Get all correlations searches and provide the relevant options
      if correlationsDict is not None: 
          
          ## Check each conf
          for stanza, settings in correlationsDict.items():
              if stanza != 'default':
                  try:
                      ## Check config
                      CorrelationSearches.checkConf(settings, stanza, confInfo, users, reviewstatuses)
                   
                  except InvalidConfigException as e:
                      logger.error( "The configuration for the '%s' correlation search is invalid: %s" % ( stanza, str(e)) )                  
             
      logger.info('%s completed successfully' % (actionStr) ) 
              
  def handleReload(self, confInfo=None, makeCSV=True):
      """
      Handles refresh/reload of the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if CorrelationSearches.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = CorrelationSearches.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))

      try:
          refreshInfo = entity.refreshEntities('properties/correlationsearches', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh correlationsearches configurations via properties endpoint: %s' % str(e))
          
      try:
          refreshInfo = entity.refreshEntities('properties/authorize', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh authorize configurations via properties endpoint: %s' % str(e))
          
      try:
          refreshInfo = entity.refreshEntities('properties/reviewstatuses', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh reviewstatuses configurations via properties endpoint: %s' % str(e))

      if makeCSV:
          self.makeCSV(CorrelationSearches.correlationsFile)
      
      logger.info('%s completed successfully' % (actionStr))
  
  def makeCSV(self, correlationsFile, correlationsDict=None):
      logger.info("Creating correlationsearches file '%s'" % (correlationsFile))
            
      if correlationsDict is None:
           ## Get the configurations from correlationsearches.conf
           correlationsDict = self.readConf('correlationsearches')
           
      ## make correlationsDict valid if None
      if correlationsDict is None:
          correlationsDict = {}
      
      ## Get the configurations from savedsearches.conf
      savedsearchesDict = self.readConf('savedsearches')

      ## if savedsearchesDict is not None     
      if savedsearchesDict is not None:
          ## iterate dict
          for stanza in savedsearchesDict:
              ## if a correlation search that 
              if stanza.endswith('Rule') and stanza not in correlationsDict:
                  logger.info('Found a savedsearches.conf stanza %s not in correlationsearches.conf' % stanza)
                  correlationsDict[stanza] = savedsearchesDict[stanza]
      
      if len(correlationsDict)>0:
          correlationsFH = False
          
          try:
              correlationsFH = open(correlationsFile, 'w')
              
          except Exception as e:
              logger.critical("Could not create handle for file '%s': %s" % (correlationsFile, str(e)))
          
          if correlationsFH:
              header = [CorrelationSearches.PARAM_SAVEDSEARCH, 
                        CorrelationSearches.PARAM_SECURITY_DOMAIN, 
                        CorrelationSearches.PARAM_SEVERITY,
                        CorrelationSearches.PARAM_RULE_NAME,
                        CorrelationSearches.PARAM_DESCRIPTION,
                        CorrelationSearches.PARAM_RULE_TITLE,
                        CorrelationSearches.PARAM_RULE_DESCRIPTION,
                        CorrelationSearches.PARAM_DRILLDOWN_NAME,
                        CorrelationSearches.PARAM_DRILLDOWN_SEARCH,
                        CorrelationSearches.PARAM_DEFAULT_STATUS,
                        CorrelationSearches.PARAM_DEFAULT_OWNER]
      
              csv.writer(correlationsFH, lineterminator='\n').writerow(header)
              correlationsCSV = csv.DictWriter(correlationsFH, header, lineterminator='\n')
              
              ## Get default review status
              defaultStatus = self.getDefaultStatus()
      
              for stanza, settings in correlationsDict.items():
                  if stanza != 'default':
                      correlation = {}                      
                      correlation[CorrelationSearches.PARAM_SAVEDSEARCH] = stanza
                      
                      for key, val in settings.items():              
                          if val is None:
                              val = ''
                          
                          ## If key is status and nothing is set then take defaultStatus
                          if key == CorrelationSearches.PARAM_DEFAULT_STATUS and len(val) == 0:
                              correlation[key] = defaultStatus
                          
                          elif key in header:
                              correlation[key] = val
                              
                      correlationsCSV.writerow(correlation)
                          
      else:
          logger.warn("Correlations dictionary and savedsearches dictionary are empty; cannot makeCSV")
  
  def handleEdit(self, confInfo):
      """
      Handles edits to the configuration options
      """
      
      ## Get requested action
      actionStr = str(self.requestedAction)
      if CorrelationSearches.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = CorrelationSearches.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload(makeCSV=False)
      
      ## Get list of valid review statuses
      reviewstatuses = self.getReviewStatuses()
      
      ## Get list of valid Splunk users
      users = self.getUsers()
      
      name = self.callerArgs.id
      args = self.callerArgs
      
      if name is not None:
          try:
              conf = entity.getEntity('configs/conf-correlationsearches', name, sessionKey=self.getSessionKey())
              
          except ResourceNotFound:
              raise admin.NotFoundException("A correlationsearch configuration with the given name '%s' could not be found" % (name))
    
      else:
          # Stop if no name was provided
          raise admin.ArgValidationException("No name provided")
      
      # Create the resulting configuration that would be persisted if the settings provided are applied
      for key, val in conf.items():
          if key in args.data:
              
              # Get the new value
              new_value = args[key][0]
              
              # Set the value to a single space if empty or none, otherwise, Splunk won't save it (SOLNPCI-532)
              if new_value in [None, '']:
                  new_value = ' '
                  
              # Assign the value
              conf[key] = new_value
        
          if key == admin.EAI_ENTRY_ACL:
              if val.has_key('app') and val['app'] is not None and len(val['app']) > 0:
                  conf.namespace = val['app']
            
              if val.has_key('owner') and val['owner'] is not None and len(val['owner']) > 0:
                  conf.owner = val['owner']
                
      if conf.namespace is None or len(conf.namespace) == 0:
          conf.namespace = CorrelationSearches.DEFAULT_NAMESPACE
        
      if conf.owner is None or len(conf.owner) == 0:
          conf.owner = CorrelationSearches.DEFAULT_OWNER
      
      try:
          ## Check config
          CorrelationSearches.checkConf(conf, name, users=users, reviewstatuses=reviewstatuses)
               
      except InvalidConfigException as e:
          e = "The edit attempt for the correlation search '%s' produced an invalid configuration: %s" % (name, str(e))
          logger.error(e)
          raise admin.ArgValidationException(e)

      ## Write out an update to the correlationsearches config file
      try:
          entity.setEntity(conf, sessionKey=self.getSessionKey())
      except AuthorizationFailed as e:
          raise admin.InternalException(e)
      
      logger.info("Successfully updated the '%s' correlation search" % (name))
      
      ## Reload correlationsearches (makeCSV)
      self.handleReload()
      
      logger.info('%s completed successfully' % (actionStr))
          
  def handleRemove(self, confInfo):
      pass        
        
  @staticmethod
  def str_to_bool(strval):
      """
      Converts the given string to a boolean; raises a ValueError if the str cannot be converted to a boolean.
        
      Arguments:
      str -- the string that needs to be converted to a boolean.
      """
        
      bool_str = strval.strip().lower()
        
      if bool_str in ["t", "true", "1"]:
          return True
      elif bool_str in ["f", "false", "0"]:
          return False
      else:
          raise ValueError("The value is not a valid boolean")
              
  @staticmethod
  def checkConf(settings, stanza=None, confInfo=None, users=[], reviewstatuses=[], throwExceptionOnError=False):
      """
      Checks the settings and raises an exception if the configuration is invalid.
      """ 
      ## Below is a list of the required fields. The entries in this list will be removed as they
      ## are observed. An empty list at the end of the config check indicates that all necessary
      ## fields where provided.
      required_fields = CorrelationSearches.REQUIRED_PARAMS[:]
            
      if stanza is not None and confInfo is not None:

          # Add each of the settings
          for key, val in settings.items():              
              ## Set val to empty if None
              if val is None:
                  val = ''
                  
              if key in CorrelationSearches.VALID_PARAMS:
                  confInfo[stanza].append(key, val)
                          
              ## Key is eai;acl Set meta  
              elif key.startswith(admin.EAI_ENTRY_ACL):
                  confInfo[stanza].setMetadata(key, val)
                          
              ## Key is eai; userName/appName
              elif key.startswith(admin.EAI_META_PREFIX):
                  confInfo[stanza].append(key, val)
                  
              ## Key is not proper
              else:
                  pass
              
      else:
          pass
      ## end if statement
                  
      ## Check each of the settings
      logger.info("Checking general settings for the '%s' correlation search" % (stanza))

      for key, val in settings.items():
          
          if val is None:
              val = ''
              
          ## Check the DEFAULT_STATUS
          if key == CorrelationSearches.PARAM_DEFAULT_STATUS and ( len(val) > 0 and val != ' '):
              if val not in reviewstatuses:
                  raise InvalidParameterValueException(key, val, "must be a valid review status")
              
              ## Remove the field from the list of required fields
              try:
                  required_fields.remove(key)
                      
              except ValueError:
                  pass # Field not available, probably because it is not required

          ## Check the DEFAULT_OWNER
          elif key == CorrelationSearches.PARAM_DEFAULT_OWNER and ( len(val) > 0 and val != ' '):
              if val not in users:
                  raise InvalidParameterValueException(key, val, "must be a valid Splunk user")
              
              ## Remove the field from the list of required fields
              try:
                  required_fields.remove(key)
                      
              except ValueError:
                  pass # Field not available, probably because it is not required
          
          #elif key == CorrelationSearches.PARAM_RULE_NAME and len(val) == 0 and CorrelationSearches.PARAM_RULE_NAME in CorrelationSearches.REQUIRED_PARAMS:
          #    raise InvalidParameterValueException(key, val, "must not be blank")

          elif key in CorrelationSearches.REQUIRED_PARAMS:
              ## Remove the field from the list of required fields
              try:
                  required_fields.remove(key)
                      
              except ValueError:
                  pass # Field not available, probably because it is not required

          elif key in CorrelationSearches.VALID_PARAMS:
              pass
                  
          ## Key is ignored
          elif key in CorrelationSearches.IGNORED_PARAMS:
              pass        
                                 
          ## Key is eai
          elif key.startswith('eai'):
              pass
               
          ## Key is not proper
          else:
              if throwExceptionOnError:
                  raise UnsupportedParameterException()
              
              else:
                  logger.warn("The configuration for the '%s' correlation search contains an unsupported parameter: %s" % (stanza, key))
      
      ## Warn if some of the required fields were not provided
      if len(required_fields) > 0:
          raise InvalidConfigException('The following fields must be defined in the configuration but were not: ' + ', '.join(required_fields).strip())
        
  def getReviewStatuses(self):
      reviewstatuses = []

      logger.info('Retrieving review statuses')
      ## IMPORTANT must use configs/conf- instead of alerts/reviewstatuses to avoid looping
      reviewstatusesDict = bundle.getConf('reviewstatuses', sessionKey=self.getSessionKey())
      
      if reviewstatusesDict is not None:
          ## Iterate status dictionary
          for stanza in reviewstatusesDict:
              if stanza != 'default':
                  reviewstatuses.append(stanza)
    
      else:
          logger.error("Could not retrieve review statuses; reviewstatusesDict is None")
    
      return reviewstatuses

  def getDefaultStatus(self):
      logger.info("Retrieving review statuses with 'default' parameter set")
      ## IMPORTANT must use configs/conf- instead of alerts/reviewstatuses to avoid looping
      reviewstatusesDict = bundle.getConf('reviewstatuses', sessionKey=self.getSessionKey())

      if reviewstatusesDict is not None:
          ## Iterate status dictionary
          for stanza in reviewstatusesDict:
              if stanza != 'default':
                  result = {}
                  result['stanza'] = stanza
                
                  for key, val in reviewstatusesDict[stanza].items():
                      if val is None:
                          val = ''
                      
                      if key == CorrelationSearches.PARAM_DISABLED:
                          try:
                              is_disabled = CorrelationSearches.str_to_bool(val)
                    
                          except:
                              is_disabled = True
                      
                      if key == 'default':
                          try:
                              is_default = CorrelationSearches.str_to_bool(val)
                 
                          except:
                              is_default = False
       
              if is_default and not is_disabled:
                  logger.info("Successfully retrieved default review status '%s'" % (stanza))
                  return stanza
          
      else:
          logger.error("Could not retrieve review status with 'default' parameter set; reviewstatusesDict is None")
          return ''
      
      logger.error("Could not retrieve review status with 'default' parameter set; no such status exists")
      return ''
    
#  def getUsers(self):
#      users = []
#
#      logger.info('Retrieving users')
#      userDict = entity.getEntities('authentication/users', count=-1, sessionKey=self.getSessionKey())
#      
#      for stanza in userDict:
#          users.append(stanza)
#          
#      return users

  # SOLNESS-1576 fix [BEGIN]
  def getUsers(self):
      '''Get list of users who can be assigned ownership of a notable event.
         We retrieve this information from notable_owners.csv, since there
         is currently no list_user capability in Splunk. Thus, a user who
         attempts to read the authentication/users endpoint but does not
         possess the edit_user privilege will only be able to see their
         own user account. This method can be replaced by the previous
         implementation when a list_user feature is available.

         Some of this stolen from ListNotableOwners.html which uses the
         same idea.
      '''

      filename = make_splunkhome_path(["etc",
                                   "apps",
                                   "SA-ThreatIntelligence",
                                   "lookups",
                                   "notable_owners.csv"])

      users = []
      with open(filename, "rb") as fh:
          users.extend([row.get('owner') for row in csv.DictReader(fh)])
      logger.info('Retrieving list of users who can own notable events.')
      return users
  # SOLNESS-1576 fix [END]
          
# initialize the handler
admin.init(CorrelationSearches, admin.CONTEXT_APP_AND_USER)