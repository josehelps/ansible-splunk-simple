'''
Copyright (C) 2005 - 2011 Splunk Inc. All Rights Reserved.
'''
import csv
import logging
import logging.handlers
import os
import re
import shutil
import splunk.admin as admin
import splunk.entity as entity

from splunk import ResourceNotFound
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('governance_rest_handler')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'governance_rest_handler.log']), maxBytes=25000000, backupCount=5)
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


class IncompleteComplianceException(InvalidConfigException):
    """
    Describes a compliance parameter that is incomplete.
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

          
class Governance(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  ## admin.py constants
  REQUESTED_ACTIONS   = { '1': 'ACTION_CREATE', '2': 'ACTION_LIST', '4': 'ACTION_EDIT', '8': 'ACTION_REMOVE', '16': 'ACTION_MEMBERS', '32': 'ACTION_RELOAD' }
  
  ## Permissions
  WRITE_CAPABILITY    = 'edit_correlationsearches'

  ## Defaults Param
  PARAM_DISABLED      = 'disabled'
  PARAM_SAVEDSEARCH   = 'savedsearch'
  PARAM_GOVERNANCE    = 'governance'
  PARAM_CONTROL       = 'control'
  PARAM_TAG           = 'tag'
  PARAM_LOOKUP_TYPE   = 'lookup_type'
  
  VALID_PARAMS        = []
  REQUIRED_PARAMS     = []
  REQUIRED_COMPLIANCE = [PARAM_GOVERNANCE, PARAM_CONTROL]
  
  IGNORED_PARAMS      = [PARAM_DISABLED]
  
  ## Default Vals
  DEFAULT_NAMESPACE   = 'SA-ThreatIntelligence'
  DEFAULT_OWNER       = 'owner'
  DEFAULT_LOOKUP_TYPE = 'default'
  TAG_LOOKUP_TYPE     = 'tag'
  
  governanceRE        = re.compile('^(compliance\.\d+)\.' + PARAM_GOVERNANCE + '$')
  controlRE           = re.compile('^(compliance\.\d+)\.' + PARAM_CONTROL + '$')
  tagRE               = re.compile('^(compliance\.\d+)\.' + PARAM_TAG + '$')

  ## Lookup file
  parent              = os.path.dirname(os.path.dirname(__file__))
  governanceFile      = os.path.join(parent, 'lookups', 'governance.csv')    
  
  def setup(self):
      logger.info('Setting up governance_rest_handler')
      
      ## set write capability
      self.setWriteCapability(Governance.WRITE_CAPABILITY)       
       
      if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:         
          ## Fill required params
          for arg in Governance.REQUIRED_PARAMS:
              self.supportedArgs.addReqArg(arg)
              
          ## Fill valid params
          for arg in Governance.VALID_PARAMS:
              if arg not in Governance.REQUIRED_PARAMS:
                  self.supportedArgs.addOptArg(arg)

          ## Fill wildcarded params
          for arg in Governance.REQUIRED_COMPLIANCE:
              wildcardParam = 'compliance.*'
              if wildcardParam not in Governance.REQUIRED_PARAMS:
                  self.supportedArgs.addOptArg(wildcardParam)
  
  def handleCreate(self, confInfo):
      """
      Handles creation of a governance configuration
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Governance.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Governance.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload(makeCSV=False)

      name = self.callerArgs.id
      args = self.callerArgs.data
      
      # Make sure the name is not empty
      if not name or len(name) == 0:
          raise admin.ArgValidationException("The name of the governance configuration must not be empty")
      
      # Make sure the item does not already exist
      if name in self.readConf('governance'):
          raise admin.AlreadyExistsException("A governance configuration already exists for %s" % (name))
      
      ## Get a new entry from the conf-postprocess interface
      conf = entity.getEntity('configs/conf-governance', '_new', sessionKey=self.getSessionKey())
    
      conf.namespace = self.appName # always save things to SOME app context.
      conf.owner = self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"
      
      conf['name'] = name
      
      for arg in args:
          governanceMatch = Governance.governanceRE.match(arg)
          controlMatch = Governance.controlRE.match(arg)
          tagMatch = Governance.tagRE.match(arg)
          
          ## Add the field values to a configuration dictionary (that will be verified)
          if governanceMatch or controlMatch or tagMatch or arg in Governance.VALID_PARAMS:
              _addToDictIfNonNull(conf, arg, args[arg][0])
    
      ## Check the configuration
      try:
          Governance.checkConf(conf, name)
      
      except InvalidConfigException as e:
          e = "The configuration for the new governance entry '%s' is invalid and could not be created: %s" % (name, str(e))
          logger.error(e)
          raise admin.ArgValidationException(e)
    
      ## Write out an update to the reviewstatuses config file
      entity.setEntity(conf, sessionKey=self.getSessionKey())

      logger.info('Successfully added governance configuration: %s' % (name))
      
      ## Reload governance (makeCSV)
      self.handleReload()
      
      logger.info('%s completed successfully' % (actionStr))
      
  def handleList(self, confInfo):      
      """
      Handles listing of a governance entry
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Governance.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Governance.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload(makeCSV=False)

      ## Get the configurations from governance.conf
      governanceDict = self.readConfCtx('governance')
      
      ## Get all governance configurations and provide the relevant options
      if governanceDict is not None: 
          
          ## Check each conf
          for stanza, settings in governanceDict.items():
              if stanza != 'default':
                  try:
                      ## Check config
                      Governance.checkConf(settings, stanza, confInfo)
                   
                  except InvalidConfigException as e:
                      logger.error( "The configuration for governance entry '%s' is invalid: %s" % ( stanza, str(e)) )                  
             
      logger.info('%s completed successfully' % (actionStr) ) 
              
  def handleReload(self, confInfo=None, makeCSV=True):
      """
      Handles refresh/reload of the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Governance.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Governance.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))

      try:
          refreshInfo = entity.refreshEntities('properties/governance', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh governance configurations via properties endpoint: %s' % str(e))
     
      if makeCSV:
          self.makeCSV(Governance.governanceFile)
      
      logger.info('%s completed successfully' % (actionStr))
  
  def makeCSV(self, governanceFile, governanceDict=None):
      logger.info("Creating governance file '%s'" % (governanceFile))
      
      if governanceDict is None:
           ## Get the configurations from governance.conf
           governanceDict = self.readConf('governance')
           
      if governanceDict is not None:          
          ## Get governanceFileData
          try:
              governanceFH = open(governanceFile, 'rU')
              governanceFileData = governanceFH.read()
              
          except Exception as e:
              logger.warn("Could not create handle for file '%s': %s" % (governanceFile, str(e)))
              governanceFileData = ''
          
          ## Initialize header
          header = [Governance.PARAM_SAVEDSEARCH, 
                    Governance.PARAM_GOVERNANCE, 
                    Governance.PARAM_CONTROL,
                    Governance.PARAM_TAG,
                    Governance.PARAM_LOOKUP_TYPE]
        
          ## Initialize temporary file
          governanceMH = os.tmpfile()
          
          ## Write header
          csv.writer(governanceMH, lineterminator='\n').writerow(header)
          
          ## Create DictWriter
          governanceResults = csv.DictWriter(governanceMH, header, lineterminator='\n')
        
          for stanza, settings in governanceDict.items():
              result = {}
                          
              if stanza != 'default':
                  complianceKeys = []      
                      
                  ## compile a list of compliance keys
                  for key, val in settings.items():
                      governanceMatch = Governance.governanceRE.match(key)
                      controlMatch = Governance.controlRE.match(key)
                      tagMatch = Governance.tagRE.match(key)
                          
                      if governanceMatch:
                          key = governanceMatch.group(1)
                              
                          if key not in complianceKeys:
                              complianceKeys.append(key)
                                                
                      elif controlMatch:
                          key = controlMatch.group(1)
                              
                          if key not in complianceKeys:
                              complianceKeys.append(key)
                              
                      elif tagMatch:
                          key = tagMatch.group(1)
                          
                          if key not in complianceKeys:
                              complianceKeys.append(key)
                      
                  ## iterate compliance keys
                  for key in complianceKeys:
                      result = {}
                      result[Governance.PARAM_SAVEDSEARCH] = stanza
                          
                      govKey     = key + '.' + Governance.PARAM_GOVERNANCE
                      controlKey = key + '.' + Governance.PARAM_CONTROL
                      tagKey     = key + '.' + Governance.PARAM_TAG
                      
                      ## add the governance setting
                      if settings.has_key(govKey) and settings[govKey] is not None and len(settings[govKey]) > 0:
                          result[Governance.PARAM_GOVERNANCE] = settings[govKey]
                          
                      else:
                          result[Governance.PARAM_GOVERNANCE] = 'unknown'
                      
                      ## add the control setting            
                      if settings.has_key(controlKey) and settings[controlKey] is not None and len(settings[controlKey]) > 0:
                          result[Governance.PARAM_CONTROL] = settings[controlKey]
                              
                      else:
                          result[Governance.PARAM_CONTROL] = 'unknown'
                      
                      ## add the tag setting    
                      if settings.has_key(tagKey) and settings[tagKey] is not None and len(settings[tagKey]) > 0:
                          result[Governance.PARAM_TAG] = settings[tagKey]
                          result[Governance.PARAM_LOOKUP_TYPE] = Governance.TAG_LOOKUP_TYPE
                          
                      else:
                          result[Governance.PARAM_TAG] = ''
                          result[Governance.PARAM_LOOKUP_TYPE] = Governance.DEFAULT_LOOKUP_TYPE
                      
                      ## writerow as long as both governance and control are not unknown
                      if result[Governance.PARAM_GOVERNANCE] == 'unknown' and result[Governance.PARAM_CONTROL] == 'unknown':
                          pass        
                      
                      else:
                          governanceResults.writerow(result)
          
          ## Seek
          governanceMH.seek(0)
          
          ## Mem Data
          governanceMemData = governanceMH.read()
          
          if governanceMemData == governanceFileData:
              logger.info("File %s does not require change; exiting" % (governanceFile))
              governanceFH.close()
              governanceMH.close()
                      
          else:
              logger.info("File %s requires updating" % (governanceFile))
              
              governanceTempFile = governanceFile + '.tmp'
              governanceTempFH = False
              
              try:
                  governanceTempFH = open(governanceTempFile, 'w')
                  
              except Exception as e:
                  logger.critical("Could not create handle for temporary file '%s': %s" % (governanceTempFile, str(e)))
                  
              if governanceTempFH:
                  logger.info("Writing temporary file %s" % (governanceTempFile))
                  governanceTempFH.write(governanceMemData)
                  governanceMH.close()
                  governanceTempFH.close()
                  logger.info("Moving temporary file %s to %s" % (governanceTempFile, governanceFile))
                  
                  try:
                      shutil.move(governanceTempFile, governanceFile)
                  
                  except Exception as e:
                      logger.critical("Could not move file from %s to %s: %s" % (governanceTempFile, governanceFile, str(e)))
                      
      else:
          logger.critical("Governance dictionary is None; cannot makeCSV")
  
  def handleEdit(self, confInfo):
      """
      Handles edits to the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Governance.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Governance.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload(makeCSV=False)
      
      name = self.callerArgs.id
      args = self.callerArgs
      
      if name is not None:
          try:
              conf = entity.getEntity('configs/conf-governance', name, sessionKey=self.getSessionKey())
                
          except ResourceNotFound:
              raise admin.NotFoundException("A governance configuration with the given name '%s' could not be found" % (name))

      else:
          # Stop if no name was provided
          raise admin.ArgValidationException("No name provided")
      
      ## Create the resulting configuration that would be persisted if the settings provided are applied
      ## This rest handler supports the addition of arguments based on convention; therefore we merge args a little differently
      for arg in args:
          governanceMatch = Governance.governanceRE.match(arg)
          controlMatch = Governance.controlRE.match(arg)
          tagMatch = Governance.tagRE.match(arg)

          if governanceMatch or controlMatch or tagMatch or arg in Governance.VALID_PARAMS:
              conf[arg] = args[arg][0]
      
      for key, val in conf.items():      
          if key == admin.EAI_ENTRY_ACL:
              if val.has_key('app') and val['app'] is not None and len(val['app']) > 0:
                  conf.namespace = val['app']
            
              if val.has_key('owner') and val['owner'] is not None and len(val['owner']) > 0:
                  conf.owner = val['owner']
                    
      if conf.namespace is None or len(conf.namespace) == 0:
          conf.namespace = Governance.DEFAULT_NAMESPACE
            
      if conf.owner is None or len(conf.owner) == 0:
          conf.owner = Governance.DEFAULT_OWNER
            
      try:
          ## Check config
          Governance.checkConf(conf, name)
               
      except InvalidConfigException as e:
          e = "The edit attempt for the governance entry '%s' produced an invalid configuration: %s" % (name, str(e))
          logger.error(e)
          raise admin.ArgValidationException(e)

      ## Write out an update to the governance config file
      entity.setEntity(conf, sessionKey=self.getSessionKey())

      logger.info("Successfully updated the '%s' governance configuration" % (name))
      
      ## Reload governance (makeCSV)
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
      required_fields = Governance.REQUIRED_PARAMS[:]
      
      compliances = {}
      
      if stanza is not None and confInfo is not None:

          # Add each of the settings
          for key, val in settings.items():
              governanceMatch = Governance.governanceRE.match(key)
              controlMatch = Governance.controlRE.match(key)
              tagMatch = Governance.tagRE.match(key)
              
              ## Set val to empty if None
              if val is None:
                  val = ''
                  
              if key in Governance.VALID_PARAMS:
                  confInfo[stanza].append(key, val)
                  
              elif governanceMatch:
                  complianceKey = governanceMatch.group(1)
                  
                  if compliances.has_key(complianceKey):
                      compliances[complianceKey][Governance.PARAM_GOVERNANCE] = val
                      
                  else:
                      compliance = {}
                      compliance[Governance.PARAM_GOVERNANCE] = val
                      compliances[complianceKey] = compliance
                                            
              elif controlMatch:
                  complianceKey = controlMatch.group(1)
                  
                  if compliances.has_key(complianceKey):
                      compliances[complianceKey][Governance.PARAM_CONTROL] = val
                      
                  else:
                      compliance = {}
                      compliance[Governance.PARAM_CONTROL] = val
                      compliances[complianceKey] = compliance
                      
              elif tagMatch:
                  complianceKey = tagMatch.group(1)
                  
                  if compliances.has_key(complianceKey):
                      compliances[complianceKey][Governance.PARAM_TAG] = val
                      
                  else:
                      compliance = {}
                      compliance[Governance.PARAM_TAG] = val
                      compliances[complianceKey] = compliance
              
              ## Key is eai; Set meta  
              elif key.startswith(admin.EAI_ENTRY_ACL):
                  confInfo[stanza].setMetadata(key, val)
                          
              ## Key is eai; userName/appName
              elif key.startswith(admin.EAI_META_PREFIX):
                  confInfo[stanza].append(key, val)
                  
              ## Key is not proper
              else:
                  pass
          
          ## Add compliance settings
          for complianceKey in compliances:
              compliance = compliances[complianceKey]
              val = []
              
              ## Add governance as settings[0], control as settings[1], tag as settings[2]
              val.append(compliance.get(Governance.PARAM_GOVERNANCE, ''))
              val.append(compliance.get(Governance.PARAM_CONTROL, ''))
              val.append(compliance.get(Governance.PARAM_TAG, ''))
                  
              confInfo[stanza].append(complianceKey, val)

      else:
          pass
      ## end if statement
                  
      ## Check each of the settings
      logger.info("Checking general settings for the '%s' governance configuration" % (stanza))

      for key, val in settings.items():
          governanceMatch = Governance.governanceRE.match(key)
          controlMatch = Governance.controlRE.match(key)
          tagMatch = Governance.tagRE.match(key)
          
          if val is None:
              val = ''
                    
          if governanceMatch:
              complianceKey = governanceMatch.group(1)
                  
              if compliances.has_key(complianceKey):
                  compliances[complianceKey][Governance.PARAM_GOVERNANCE] = val
                      
              else:
                  compliance = {}
                  compliance[Governance.PARAM_GOVERNANCE] = val
                  compliances[complianceKey] = compliance
                                            
          elif controlMatch:
              complianceKey = controlMatch.group(1)
                  
              if compliances.has_key(complianceKey):
                  compliances[complianceKey][Governance.PARAM_CONTROL] = val
                      
              else:
                  compliance = {}
                  compliance[Governance.PARAM_CONTROL] = val
                  compliances[complianceKey] = compliance
                  
          elif tagMatch:
              complianceKey = tagMatch.group(1)
              
              if compliances.has_key(complianceKey):
                  compliances[complianceKey][Governance.PARAM_TAG] = val
                  
              else:
                  compliance = {}
                  compliance[Governance.PARAM_TAG] = val
                  compliances[complianceKey] = compliance
          
          elif key in Governance.REQUIRED_PARAMS:
              ## Remove the field from the list of required fields
              try:
                  required_fields.remove(key)
                      
              except ValueError:
                  pass # Field not available, probably because it is not required

          elif key in Governance.VALID_PARAMS:
              pass
                  
          ## Key is ignored
          elif key in Governance.IGNORED_PARAMS:
              pass        
                                 
          ## Key is eai
          elif key.startswith(admin.EAI_META_PREFIX):
              pass
               
          ## Key is not proper
          else:
              if throwExceptionOnError:
                  raise UnsupportedParameterException()
              
              else:
                  logger.warn("The configuration for the '%s' governance entry contains an unsupported parameter: %s" % (stanza, key))
                   
      for complianceKey in compliances:
          compliance = compliances[complianceKey]
          Governance.checkCompliance(compliance, complianceKey, stanza, throwExceptionOnError)
      
      ## Warn if some of the required fields were not provided
      if len(required_fields) > 0:
          raise InvalidConfigException('The following fields must be defined in the configuration but were not: ' + ', '.join(required_fields).strip())
        
  @staticmethod 
  def checkCompliance(compliance, complianceKey, stanza=None, throwExceptionOnError=False):
      logger.info("Checking '%s' settings for the '%s' governance configuration" % (complianceKey, stanza))
      required_fields = Governance.REQUIRED_COMPLIANCE[:]
      
      for field in Governance.REQUIRED_COMPLIANCE:
          if compliance.has_key(field) and len(compliance[field]) > 0:
              ## Remove the field from the list of required fields
              try:
                  required_fields.remove(field)
            
              except ValueError:
                  pass # Field not available, probably because it is not required 
          
      if len(required_fields) > 0:
          if throwExceptionOnError:
              raise IncompleteComplianceException()
          
          else:
              for field in required_fields:
                  logger.warn("The parameter '%s' for configuration '%s' is incomplete; missing '%s.%s'" % (complianceKey, stanza, complianceKey, field) )  
  
                               
# initialize the handler
admin.init(Governance, admin.CONTEXT_APP_AND_USER)