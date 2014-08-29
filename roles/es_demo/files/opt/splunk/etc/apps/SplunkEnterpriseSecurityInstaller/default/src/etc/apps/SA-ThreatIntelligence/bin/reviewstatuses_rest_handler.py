'''
Copyright (C) 2005 - 2011 Splunk Inc. All Rights Reserved.
'''
import csv
import datetime
import logging
import logging.handlers
import os
import random
import re
import shutil
import splunk.admin as admin
import splunk.entity as entity
import splunk.rest as rest
import time

from splunk import ResourceNotFound
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)


## Setup the logger
def setup_logger():
    """
    Setup a logger for the REST handler.
    """
   
    logger = logging.getLogger('reviewstatuses_rest_handler')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
   
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'reviewstatuses_rest_handler.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
   
    logger.addHandler(file_handler)
   
    return logger

logger = setup_logger()

def time_function_call(fx):
    """
    This decorator will provide a log message measuring how long a function call took.
    
    Arguments:
    fx -- The function to measure
    """
    
    def wrapper(*args, **kwargs):
        t = time.time()
        
        r = fx(*args, **kwargs)
        
        diff = time.time() - t
        
        if diff > 60:
            diff_string = str( round( diff / 60, 2) ) + " minutes"
        else:
            diff_string = str( round( diff, 2) ) + " seconds"
        
        logger.debug( "%s, duration=%s" % (fx.__name__, diff_string)  )
        
        return r
    return wrapper


