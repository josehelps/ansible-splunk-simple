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
import time

from splunk import ResourceNotFound
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('transitioners_rest_handler')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'transitioners_rest_handler.log']), maxBytes=25000000, backupCount=5)
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
            diff_string = str( round( diff / 60, 2)) + " minutes"
        else:
            diff_string = str( round( diff, 2) ) + " seconds"
        
        logger.debug( "Notable Event Status::%s, duration=%s" % (fx.__name__, diff_string)  )
        
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

          
class Transitioners(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  ## admin.py constants
  REQUESTED_ACTIONS = { '1': 'ACTION_CREATE', '2': 'ACTION_LIST', '4': 'ACTION_EDIT', '8': 'ACTION_REMOVE', '16': 'ACTION_MEMBERS', '32': 'ACTION_RELOAD' }  
  
  ## Permissions
  WRITE_CAPABILITY = 'edit_reviewstatuses'
  
  ## Default Params
  PARAM_DISABLED = 'disabled'
  PARAM_ENABLED = 'enabled'
  PARAM_IMPORT_ROLES = 'importRoles'
  PARAM_IMPORTED_ROLES = 'imported_roles'
  PARAM_CAPABILITIES = 'capabilities'
  PARAM_IMPORTED_CAPABILITIES = 'imported_capabilities'
  
  REQUIRED_PARAMS = []
  VALID_PARAMS = ['transition_reviewstatus*', PARAM_IMPORTED_ROLES, PARAM_CAPABILITIES, PARAM_IMPORTED_CAPABILITIES]
  
  ## Default Vals
  transitionRE = re.compile('^(?:capability::)?(transition_reviewstatus-\d+_to_\d+)$')
  roleRE = re.compile('^role_(.+)$')
  
  def setup(self):
      logger.info('Setting up transitions_rest_handler')
      
      ## set write capability
      self.setWriteCapability(Transitioners.WRITE_CAPABILITY)

      if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:         
          ## Fill required params
          for arg in Transitioners.REQUIRED_PARAMS:
              self.supportedArgs.addReqArg(arg)
              
          ## Fill valid params
          for arg in Transitioners.VALID_PARAMS:
              if arg not in Transitioners.REQUIRED_PARAMS:
                  self.supportedArgs.addOptArg(arg)
      
  def handleList(self, confInfo):      
      """
      Handles listing of a transition
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Transitioners.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Transitioners.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      self.handleReload(refreshProvidersServices=False)
       
      ## Get the configurations from authorize.conf
      authorizeDict = self.readConf('authorize')
      
      ## Get all transitions and provide the relevant options
      if authorizeDict != None:
          ## Check each conf
          for stanza, settings in authorizeDict.items():
              roleMatch = Transitioners.roleRE.match(stanza)
              
              if roleMatch:
                  try:
                      ## Check config
                      Transitioners.checkConf(settings, roleMatch.group(1), confInfo, authorizeDict)
                          
                  except InvalidConfigException as e:
                      logger.error("The configuration for role '%s' is invalid: %s" % ( stanza, str(e)) )                  

      logger.info('%s completed successfully' % (actionStr))
         
  @time_function_call
  def handleReload(self, confInfo=None, refreshProvidersServices=True):
      """
      Handles refresh/reload of the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Transitioners.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Transitioners.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))

      logger.info('Refreshing authorize configurations via properties endpoint')
      
      # Refresh the authorize endpoint: this will make it such that the calls to readConf for authorize.conf will return the correct results
      try:
          refreshInfo = entity.refreshEntities('properties/authorize', sessionKey=self.getSessionKey())
      except Exception as e:
          logger.warn('Could not refresh authorize configurations via properties endpoint: %s' % str(e))
          
      # Refresh the internal cached authentication capabilities data: this will make the /authorization/roles return the correct data
      if refreshProvidersServices:
          try:
              refreshInfo = entity.refreshEntities('/authentication/providers/services', sessionKey=self.getSessionKey())
          except Exception as e:
              logger.warn('Could not refresh authorize configurations via properties endpoint: %s' % str(e))
 
      logger.info('%s completed successfully' % (actionStr))
            
  @time_function_call
  def handleEdit(self, confInfo):
      """
      Handles edits to the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if Transitioners.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = Transitioners.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload( refreshProvidersServices=False )
      
      authorizeDict = self.readConf('authorize')
      
      name = self.callerArgs.id
      args = self.callerArgs
      
      namespace = self.appName # always save things to SOME app context.
      owner = self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"
          
      if name is not None:
          ## Prepend 'role_' to name if not already there
          if not name.startswith('role_'):
              name = 'role_' + name
          
          try:
              conf = entity.getEntity('configs/conf-authorize', name, namespace=namespace, owner=owner, sessionKey=self.getSessionKey())
              
          except ResourceNotFound:
              raise admin.NotFoundException("The role '%s' could not be found" % (name))
          
      else:
          # Stop if no name was provided
          raise admin.ArgValidationException("No name provided")
   
      ## Get system transitions
      systemTransitions = Transitioners.getTransitions(authorizeDict, enabledOnly=False)
      
      ## Create the resulting configuration that would be persisted if the settings provided are applied
      ## This rest handler supports the addition of arguments based on convention; therefore we merge args a little differently
      for arg in args:
          if arg in systemTransitions:
              conf[arg] = args[arg][0]
   
      try:
          ## Check config
          Transitioners.checkConf(conf, name, authorizeDict=authorizeDict)
               
      except InvalidConfigException as e:
          e = "The edit attempt for role '%s' produced an invalid configuration: %s" % (name, str(e))
          logger.error(e)
          raise admin.ArgValidationException(e)
      
      ## Write out an update to the authorize config file
      entity.setEntity(conf, sessionKey=self.getSessionKey())
      
      logger.info("Successfully updated role '%s'" % (name))
      
      ## Reload transitions
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
  def checkConf(settings, stanza=None, confInfo=None, authorizeDict={}, throwExceptionOnError=False):
      """
      Checks the settings and raises an exception if the configuration is invalid.
      """            
      if stanza is not None and confInfo is not None:
          role = stanza
          stanza = 'role_' + stanza
      
          capabilities = Transitioners.getTransitions(authorizeDict, stanza)
          importedCapabilities = []
          
          # Add each of the settings
          for key, val in settings.items():              
              ## Set val to empty if None
              if val is None:
                  val = ''
                      
              if key == Transitioners.PARAM_IMPORT_ROLES:
                  val = val.split(';')
                  confInfo[role].append(Transitioners.PARAM_IMPORTED_ROLES, val)
                  
              ## Key is eai; userName/appName
              elif key.startswith('eai') and key != 'eai:acl':
                  confInfo[role].append(key, val)
                  
              ## Key is eai; Set meta  
              elif key.startswith('eai'):
                  confInfo[role].setMetadata(key, val)
                  
              ## Key is not proper
              else:
                  pass
          
          importRoles = []
          
          # get the roles
          importRoles = Transitioners.traverseRoles(stanza, authorizeDict)
                    
          for tempRole in importRoles:
              
              # Get the imported capabilities (transitions) for each role
              tempImportedCapabilities = Transitioners.getTransitions(authorizeDict, 'role_' + tempRole)
              
              # Add each imported capability if it is not already present
              for importedCapability in tempImportedCapabilities:
                  if importedCapability not in importedCapabilities:
                      importedCapabilities.append(importedCapability)
          
          # Add the imported capabilities to the given role for the REST endpoint to display
          confInfo[role].append(Transitioners.PARAM_IMPORTED_CAPABILITIES, importedCapabilities)
          
          tempCapabilities = capabilities[:]
          
          for capability in tempCapabilities:
              if capability in importedCapabilities:
                  capabilities.remove(capability)
          
          confInfo[role].append(Transitioners.PARAM_CAPABILITIES, capabilities)

      ## Check each of the settings individually
      logger.info("Checking general settings for role '%s'" % (stanza))
      
      systemTransitions = Transitioners.getTransitions(authorizeDict, enabledOnly=False)
      
      for key, val in settings.items():
          transitionMatch = Transitioners.transitionRE.match(key)
          
          ## Set val to empty if None
          if val is None:
              val = ''
          
          ## Verify the key is a transition
          if transitionMatch and key in systemTransitions:
              if val == Transitioners.PARAM_DISABLED or val == Transitioners.PARAM_ENABLED:
                  pass
              
              else:
                  raise InvalidParameterValueException(key, val, "must be '%s' or '%s'" % (Transitioners.PARAM_DISABLED, Transitioners.PARAM_ENABLED))
        
          elif transitionMatch:
              if throwExceptionOnError:
                  raise UnsupportedParameterException()
              
              else:
                  logger.warn("The '%s' role contains an unsupported parameter: %s" % (stanza, key))
          
          else:
              pass
      
  @staticmethod
  def getTransitions(authorizeDict, role=None, enabledOnly=True):
      transitions = []
      transitions4Role = []
      
      # If the dictionary of authorize.conf was provided, then pull out the transitions
      if authorizeDict is not None:
          
          # Iterate through each entry and find the transitions
          for stanza, settings in authorizeDict.items():
              
              # See if this entry is a transition capability
              transitionMatch = Transitioners.transitionRE.match(stanza)
              
              # If the transition matches, then add it
              if transitionMatch:
                  
                  # Add the item immediately if we are including the entries regardless of whether they are enabled
                  if not enabledOnly:
                      transitions.append(transitionMatch.group(1))
                      
                  # If the disabled stanza was not found, then assume the item is enabled and add it
                  elif not Transitioners.PARAM_DISABLED in settings:
                      transitions.append(transitionMatch.group(1))
                      
                  # Add the item if it is disabled
                  elif Transitioners.PARAM_DISABLED in settings:
                      
                      # Determine if the transition is enabled
                      val = settings[Transitioners.PARAM_DISABLED]
                      val = Transitioners.str_to_bool(val)
                      
                      # Add the item to the list if it is enabled
                      if val == False:
                          transitions.append(transitionMatch.group(1))
          
          if role is None:
              logger.debug("Transitions: " + str(len(transitions)))
              return transitions
            
          else:
              
              # Iterate through each entry and find the transitions
              for stanza, settings in authorizeDict.items():
                  
                  # See if this entry is for a role
                  roleMatch = Transitioners.roleRE.match(stanza)
    
                  # Process the entry if it is the role we are looking for
                  if roleMatch and stanza == role:
                      
                      # Iterate through the auth dictionary entry for the role and add the transitions that it has enabled
                      for key, val in settings.items():
                          
                          # If the transition is in the list of valid transitions, then add it
                          if key in transitions:
                              
                              # If we are adding add transitions, then go a ahead and add it
                              if not enabledOnly:
                                  transitions4Role.append(key)
                              
                              # If we are adding only enabled transitions, then add it if is enabled
                              elif enabledOnly and val == Transitioners.PARAM_ENABLED:
                                  transitions4Role.append(key)
                              
                              else:
                                  pass
                      
            
              logger.debug( "Transitions(%s): %d" % ( role, len(transitions) ) )
              return transitions4Role
                  
  @staticmethod
  def getImportedRoles(role, rolesDict):
    importedRoles = []
    
    if role is not None and rolesDict is not None:
        for stanza, settings in rolesDict.items():
            if stanza == role:
                for key, val in settings.items():
                    if key == Transitioners.PARAM_IMPORT_ROLES:
                        importedRoles = val.split(';')
                        break
                    
    return importedRoles
    
  @staticmethod
  def traverseRoles(role, rolesDict, roles=None):
    """
    Traverse the roles and create a complete list of the roles that are imported.
    
    Arguments:
    role        -- The role that we are looking up
    rolesDict   -- The dictionary from the 
    roles       -- The roles we have already traversed, used to determine if already processed the item (to prevented infinite loops)
    """

    # Initialize the roles to an empty list if it was not provided
    if roles is None:
        roles = []
    
    # Get the imported roles
    importedRoles = Transitioners.getImportedRoles(role, rolesDict)
    
    # For each imported role, get the roles imported by each role
    for importedRole in importedRoles:
        
        # If the role is not already in the list (i.e. has not yet been seen, then process it)
        if importedRole not in roles:
            
            # Append the given role (provided it isn't the role we are looking for)
            if importedRole != role:
                roles.append(importedRole)
            
            # Get the imported roles list
            traversedRoles = Transitioners.traverseRoles('role_' + importedRole, rolesDict, roles)
            
            # Add the unique set of roles
            for r in traversedRoles:
                if r not in roles:
                    roles.append( r )
            
    # Return the roles
    return roles
                        
                        
# initialize the handler
admin.init(Transitioners, admin.CONTEXT_APP_AND_USER)