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

from postprocess import *
from splunk import ResourceNotFound
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('postprocess_rest_handler')
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'postprocess_rest_handler.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()


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

          
class PostProcessRH(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  ## admin.py constants
  REQUESTED_ACTIONS = { '1': 'ACTION_CREATE', '2': 'ACTION_LIST', '4': 'ACTION_EDIT', '8': 'ACTION_REMOVE', '16': 'ACTION_MEMBERS', '32': 'ACTION_RELOAD' }
  
  ## Permissions
  WRITE_CAPABILITY = 'edit_postprocess'

  def setup(self):
      logger.info('Setting up postprocess_rest_handler')
      
      ## set write capability
      self.setWriteCapability(PostProcessRH.WRITE_CAPABILITY)       
       
      if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:         
          ## Fill required params
          for arg in PostProcess.REQUIRED_PARAMS:
              self.supportedArgs.addReqArg(arg)
              
          ## Fill valid params
          for arg in PostProcess.VALID_PARAMS:
              if arg not in PostProcess.REQUIRED_PARAMS:
                  self.supportedArgs.addOptArg(arg)
  
  def handleCreate(self, confInfo):
      """
      Handles creation of a correlation search
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if PostProcessRH.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = PostProcessRH.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      self.handleReload()
      
      ## Get list of valid saved searches
      savedsearches = self.getSavedSearches()

      name = self.callerArgs.id
      args = self.callerArgs.data
      
      # Make sure the name is not empty
      if not name or len(name) == 0:
          raise admin.ArgValidationException("The name of the post process must not be empty")
      
      # Make sure the item does not already exist
      if name in self.readConf('postprocess'):
          raise admin.AlreadyExistsException("A post process entry already exists for %s" % (name))
      
      ## Get the field values
      savedsearch = _getFieldValue(args, PostProcess.PARAM_SAVEDSEARCH)
      postprocess = _getFieldValue(args, PostProcess.PARAM_POSTPROCESS)
      
      ## Add the field values to a configuration dictionary (that will be verified)
      conf = entity.getEntity('configs/conf-postprocess', '_new', sessionKey=self.getSessionKey())
    
      conf.namespace = self.appName # always save things to SOME app context.
      conf.owner = self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"
      
      conf['name'] = name

      _addToDictIfNonNull(conf, PostProcess.PARAM_SAVEDSEARCH, savedsearch)
      _addToDictIfNonNull(conf, PostProcess.PARAM_POSTPROCESS, postprocess)
      
      ## Check the configuration
      try:
          PostProcess.checkConf(conf, name, savedsearches=savedsearches)
      
      except InvalidConfigException as e:
          e = "The configuration for the new post process '%s' is invalid and could not be created: %s" % (name, str(e))
          logger.error(e)
          raise admin.ArgValidationException(e)
    
      # Write out an update to the config file
      entity.setEntity(conf, sessionKey=self.getSessionKey())
      
      logger.info('Successfully added post process: %s' % (name))
      
      ## Reload PostProcess (makeCSV)
      self.handleReload()
      
      logger.info('%s completed successfully' % (actionStr))
    
  def handleList(self, confInfo):      
      """
      Handles listing of a correlation search
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if PostProcessRH.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = PostProcessRH.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh - Commented out per SOLNPCI-868
      #self.handleReload()

      ## Get the configurations from postprocess
      postprocessDict = self.readConfCtx('postprocess')
      
      ## Get list of valid saved searches
      savedsearches = self.getSavedSearches()
      
      ## Get all correlations searches and provide the relevant options
      if postprocessDict is not None: 
          
          ## Check each conf
          for stanza, settings in postprocessDict.items():
              if stanza != 'default':
                  try:
                      ## Check config
                      PostProcess.checkConf(settings, stanza, confInfo, savedsearches)
                   
                  except InvalidConfigException as e:
                      logger.error( "The configuration for the '%s' post process is invalid: %s" % ( stanza, str(e)) )                  
             
      logger.info('%s completed successfully' % (actionStr) ) 
              
  def handleReload(self, confInfo=None):
      """
      Handles refresh/reload of the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if PostProcessRH.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = PostProcessRH.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))

      try:
          refreshInfo = entity.refreshEntities('properties/postprocess', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh postprocess configurations via properties endpoint: %s' % str(e))
          
      try:
          refreshInfo = entity.refreshEntities('properties/savedsearches', sessionKey=self.getSessionKey())
          
      except Exception as e:
          logger.warn('Could not refresh savedsearches configurations via properties endpoint: %s' % str(e))
      
      logger.info('%s completed successfully' % (actionStr))
  
  def handleEdit(self, confInfo):
      """
      Handles edits to the configuration options
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if PostProcessRH.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = PostProcessRH.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))

      ## Refresh
      self.handleReload()
      
      ## Get list of valid saved searches
      savedsearches = self.getSavedSearches()
      
      name = self.callerArgs.id
      args = self.callerArgs
      
      if name is not None:
          try:
              conf = entity.getEntity('configs/conf-postprocess', name, sessionKey=self.getSessionKey())
                
          except ResourceNotFound:
              raise admin.NotFoundException("A postprocess configuration with the given name '%s' could not be found" % (name))

      else:
          # Stop if no name was provided
          raise admin.ArgValidationException("No name provided")
      
      # Create the resulting configuration that would be persisted if the settings provided are applied
      for key, val in conf.items():
          if key in args.data:
              conf[key] = args[key][0]
            
          if key == admin.EAI_ENTRY_ACL:
              if val.has_key('app') and val['app'] is not None and len(val['app']) > 0:
                  conf.namespace = val['app']
            
              if val.has_key('owner') and val['owner'] is not None and len(val['owner']) > 0:
                  conf.owner = val['owner']
                    
      if conf.namespace is None or len(conf.namespace) == 0:
          conf.namespace = PostProcess.DEFAULT_NAMESPACE
            
      if conf.owner is None or len(conf.owner) == 0:
          conf.owner = PostProcess.DEFAULT_OWNER
      
      try:
          ## Check config
          PostProcess.checkConf(conf, name, savedsearches=savedsearches)
               
      except InvalidConfigException as e:
          e = "The edit attempt for post process '%s' produced an invalid configuration: %s" % (name, str(e))
          logger.error(e)
          raise admin.ArgValidationException(e)
      
      ## Write out an update to the postprocess config file
      entity.setEntity(conf, sessionKey=self.getSessionKey())

      logger.info("Successfully updated post process: %s" % (name))
      
      ## Reload postprocess
      self.handleReload()
      
      logger.info('%s completed successfully' % (actionStr))
          
  def handleRemove(self, confInfo):
      pass        
        
  def getSavedSearches(self):
      savedsearches = []
      
      savedsearchesDict = entity.getEntities('saved/searches', count=-1, sessionKey=self.getSessionKey())
      
      if savedsearchesDict is not None:
          ## Iterate status dictionary
          for stanza in savedsearchesDict:
              savedsearches.append(stanza)
    
      else:
          logger.error("Could not retrieve saved searches; savedsearchesDict is None")
    
      return savedsearches
   
                               
# initialize the handler
admin.init(PostProcessRH, admin.CONTEXT_APP_AND_USER)