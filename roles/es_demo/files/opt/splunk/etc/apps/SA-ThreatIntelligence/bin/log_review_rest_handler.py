'''
Copyright (C) 2005 - 2011 Splunk Inc. All Rights Reserved.
'''
import splunk.admin as admin
import splunk.entity as entity
import logging
import logging.handlers
import os
import splunk.bundle as bundle
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from splunk import ResourceNotFound

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """
    
    logger = logging.getLogger('LogReviewPopup')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'LogReviewPopup_rest_handler.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

# Setup the handler
logger = setup_logger(logging.DEBUG)

class InvalidConfigException(Exception):
    """
    Describes an invalid configuration.
    """
    pass
    
class InvalidParameterValueException(InvalidConfigException):
    """
    Describes a config parameter that has an invalid value.
    """
    
    def __init__(self, field, value, value_must_be):
        message = "The value for the field '%s' is invalid: %s (was %s)" % (field, value_must_be, value)
        super(InvalidConfigException, self).__init__( message )

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
                                                          max_length) % {'name' : name, 'max_length' : max_length} )
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

class LogReview(admin.MConfigHandler):
    
    ## Permissions
    WRITE_CAPABILITY = 'edit_log_review_settings'
    
    ## Default Params
    PARAM_COMMENT_MINIMUM_LENGTH = 'minimum_length'
    PARAM_COMMENT_REQUIRED = 'is_required'
    PARAM_DEBUG = 'debug'
    PARAM_ALLOW_URGENCY_OVERRIDE = 'allow_urgency_override'
    
    VALID_PARAMS = [ PARAM_DEBUG, PARAM_COMMENT_MINIMUM_LENGTH, PARAM_COMMENT_REQUIRED, PARAM_ALLOW_URGENCY_OVERRIDE ]
    REQUIRED_PARAMS = [ ]
  
    ## Default Vals
    DEFAULT_NAMESPACE = 'SA-ThreatIntelligence'
    DEFAULT_OWNER = 'nobody'
    
    DEFAULT_COMMENT_LENGTH = 8
    DEFAULT_COMMENT_REQUIRED = False
    
    '''
    Set up supported arguments
    '''
    def setup(self):
        ## set write capability
        self.setWriteCapability(LogReview.WRITE_CAPABILITY)            
       
        if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:
              
            for arg in self.REQUIRED_PARAMS:
                self.supportedArgs.addReqArg(arg)
             
            for arg in self.VALID_PARAMS:
                if arg not in self.REQUIRED_PARAMS:
                    self.supportedArgs.addOptArg(arg)

    def handleCreate(self, confInfo):
        logger.debug("In handleCreate")
      
        # Refresh
        self.handleReload()
      
        name = self.callerArgs.id
        args = self.callerArgs.data
      
        # Make sure the name is not empty
        if not name or len(name) == 0:
            raise admin.ArgValidationException("The stanza name must not be empty")
      
        # Make sure the item does not already exist
        if name in self.readConf("log_review"):
            raise admin.AlreadyExistsException("A entry already exists for %s" % (name))
      
        # Get the field values
        # TODO: obtain the values of the fields into Python variables
        
        debug = _getFieldValue( args, self.PARAM_DEBUG, default_value='false' )
        comment_minimum_length = _getFieldValue( args, self.PARAM_COMMENT_MINIMUM_LENGTH, default_value=self.DEFAULT_COMMENT_LENGTH )
        comment_required = _getFieldValue( args, self.PARAM_DEBUG, default_value=self.DEFAULT_COMMENT_REQUIRED )
      
        # Add the field values to a configuration dictionary (that will be verified)
        conf = entity.getEntity('configs/conf-log_review', '_new', sessionKey=self.getSessionKey())
        
        conf.namespace = self.appName # always save things to SOME app context.
        conf.owner = self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"
        
        conf['name'] = name
        
        _addToDictIfNonNull(conf, self.PARAM_DEBUG, debug)
        _addToDictIfNonNull(conf, self.PARAM_COMMENT_MINIMUM_LENGTH, comment_minimum_length)
        _addToDictIfNonNull(conf, self.DEFAULT_COMMENT_REQUIRED, comment_required)
      
        # Check the configuration
        try:
            self.checkConf(conf, name)
        except InvalidConfigException as e:
            logger.error( "The configuration for '%s' is invalid and could not be created: %s" % ( name, str(e)) )
            raise admin.ArgValidationException( str(e) )
      
        # Write out an update to the config file
        entity.setEntity(conf, sessionKey=self.getSessionKey())
      
        # Refresh
        self.handleReload()

    def handleList(self, confInfo):
        """
        Provide the list of configuration options.
        """
        # Refresh
        self.handleReload()
      
        # Get the configuration from log_review.conf
        confDict = self.readConfCtx('log_review')
      
        err_confs = 0
        ok_confs = 0
      
        # Get all the items and provide the relevant options
        if confDict != None: 
          
            # Check each conf
            for stanza, settings in confDict.items():
                if self.checkConfForRule(stanza, settings, confInfo):
                    ok_confs = ok_confs + 1
                else:
                    err_confs = err_confs + 1
                  
        # Print a log message
        if err_confs > 0:
            logger.debug( "LogReviewPopup REST handler found bad configuration stanzas, confs_errors=%d, confs_passed=%d" % (err_confs, ok_confs) )
        else:
            logger.debug( "LogReviewPopup REST handler loaded all configurations stanzas (no errors found), confs_errors=%d, confs_passed=%d" % (err_confs, ok_confs) )
              
    def handleReload(self, confInfo=None):
        # Refresh the configuration (handles disk based updates)
        refreshInfo = entity.refreshEntities('properties/log_review', sessionKey=self.getSessionKey())

    def handleEdit(self, confInfo):
        """
        Handles edits to the configuration options
        """
        logger.debug("In handleEdit")
        
        # Refresh
        self.handleReload()
      
        name = self.callerArgs.id
        args = self.callerArgs
        
        if name is not None:
            try:
                conf = entity.getEntity('configs/conf-log_review', name, sessionKey=self.getSessionKey())
                
            except ResourceNotFound:
                raise admin.NotFoundException("A log_review setting with the given name '%s' could not be found" % (name))

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
            conf.namespace = LogReview.DEFAULT_NAMESPACE
            
        if conf.owner is None or len(conf.owner) == 0:
            conf.owner = LogReview.DEFAULT_OWNER
        
        # Check the configuration
        try:
            self.checkConf(conf, name)
        except InvalidConfigException as e:
            logger.error( "The configuration for '%s' is invalid and could not be edited: %s" % ( name, str(e)) )
            raise admin.ArgValidationException( str(e) )
      
        logger.debug("Updating configuration for " + str(name))
      
        entity.setEntity(conf, sessionKey=self.getSessionKey())
        
        ## Reload log_review
        self.handleReload()
      
    def checkConfForRule(self, stanza, settings, confInfo=None):
        """
        Checks the settings for the given stanza (which should be the rule name) and raises an
        exception if the configuration is invalid. Otherwise, the configuration option is added to
        the confInfo object (if not None). Returns true if the item validated, false otherwise.
        """
        
        try:
            self.checkConf(settings, stanza, confInfo)
            return True
        except InvalidConfigException as e:
            logger.error( "The configuration for the '%s' stanza is invalid: %s" % ( stanza, str(e)) )
            return False
    
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
    def checkConf(settings, stanza=None, confInfo=None, onlyCheckProvidedFields=False):
        """
        Checks the settings and raises an exception if the configuration is invalid.
        """
      
        # Add all of the configuration items to the confInfo object so that the REST endpoint lists them (even if they are wrong)
        # We want them all to be listed so that the users can see what the current value is (and hopefully will notice that it is wrong)
        for key, val in settings.items():
        
            # Add the value to the configuration info
            if stanza is not None and confInfo is not None:
            
                # Handle the EAI:ACLs differently than the normal values
                if key == 'eai:acl':
                    confInfo[stanza].setMetadata(key, val)
                elif key in LogReview.VALID_PARAMS:
                    confInfo[stanza].append(key, val)

        # Below is a list of the required fields. The entries in this list will be removed as they
        # are observed. An empty list at the end of the config check indicates that all necessary
        # fields where provided.
        required_fields = LogReview.REQUIRED_PARAMS[:]
      
        # Check each of the settings
        for key, val in settings.items():
          
            # Remove the field from the list of required fields
            try:
                required_fields.remove(key)
            except ValueError:
                pass # Field not available, probably because it is not required
        
            # Debugging level
            if (stanza == 'default' or stanza is None) and key == LogReview.PARAM_DEBUG:
                try:
                    LogReview.str_to_bool(val)
                except ValueError:
                    raise InvalidParameterValueException(key, val, "must be a valid boolean")
              
            # Minimum length parameter
            elif stanza == 'comment' and key == LogReview.PARAM_COMMENT_MINIMUM_LENGTH:
                try:
                    int(val)
                except ValueError:
                    raise InvalidParameterValueException(key, val, "must be a valid integer")
                
            # Is comment required
            elif stanza == 'comment' and key == LogReview.PARAM_COMMENT_REQUIRED:
                try:
                    LogReview.str_to_bool(val)
                except ValueError:
                    raise InvalidParameterValueException(key, val, "must be a valid boolean")
                
            # Is urgency override allowed
            elif (stanza == 'notable_editing' or stanza is None) and key == LogReview.PARAM_ALLOW_URGENCY_OVERRIDE:
                try:
                    LogReview.str_to_bool(val)
                except ValueError:
                    raise InvalidParameterValueException(key, val, "must be a valid boolean")
              
        # Check to make sure the related config options that relate to the given parameters are acceptable
        if stanza != "default" and onlyCheckProvidedFields == False:
          
            # Add checks for field values that depend on the value of other field values here
          
            # Warn if some of the required fields were not provided
            if len(required_fields) > 0:
                raise InvalidConfigException("The following fields must be defined in the configuration but were not: " + ",".join(required_fields) )
              
      
# initialize the handler
admin.init(LogReview, admin.CONTEXT_APP_AND_USER)