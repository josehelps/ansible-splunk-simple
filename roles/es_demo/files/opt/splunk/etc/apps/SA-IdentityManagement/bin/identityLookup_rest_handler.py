'''
Copyright (C) 2005 - 2011 Splunk Inc. All Rights Reserved.
'''
import base64
import re
import splunk.admin as admin
import splunk.entity as entity
import splunk.rest as rest
import splunk.util as util
import logging
import logging.handlers
import os

from identity import *
from splunk import ResourceNotFound
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
    """
    Setup a logger for the REST handler.
    """
    
    logger = logging.getLogger('identityLookup_rest_handler')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
    
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'identityLookup_rest_handler.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()


class UnauthorizedUserException(Exception):
    pass


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
                                                          max_length) % {'name': name, 'max_length': max_length})
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

          
class IdentityLookupRH(admin.MConfigHandler):
    
    ## admin.py constants
    REQUESTED_ACTIONS = {'1': 'ACTION_CREATE', '2': 'ACTION_LIST', '4': 'ACTION_EDIT', '8': 'ACTION_REMOVE', '16': 'ACTION_MEMBERS', '32': 'ACTION_RELOAD'}
    
    ## Permissions
    WRITE_CAPABILITY = 'edit_identityLookup'
    
    ## Default Vals
            
    ## identities.csv file
    identitiesFile = make_splunkhome_path(["etc", "apps", IdentityLookup.DEFAULT_NAMESPACE, "lookups", IdentityLookup.DEFAULT_FILE])      
    
    def setup(self):
        logger.info('Setting up identityLookup_rest_handler')
        
        ## set write capability
        self.setWriteCapability(IdentityLookupRH.WRITE_CAPABILITY)     
         
        if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:         
            ## Fill required params
            for arg in IdentityLookup.REQUIRED_PARAMS:
                self.supportedArgs.addReqArg(arg)
                
            ## Fill valid params
            for arg in IdentityLookup.VALID_PARAMS:
                if arg not in IdentityLookup.REQUIRED_PARAMS:
                    self.supportedArgs.addOptArg(arg)
    
    def handleList(self, confInfo):      
        """
        Handles listing of a review statuses
        """
        ## Get requested action
        actionStr = str(self.requestedAction)
        if actionStr in IdentityLookupRH.REQUESTED_ACTIONS:
            actionStr = IdentityLookupRH.REQUESTED_ACTIONS[actionStr]
            
        logger.info('Entering %s' % (actionStr))
        
        self.handleReload(updateTransforms=False)
         
        ## Get the configurations from IdentityLookup.conf
        identityLookupDict = self.readConfCtx('identityLookup')
        
        ## Get all correlations searches and provide the relevant options
        if identityLookupDict != None:
            
            identitiesHeader = IdentityLookup.getIdentitiesHeader(IdentityLookupRH.identitiesFile)
            if len(identitiesHeader) == 0:
                logger.error("Identities header should not be empty")
          
            ## Check each conf
            for stanza, settings in identityLookupDict.items():
                try:
                    ## Check config
                    IdentityLookup.checkConf(settings, stanza, confInfo, identitiesHeader)
                                
                except InvalidConfigException as e:
                    logger.error("The identityLookup configuration is invalid: %s" % (str(e)))    
    
        logger.info('%s completed successfully' % (actionStr))
           
    def handleReload(self, confInfo=None, updateTransforms=False, updateCaseSensitivity=True):
        """
        Handles refresh/reload of the configuration options
        """
        ## Get requested action
        actionStr = str(self.requestedAction)
        if actionStr in IdentityLookupRH.REQUESTED_ACTIONS:
            actionStr = IdentityLookupRH.REQUESTED_ACTIONS[actionStr]
            
        logger.info('Entering %s' % (actionStr))
    
        logger.info('Refreshing identityLookup configurations via properties endpoint')
        try:
            refreshInfo = entity.refreshEntities('properties/identityLookup', sessionKey=self.getSessionKey())
            
        except Exception as e:
            logger.warn('Could not refresh identityLookup configurations via properties endpoint: %s' % (str(e)))
        
        ## We want the latest transforms as well in case we need to update
        logger.info('Refreshing transforms configurations via properties endpoint')
        try:
            refreshInfo = entity.refreshEntities('properties/transforms', sessionKey=self.getSessionKey())
        
        except Exception as e:
            logger.warn('Could not refresh transforms configurations via properties endpoint: %s' % (str(e)))

        if updateTransforms:
            logger.info("Attempting to update identity_lookup transforms")

            identityLookupDict = self.readConf('identityLookup')
          
            confString = IdentityLookup.confDict2String(identityLookupDict)
          
            encodedConfString = IdentityLookup.encodeConf(confString)
          
            self.updateTransforms(encodedConfString=encodedConfString)

        if updateCaseSensitivity:
            logger.info("Attempting to update identity_lookup_expanded transform for case sensitivity")
            identityLookupDict = self.readConf('identityLookup')
            stanza = identityLookupDict.get(IdentityLookup.DEFAULT_STANZA, {})
            isCaseSensitive = util.normalizeBoolean(stanza.get('case_sensitive', False))            
            self.updateCaseSensitivity(isCaseSensitive)
         
        logger.info('%s completed successfully' % (actionStr))
    
    def handleEdit(self, confInfo):
        """
        Handles edits to the configuration options
        """
        ## Get requested action
        actionStr = str(self.requestedAction)
        if actionStr in IdentityLookupRH.REQUESTED_ACTIONS:
            actionStr = IdentityLookupRH.REQUESTED_ACTIONS[actionStr]
            
        logger.info('Entering %s' % (actionStr))
    
        ## Refresh
        self.handleReload(updateTransforms=False)
    
        name = self.callerArgs.id
        args = self.callerArgs
        
        if name is not None:
            try:
                conf = entity.getEntity('configs/conf-identityLookup', name, sessionKey=self.getSessionKey())
                
            except ResourceNotFound:
                raise admin.NotFoundException("An identityLookup configuration with the given name '%s' could not be found" % (name))
      
        else:
            # Stop if no name was provided
            raise admin.ArgValidationException("No name provided")
    
        # Create the resulting configuration that would be persisted if the settings provided are applied
        for key, val in conf.items():
            if key in args.data:
                conf[key] = args[key][0]
          
            if key == admin.EAI_ENTRY_ACL:
                if len(val.get('app', '')) > 0:
                    conf.namespace = val['app']
              
                if len(val.get('owner', '')) > 0:
                    conf.owner = val['owner']
                  
        if conf.namespace is None or len(conf.namespace) == 0:
            conf.namespace = IdentityLookup.DEFAULT_NAMESPACE
          
        if conf.owner is None or len(conf.owner) == 0:
            conf.owner = IdentityLookup.DEFAULT_OWNER
    
        identitiesHeader = IdentityLookup.getIdentitiesHeader(IdentityLookupRH.identitiesFile)
        if len(identitiesHeader) == 0:
            logger.error("Identities header should not be empty")
        
        try:
            ## Check config
            IdentityLookup.checkConf(conf, name, identitiesHeader=identitiesHeader)
                 
        except InvalidConfigException as e:
            e = "The edit attempt for identityLookup '%s' produced an invalid configuration: %s" % (name, str(e))
            logger.error(e)
            raise admin.ArgValidationException(e)
        
        ## Write out an update to the identityLookup config file
        entity.setEntity(conf, sessionKey=self.getSessionKey())
        
        logger.info("Successfully updated the '%s' identityLookup configuration" % (name))
        
        ## Reload identityLookup
        self.handleReload()
        
        logger.info('%s completed successfully' % (actionStr))
        
    def handleRemove(self, confInfo):
        pass        
               
    def getTransforms(self):
        transforms = []
        TRANSFORMS_REST_URL = 'properties/transforms'
        
        logger.info('Retrieving lookup transforms via %s' % (TRANSFORMS_REST_URL))
        transformsList = entity.getEntities(TRANSFORMS_REST_URL, count=-1, sessionKey=self.getSessionKey())
    
        for stanza in transformsList:
            if stanza.startswith('identity_lookup_'):
                transforms.append(stanza)
                
        return transforms
    
    ## Since handleList for '/data/transforms/lookups shows more keys
    ## than expected, we need to hit _new to determine what keys to keep
    ## when performing a get->set entity
    def getValidTransformKeys(self):
        keys = []
        
        TRANSFORMS_REST_URL = 'data/transforms/lookups/'
        
        logger.info('Retrieving lookup transforms keys via %s' % (TRANSFORMS_REST_URL))
        newEntity = entity.getEntity(TRANSFORMS_REST_URL, '_new', namespace='SA-IdentityManagement', owner='nobody', sessionKey=self.getSessionKey())
    
        return [key for key in newEntity]
    
    def updateCaseSensitivity(self, isCaseSensitive):
        '''Update case sensitivity of identity_lookup_expanded transform to
        match setting in identityLookup.conf.'''
        
        # Note use of configs/conf-transforms here. The case_sensitive_match parameter
        # is not exposed via data/transforms/lookups. 
        TRANSFORMS_REST_URL = 'configs/conf-transforms'
        TRANSFORMS_NAME = 'identity_lookup_expanded'
        TRANSFORM_CASE_SENSITIVE_KEY = 'case_sensitive_match'
        
        lookupEntity = entity.getEntity(TRANSFORMS_REST_URL, TRANSFORMS_NAME, namespace='SA-IdentityManagement', owner='nobody', sessionKey=self.getSessionKey())

        if util.normalizeBoolean(lookupEntity.get(TRANSFORM_CASE_SENSITIVE_KEY)) != isCaseSensitive:
            lookupEntity[TRANSFORM_CASE_SENSITIVE_KEY] = isCaseSensitive
            try:
                entity.setEntity(lookupEntity, sessionKey=self.getSessionKey())         
                logger.info("Successfully updated transform '%s'" % (TRANSFORMS_NAME))
            except Exception as e:
                logger.critical("Could not update transform '%s': %s" % (TRANSFORMS_NAME, str(e)))
        else:
            logger.info("No update required for transform '%s'" % (TRANSFORMS_NAME))

 
    def updateTransforms(self, transforms=None, encodedConfString='', VALID_KEYS=None):
        TRANSFORMS_REST_URL = 'data/transforms/lookups'
        
        ## Regex to find conf= kv pairs in sys.argv of external_cmd
        confKeyRE = re.compile('(conf=(?:\S+)?)')
        
        ## Expected conf= value
        EXPECTED_CONF = 'conf=' + encodedConfString
        
        ## MAX external_cmd length
        ## http://support.microsoft.com/kb/830473
        ## Since we only have the fully qualified command, 256 characters are set aside
        MAX_LENGTH = 8191 - 256
        
        if transforms is None:
            transforms = self.getTransforms()
            
        if VALID_KEYS is None:
            VALID_KEYS = self.getValidTransformKeys()
                
        for stanza in transforms:
            logger.info("Retrieving '%s' transform via %s" % (stanza, TRANSFORMS_REST_URL))
            lookupEntity = entity.getEntity(TRANSFORMS_REST_URL, stanza, namespace='SA-IdentityManagement', owner='nobody', sessionKey=self.getSessionKey())
            
            changeNeeded = True
            
            for key, val in lookupEntity.items():
                if key == 'external_cmd':
                    logger.info("Detecting if external_cmd value needs changing for lookup '%s'" % (stanza))
                    
                    if val is None:
                        val = ''
                        
                    ## Look for the conf= kv pair in the external_cmd value
                    confKeyMatch = confKeyRE.findall(val)
                            
                    ## Check to see if the external_cmd value needs changing
                    if len(confKeyMatch) == 1:
                        if confKeyMatch[0] == EXPECTED_CONF:
                            logger.info("external_cmd setting for '%s' does not require changing" % (stanza))
                            changeNeeded = False
                            
                    ## if a change is needed       
                    if changeNeeded:
                        logger.info("external_cmd setting for '%s' requires changing" % (stanza))
                                
                        ## iterate match list and replace conf= kv's with empty strings
                        for match in confKeyMatch:
                            val = val.replace(match, '')
                                    
                        ## append the expected value
                        val += EXPECTED_CONF
                        
                        if len(val) > MAX_LENGTH:
                            changeNeeded = False
                            logger.critical("Could not update identityLookup transform '%s': external_cmd exceeds MAX_LENGTH %s" % (stanza, MAX_LENGTH))
                        
                        else:        
                            ## update value
                            lookupEntity[key] = val
                                              
                ## Since handleList for '/data/transforms/lookups shows more keys
                ## than expected, we need to hit _new to determine what keys to keep
                ## when performing a get->set entity        
                elif key not in VALID_KEYS:
                    del lookupEntity.properties[key]
                
                ## The only key we want to manipulate is external_cmd.
                ##If it's any other valid key we do nothing    
                else:
                    pass
            
            ## Perform update    
            if changeNeeded:
                try:
                    entity.setEntity(lookupEntity, sessionKey=self.getSessionKey())         
                    logger.info("Successfully updated identityLookup transform '%s'" % (stanza))
                    
                except Exception as e:
                    logger.critical("Could not update identityLookup transform '%s': %s" % (stanza, str(e))) 
                          
                            
# initialize the handler
admin.init(IdentityLookupRH, admin.CONTEXT_APP_AND_USER)