"""
This class provides a mechanism for determining how long operations take. Results are submitted as debug
calls to the logger provided in the constructor or the instance in the global variable logger if no logger
is provided in the constructor.

Example:
with TimeLogger("doing_something", Logger()):
    time.sleep(2)
"""
class TimeLogger():

    def __init__(self, title, logger=None):
        self.title = title
        self.logger = logger
    
    def __enter__(self):
        
        # Define the start time
        self.start_time = int(time.time())

    def __exit__(self, type, value, traceback):
        
        # Determine how long the operation took
        time_spent = int(time.time()) - self.start_time
        
        # See if we can find a logger as a global variable
        if self.logger is None:
            try:
                self.logger = logger
            except NameError:
                raise Exception("Could not get a logger instance for the purposes of recording performance")
        
        # Log the time spent
        self.logger.debug( self.title + ", duration=%d" % (time_spent) )

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

          
class ReviewStatuses(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  ## admin.py constants
  REQUESTED_ACTIONS       = { '1': 'ACTION_CREATE', '2': 'ACTION_LIST', '4': 'ACTION_EDIT', '8': 'ACTION_REMOVE', '16': 'ACTION_MEMBERS', '32': 'ACTION_RELOAD' }  

  ## Permissions
  WRITE_CAPABILITY        = 'edit_reviewstatuses'

  ## Default Params
  PARAM_DISABLED          = 'disabled'
  PARAM_LABEL             = 'label'
  PARAM_DESCRIPTION       = 'description'
  PARAM_DEFAULT           = 'default'
  PARAM_SELECTED          = 'selected'
  PARAM_HIDDEN            = 'hidden'
  PARAM_END               = 'end'
  
  BOOLEAN_PARAMS          = [PARAM_DISABLED, PARAM_DEFAULT, PARAM_SELECTED, PARAM_HIDDEN, PARAM_END]
  
  VALID_PARAMS            = [PARAM_DISABLED, 
                             PARAM_LABEL, 
                             PARAM_DESCRIPTION, 
                             PARAM_DEFAULT, 
                             PARAM_SELECTED, 
                             PARAM_HIDDEN, 
                             PARAM_END]
  
  REQUIRED_PARAMS         = [PARAM_DISABLED, PARAM_LABEL, PARAM_DEFAULT, PARAM_HIDDEN]

  ## Default Vals
  DEFAULT_NAMESPACE       = 'SA-ThreatIntelligence'
  DEFAULT_OWNER           = 'nobody'
  
  ## Lookup file
  parent                  = os.path.dirname(os.path.dirname(__file__))
  reviewstatusesFile      = os.path.join(parent, 'lookups', 'reviewstatuses.csv')    

  DEFAULT_DISABLED        = '0'
  DEFAULT_DEFAULT         = '0'
  DEFAULT_SELECTED        = '0'
  DEFAULT_HIDDEN          = '0'
  DEFAULT_END             = '0'
  
  PARAM_UNASSIGNED_STANZA = '0'
  PARAM_UNASSIGNED_DICT   = {
                             PARAM_DISABLED: DEFAULT_DISABLED,
                             PARAM_LABEL: 'Unassigned',
                             PARAM_DESCRIPTION: 'An error is preventing the issue from having a valid status assignment',
                             PARAM_DEFAULT: DEFAULT_DEFAULT,
                             PARAM_SELECTED: DEFAULT_SELECTED,
                             PARAM_HIDDEN: DEFAULT_HIDDEN,
                             PARAM_END: DEFAULT_END
                             }

  def setup(self):
      logger.info('Setting up reviewstatuses_rest_handler')
      
      ## set write capability
      self.setWriteCapability(ReviewStatuses.WRITE_CAPABILITY)    
       
      if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:         
          ## Fill required params
          for arg in ReviewStatuses.REQUIRED_PARAMS:
              self.supportedArgs.addReqArg(arg)
              
          ## Fill valid params
          for arg in ReviewStatuses.VALID_PARAMS:
              if arg not in ReviewStatuses.REQUIRED_PARAMS:
                  self.supportedArgs.addOptArg(arg)
              
  @time_function_call
  def handleCreate(self, confInfo):
      """
      Handles creation of a review status
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if ReviewStatuses.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = ReviewStatuses.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload(makeCSV=False)
      
      ## Get the configurations from reviewstatuses.conf
      reviewstatusesDict = self.readConf('reviewstatuses')
      authorizeDict = self.readConf('authorize')
      
      ## Get default statuses
      defaultStatuses = ReviewStatuses.getSpecialStatuses(reviewstatusesDict, type=ReviewStatuses.PARAM_DEFAULT)

      name = self.callerArgs.id
      args = self.callerArgs.data
      
      ## Check name
      if name is None or len(name) == 0:
          raise admin.ArgValidationException('The name (stanza) of the status must not be empty')
      
      ## Make sure the item is not '0'
      ## '0' is reserved for the Unassigned status
      if name == '0':
          raise admin.ArgValidationException('The name (stanza) of the status must not be 0 (this is reserved for the Unassigned status)')
      
      ## Make sure the item does not already exist
      ## This should not be possible based on getUID, but no hurt in double checking
      if name in reviewstatusesDict:
          raise admin.AlreadyExistsException('A reviewstatuses.conf entry already exists for status ID %s' % (name))
      
      ## Get the field values
      disabled = _getFieldValue(args, ReviewStatuses.PARAM_DISABLED)
      label = _getFieldValue(args, ReviewStatuses.PARAM_LABEL)
      description = _getFieldValue(args, ReviewStatuses.PARAM_DESCRIPTION)
      default = _getFieldValue(args, ReviewStatuses.PARAM_DEFAULT)      
      selected = _getFieldValue(args, ReviewStatuses.PARAM_SELECTED)
      hidden = _getFieldValue(args, ReviewStatuses.PARAM_HIDDEN)
      end = _getFieldValue(args, ReviewStatuses.PARAM_END)
      
      ## Add the field values to a configuration dictionary (that will be verified)
      conf = entity.getEntity('configs/conf-reviewstatuses', '_new', sessionKey=self.getSessionKey())
        
      conf.namespace = self.appName # always save things to SOME app context.
      conf.owner = self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"
        
      conf['name'] = name
        
      _addToDictIfNonNull(conf, ReviewStatuses.PARAM_DISABLED, disabled)
      _addToDictIfNonNull(conf, ReviewStatuses.PARAM_LABEL, label)
      _addToDictIfNonNull(conf, ReviewStatuses.PARAM_DESCRIPTION, description)
      _addToDictIfNonNull(conf, ReviewStatuses.PARAM_DEFAULT, default)
      _addToDictIfNonNull(conf, ReviewStatuses.PARAM_SELECTED, selected) 
      _addToDictIfNonNull(conf, ReviewStatuses.PARAM_HIDDEN, hidden) 
      _addToDictIfNonNull(conf, ReviewStatuses.PARAM_END, end)
      
      ## Check the configuration
      try:
          ReviewStatuses.checkConf(conf, name, defaultStatuses=defaultStatuses, checkDefault=True)
          
      except InvalidConfigException as e:
          f = "The configuration for the new review status '%s' is invalid and could not be created: %s" % (name, str(e))
          logger.error(f)
          
          e = "The configuration for the new review status is invalid and could not be created: %s" % (str(e))
          raise admin.ArgValidationException(e)
        
      ## Write out an update to the reviewstatuses config file
      entity.setEntity(conf, sessionKey=self.getSessionKey())

      logger.info('Successfully added review status: %s' % (label))
      
      ## Create new transitions
      transitions = []
      
      transitions.extend(ReviewStatuses.makeTransitions('0', name, toOnly=True))
      
      for stanza in reviewstatusesDict:
          if stanza != 'default' and stanza != '0':
              transitions.extend(ReviewStatuses.makeTransitions(name, stanza))
      
      transitions.sort()
            
      ## Write out an update to the authorize config file
      conf = entity.getEntity('configs/conf-authorize', '_new', sessionKey=self.getSessionKey())

      conf.namespace = self.appName # always save things to SOME app context.
      conf.owner = self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"

      conf['disabled'] = '0'

      with TimeLogger("setting_transitions", logger):
          for transition in transitions:
              if transition in authorizeDict:
                  logger.warn('An authorize.conf entry already exists for %s' % (transition))
              
              else:
                  conf['name'] = transition
                  entity.setEntity(conf, sessionKey=self.getSessionKey())
                  logger.info('Successfully added transition %s' % (transition))
      
      ## Reload reviewstatuses (makeCSV)
      self.handleReload()
      
      logger.info('%s completed successfully' % (actionStr))
      
  @time_function_call
  def handleList(self, confInfo):      
      """
      Handles listing of a review statuses
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if ReviewStatuses.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = ReviewStatuses.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload(makeCSV=False)
       
      ## Get the configurations from reviewstatuses.conf
      reviewstatusesDict = self.readConfCtx('reviewstatuses')
      authorizeDict = self.readConf('authorize')
      
      ## Get all correlations searches and provide the relevant options
      if reviewstatusesDict != None:
          ## Get default count
          defaultCount = len(ReviewStatuses.getSpecialStatuses(reviewstatusesDict, type=ReviewStatuses.PARAM_DEFAULT))
          
          ## Get end count
          endCount = len(ReviewStatuses.getSpecialStatuses(reviewstatusesDict, type=ReviewStatuses.PARAM_END))
          
          ## Check default count
          if defaultCount != 1:
              logger.error("The reviewstatuses.conf configurations are invalid because %s default statuses are set; should be one" % (defaultCount))
          
          ## Check end count
          if endCount < 1:
              logger.error("The reviewstatuses.conf configurations are invalid because %s end statuses are set; should be one" % (endCount))
          
          ## Check each conf
          for stanza, settings in reviewstatusesDict.items():
              ## Make sure the item is not '0'
              ## '0' is reserved for the Unassigned status
              if stanza != 'default' and stanza != '0':
                  try:
                      ## Check config
                      ReviewStatuses.checkConf(settings, stanza, confInfo)
                      
                      ## Check transitions
                      ReviewStatuses.checkTransitions(stanza, reviewstatusesDict, authorizeDict)
                  
                  except MissingTransitionException as e:
                      for exc in e.transitions:
                          logger.error("The configuration for status ID '%s' is invalid: %s" % ( stanza, str(exc)))
                          
                  except InvalidConfigException as e:
                      logger.error("The configuration for status ID '%s' is invalid: %s" % ( stanza, str(e)) )                  
          
          ## Add static "Unassigned"
          for key, val in ReviewStatuses.PARAM_UNASSIGNED_DICT.items():
              confInfo[ReviewStatuses.PARAM_UNASSIGNED_STANZA].append(key, val)
           
      logger.info('%s completed successfully' % (actionStr))
         
  @time_function_call
  def handleReload(self, confInfo=None, makeCSV=True):
      """
      Handles refresh/reload of the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if ReviewStatuses.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = ReviewStatuses.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))

      logger.info('Refreshing reviewstatuses configurations via properties endpoint')
      try:
          refreshInfo = entity.refreshEntities('properties/reviewstatuses', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh reviewstatuses configurations via properties endpoint: %s' % str(e))
        
      logger.info('Refreshing authorize configurations via properties endpoint')    
      try:
          refreshInfo = entity.refreshEntities('properties/authorize', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh authorize configurations via properties endpoint: %s' % str(e))
       
      if makeCSV:
          self.makeCSV(ReviewStatuses.reviewstatusesFile) 
          self.reloadCorrelationSearches()
       
      logger.info('%s completed successfully' % (actionStr))
  
  ## CorrelationSearches.makeCSV
  @time_function_call
  def reloadCorrelationSearches(self):
      """
      Handles refresh/reload of correlationsearches configuration options.  Will also call CorrelationSearches.makeCSV.
      """      
      logger.info('Refreshing correlationsearches configurations via alerts/correlationsearches endpoint')
      
      try:
          refreshInfo = rest.simpleRequest('alerts/correlationsearches/_reload', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh correlationsearches configurations via alerts/correlationsearches endpoint: %s' % str(e))
  
  ## ReviewStatuses.makeCSV
  @time_function_call
  def makeCSV(self, reviewstatusesFile, reviewstatusesDict=None):
      logger.info("Creating reviewstatuses file '%s'" % (reviewstatusesFile))
      
      if reviewstatusesDict is None:
           ## Get the configurations from correlationsearches.conf
           reviewstatusesDict = self.readConf('reviewstatuses')
           
      if reviewstatusesDict is not None:
          ## Get reviewstatusesFileData
          try:
              reviewstatusesFH = open(reviewstatusesFile, 'rU')
              reviewstatusesFileData = reviewstatusesFH.read()
              
          except Exception as e:
              logger.warn("Could not create handle for file '%s': %s" % (reviewstatusesFile, str(e)))
              reviewstatusesFileData = ''

          ## Initialize header
          header = ['status',
                    ReviewStatuses.PARAM_LABEL,
                    ReviewStatuses.PARAM_DESCRIPTION,
                    ReviewStatuses.PARAM_DISABLED,
                    ReviewStatuses.PARAM_DEFAULT,
                    ReviewStatuses.PARAM_SELECTED,
                    ReviewStatuses.PARAM_HIDDEN,
                    ReviewStatuses.PARAM_END]
          
          ## Initialize temporary file
          reviewstatusesMH = os.tmpfile()

          ## Write header
          csv.writer(reviewstatusesMH, lineterminator='\n').writerow(header)
          
          ## Create DictWriter
          reviewstatusesResults = csv.DictWriter(reviewstatusesMH, header, lineterminator='\n')
          
          ## Iterate reviewstatuses
          for stanza, settings in reviewstatusesDict.items():
              
              if stanza != 'default':
                  reviewstatus = {}
                  
                  reviewstatus['status'] = stanza
                  
                  for key, val in settings.items():
                      if val is None:
                          val = ''
                          
                      if key in header:
                          reviewstatus[key] = val
                          
                  reviewstatusesResults.writerow(reviewstatus)
                  
          ## Seek
          reviewstatusesMH.seek(0)
          
          ## Mem Data
          reviewstatusMemData = reviewstatusesMH.read()
          
          if reviewstatusMemData == reviewstatusesFileData:
              logger.info("File %s does not require change; exiting" % (reviewstatusesFile))
              reviewstatusesFH.close()
              reviewstatusesMH.close()
                      
          else:
              logger.info("File %s requires updating" % (reviewstatusesFile))
              
              reviewstatusesTempFile = reviewstatusesFile + '.tmp'
              reviewstatusesTempFH = False
              
              try:
                  reviewstatusesTempFH = open(reviewstatusesTempFile, 'w')
                  
              except Exception as e:
                  logger.critical("Could not create handle for temporary file '%s': %s" % (reviewstatusesTempFile, str(e)))
                  
              if reviewstatusesTempFH:
                  logger.info("Writing temporary file %s" % (reviewstatusesTempFile))
                  reviewstatusesTempFH.write(reviewstatusMemData)
                  reviewstatusesMH.close()
                  reviewstatusesTempFH.close()
                  logger.info("Moving temporary file %s to %s" % (reviewstatusesTempFile, reviewstatusesFile))
                  
                  try:
                      shutil.move(reviewstatusesTempFile, reviewstatusesFile)
                  
                  except Exception as e:
                      logger.critical("Could not move file from %s to %s: %s" % (reviewstatusesTempFile, reviewstatusesFile, str(e)))
      
      else:
          logger.critical("Review statuses dictionary is None; cannot makeCSV")                  
                    
  @time_function_call
  def correctMissingTransition(self, transition, save=True):
      """
      Create the messing transition and return the created transition.
      """
      
      logger.info("Transition %s does not exist but should, it will be created" % (transition) )
      
      # Get the _new entity in order to start editing
      conf = entity.getEntity('configs/conf-authorize', '_new', sessionKey=self.getSessionKey())

      # Set the namespace and owner
      conf.namespace = self.appName
      conf.owner = ReviewStatuses.DEFAULT_OWNER
      
      # Set the transition
      conf['name'] = transition
      conf['disabled'] = '1'
      
      # Save the transition
      if save:
          entity.setEntity(conf, sessionKey=self.getSessionKey())
          logger.info('Successfully added transition %s' % (transition))
      else:
          logger.info('Preparing the creation of the missing transition %s; save is deferred until other edits are complete' % (transition))
      
      return conf
                    
  @time_function_call
  def handleEdit(self, confInfo):
      """
      Handles edits to the configuration options
      """
      
      ## Get requested action
      actionStr = str(self.requestedAction)
      if ReviewStatuses.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = ReviewStatuses.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload(makeCSV=False)
      
      ## Get the configurations from reviewstatuses.conf
      reviewstatusesDict = self.readConf('reviewstatuses')
      
      ## Get default review status(es)
      defaultStatuses = ReviewStatuses.getSpecialStatuses(reviewstatusesDict, type=ReviewStatuses.PARAM_DEFAULT)
      
      name = self.callerArgs.id
      args = self.callerArgs
      
      if name is not None:
          ## Make sure the item is not '0'
          ## '0' is reserved for the Unassigned status
          if name == '0':
              raise admin.ArgValidationException('The name (stanza) of the status must not be 0 (this is reserved for the Unassigned status)')
      
          try:
              conf = entity.getEntity('configs/conf-reviewstatuses', name, sessionKey=self.getSessionKey())
              
          except ResourceNotFound:
              raise admin.NotFoundException("A status with the given name '%s' could not be found" % (name))
          
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
                  namespace = val['app']
            
              if val.has_key('owner') and val['owner'] is not None and len(val['owner']) > 0:
                  owner = val['owner']
                    
      if namespace is None or len(namespace) == 0:
          namespace = ReviewStatuses.DEFAULT_NAMESPACE
            
      if owner is None or len(owner) == 0:
          owner = ReviewStatuses.DEFAULT_OWNER
          
      conf.namespace = namespace
      conf.owner = owner
            
      ## Check the resulting configuration
      try:
          ReviewStatuses.checkConf(conf, name, defaultStatuses=defaultStatuses, checkDefault=True)
          
      except InvalidConfigException as e:
          f = "The edit attempt for review status '%s' produced an invalid configuration: %s" % (name, str(e))
          logger.error(f)
          
          e = "The review status edit attempt produced an invalid configuration: %s" % (str(e))
          raise admin.ArgValidationException(e)
      
      ## Retain is_disabled
      status_disabled = ReviewStatuses.str_to_bool(conf['disabled'])
            
      ## Enable/Disable transitions
      transitions = []
      
      transitions.extend(ReviewStatuses.makeTransitions('0', name, toOnly=True))
      
      for stanza in reviewstatusesDict:
          if stanza != 'default' and stanza != '0':
              transitions.extend(ReviewStatuses.makeTransitions(name, stanza))
      
      transitions.sort()
      
      # Get the existing set of transition capabilities; we are going to store these so that we don't have to call
      # getEntity on each capability since this takes a long time (about 20 seconds each)
      existing_transitions = entity.getEntities('configs/conf-authorize', sessionKey=self.getSessionKey(), count=-1)
      
      ## Write out an update to the authorize config file
      for transition in transitions:
          
          changed = False
          
          # Get the entry that we are editing
          if transition in existing_transitions:
              transition_conf = existing_transitions[transition]
          else:
              # Uh oh, the transition wasn't found. Go ahead and create it.
              transition_conf = self.correctMissingTransition(transition, save=False)
              
              # If the transition was not returned, then skip this entry.
              if transition_conf is None:
                  continue
              
              changed = True
          
          transition_conf.namespace = self.appName
          transition_conf.owner = ReviewStatuses.DEFAULT_OWNER
          
          ## Disable only transitions to the disabled status
          if status_disabled and transition.find('to_%s' % (name)) != -1:
              action = 'disabled'
              
              # Note that we are changing the value
              if str(transition_conf['disabled']) != '1':
                  changed = True
                  transition_conf['disabled'] = '1'
              
          else:
              action = 'enabled'
              
              # Note that we are changing the value
              if str(transition_conf['disabled']) != '0':
                  changed = True
                  transition_conf['disabled'] = '0'
              
          # Set the settings if they have changed; try to avoid performing the changes unless we need to since this is a slow operation
          if changed:
              with TimeLogger( ("Set %s transition in handleEdit: %s" % (action, transition)), logger):
                  entity.setEntity(transition_conf, sessionKey=self.getSessionKey())
              logger.info('Successfully %s transition: %s' % (action, transition))
      
      ## Write out an update to the reviewstatuses config file
      ## Note that we are doing this after setting the transitions 
      with TimeLogger("setting entity in handleEdit", logger):
          entity.setEntity(conf, sessionKey=self.getSessionKey())
      
      logger.info("Successfully updated review status id %s" % (name))
      
      ## Reload reviewstatuses (makeCSV)
      self.handleReload()
      
      logger.info('%s completed successfully' % (actionStr))
          
  def handleRemove(self, confInfo):
      pass        
  
  @staticmethod
  def getUID(reviewstatuses=[]):
      """
      Returns a unique identifier to be used as a stanza name
      """
      uid = 0
      
      statusInts = []
      
      for reviewstatus in reviewstatuses:
          try:
              statusInt = int(reviewstatus)
              if statusInt > 0:
                  statusInts.append(statusInt)
                  
          except:
              pass
      
      if len(statusInts) == 0:
          return 1
      
      else:
          statusInts.sort()
          uid = statusInts[-1] + 1
      
      return uid 
        
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
  def getSpecialStatuses(confDict=None, type=PARAM_DEFAULT):
      logger.info('Retrieving statuses with %s set' % type)
      statuses = []
      
      if confDict is not None:
          for stanza, settings in confDict.items():
              if stanza != "default":
                  if type == ReviewStatuses.PARAM_DEFAULT:
                      is_default = False
                      
                      for key, val in settings.items():
                          if val is None:
                              val = ''
                         
                          if key == ReviewStatuses.PARAM_DEFAULT:
                              try:
                                  is_default = ReviewStatuses.str_to_bool(val)
                         
                              except:
                                  is_default = False
                                  
                      if is_default:
                          statuses.append(stanza)
                  
                  elif type == ReviewStatuses.PARAM_END:
                      is_end = False
                      
                      for key, val in settings.items():
                          if val is None:
                              val = ''
                              
                          if key == ReviewStatuses.PARAM_END:
                              try:
                                  is_end = ReviewStatuses.str_to_bool(val)
                                  
                              except:
                                  is_end = False
                                  
                      if is_end:
                          statuses.append(stanza)        
                
          
      else:
          logger.critical('Could not retrieve statuses with %s set; confDict is None' % type)
      
      logger.info('Successfully retrieved status(es) with %s set: %s' % (type, statuses))
      
      return statuses
              
  @staticmethod
  def checkConf(settings, stanza=None, confInfo=None, defaultStatuses=[], checkDefault=False, throwExceptionOnError=False):
      """
      Checks the settings and raises an exception if the configuration is invalid.
      """ 
      ## Below is a list of the required fields. The entries in this list will be removed as they
      ## are observed. An empty list at the end of the config check indicates that all necessary
      ## fields where provided.
      required_fields = ReviewStatuses.REQUIRED_PARAMS[:]
      
      if stanza is not None and confInfo is not None:
          # Add each of the settings
          for key, val in settings.items():
              ## Set val to empty if None
              if val is None:
                  val = ''
                  
              if key in ReviewStatuses.VALID_PARAMS:
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
          
      ## Check each of the settings individually
      logger.info("Checking general settings for the '%s' review status" % (stanza))
      for key, val in settings.items():
          ## Set val to empty if None
          if val is None:
              val = ''
          
          ## Check the disabled/selected value
          if key in ReviewStatuses.BOOLEAN_PARAMS:
              try:
                  ReviewStatuses.str_to_bool(val)
                  
                  ## Remove the field from the list of required fields
                  try:
                      required_fields.remove(key)
                      
                  except ValueError:
                      pass # Field not available, probably because it is not required
                      
              except ValueError:
                  raise InvalidParameterValueException(key, val, "must be a valid boolean")
                  
          elif key in ReviewStatuses.REQUIRED_PARAMS:
              ## Remove the field from the list of required fields
              try:
                  required_fields.remove(key)
                      
              except ValueError:
                  pass # Field not available, probably because it is not required
                      
          elif key in ReviewStatuses.VALID_PARAMS:
              pass
                                 
          ## Key is eai
          elif key.startswith(admin.EAI_META_PREFIX):
              pass
               
          ## Key is not proper
          else:
              if throwExceptionOnError:
                  raise UnsupportedParameterException()
              
              else:
                  logger.warn("The configuration for the '%s' review status contains an unsupported parameter: %s" % (stanza, key))

      ## Error if some of the required fields were not provided
      if len(required_fields) > 0:
          raise InvalidConfigException('The following fields must be defined in the configuration but were not: ' + ', '.join(required_fields).strip())
   
      ## Error if checkDefault and...
      if checkDefault:
          ## disabled
          if ReviewStatuses.PARAM_DISABLED in settings:
              disabled = ReviewStatuses.str_to_bool(settings[ReviewStatuses.PARAM_DISABLED])
          else:
              disabled = ReviewStatuses.str_to_bool(ReviewStatuses.DEFAULT_DISABLED)
          
          ## default    
          if ReviewStatuses.PARAM_DEFAULT in settings:    
              default = ReviewStatuses.str_to_bool(settings[ReviewStatuses.PARAM_DEFAULT])
          
          else:
              default = ReviewStatuses.str_to_bool(ReviewStatuses.DEFAULT_DEFAULT)
          
          ## end    
          if ReviewStatuses.PARAM_END in settings:       
              end = ReviewStatuses.str_to_bool(settings[ReviewStatuses.PARAM_END])
              
          else:
              end = ReviewStatuses.str_to_bool(ReviewStatuses.DEFAULT_END)
        
          ## 1. No disabled defaults
          if default and disabled:
              raise InvalidConfigException("Default review statuses cannot be disabled.  If you want to disable this status, then unset default.")
          
          ## 2. One default only
          if default and stanza not in defaultStatuses and len(defaultStatuses) >= 1:
              raise InvalidConfigException("Only one default status allowed")
          
          ## 3. No end defaults
          if default and end:
              raise InvalidConfigException("Default review status cannot also be end status.  If you want this status to be default, then unset end.")

  @staticmethod
  def makeTransitions(statusA, statusB, toOnly=False):
      transitions = []
      
      if statusA != statusB:
          transitions.append('capability::transition_reviewstatus-%s_to_%s' % (statusA, statusB))
          if not toOnly:
              transitions.append('capability::transition_reviewstatus-%s_to_%s' % (statusB, statusA))
      
      return transitions
  
  @staticmethod
  def checkTransitions(status, reviewstatusesDict, authorizeDict):
      transitions = []
      missingTransitions = []

      transitions.extend(ReviewStatuses.makeTransitions('0', status, toOnly=True))
      
      for stanza in reviewstatusesDict:
          if stanza != "default" and stanza != '0':        
              transitions.extend(ReviewStatuses.makeTransitions(status, stanza))
              
      for transition in transitions:
          if transition not in authorizeDict:
              missingTransitions.append('Missing capability ' + transition)
                  
      if len(missingTransitions) > 0:
          raise MissingTransitionException(missingTransitions)
      
                          
# initialize the handler
admin.init(ReviewStatuses, admin.CONTEXT_APP_AND_USER)