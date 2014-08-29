import splunk.admin as admin
import splunk.entity as entity
import splunk
import logging
import logging.handlers
import os
import re
import copy

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

class StandardFieldValidator():
    """
    This is the base class that should be used to for field validators.
    """
    
    def to_python(self, name, value):
        """
        Convert the field to a Python object. Should throw a ArgValidationException if the data is invalid.
        
        Arguments:
        name -- The name of the object, used for error messages
        value -- The value to convert
        """
        
        if len( str(value).strip() ) == 0:
            raise admin.ArgValidationException("The value for the '%s' parameter cannot be empty" % (name))
        
        return value

    def to_string(self, name, value):
        """
        Convert the field to a string that can be persisted to a conf file. Should throw a ArgValidationException if the data is invalid.
        
        Arguments:
        name -- The name of the object, used for error messages
        value -- The value to convert
        """
        
        return str(value)

class BooleanFieldValidator(StandardFieldValidator):
    """
    Validates and converts fields that represent booleans.
    """
    
    def to_python(self, name, value):
        if value in [True, False]:
            return value

        elif str(value).strip().lower() in ["true", "1"]:
            return True

        elif str(value).strip().lower() in ["false", "0"]:
            return False
        
        raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid boolean" % ( str(value), name))

    def to_string(self, name, value):

        if value == True:
            return "1"

        elif value == False:
            return "0"
        
        return str(value)
    
class IntegerFieldValidator(StandardFieldValidator):
    """
    Validates and converts fields that represent integers.
    """
    
    max_value = None
    min_value = None
    
    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value
    
    def to_python(self, name, value):
        
        if value is None:
            return None
        
        try:
            int_value = int( str(value).strip() )
            
            if self.min_value is not None and int_value < self.min_value:
                raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid integer must not be less than " % ( str(value), name, self.min_value))
            
            if self.max_value is not None and int_value > self.max_value:
                raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid integer must not be greater than " % ( str(value), name, self.max_value))
            
            return int_value
        
        except ValueError:
            raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid integer" % ( str(value), name))

    def to_string(self, name, value):

        if value is None or len(str(value).strip()) == 0:
            return None

        else:
            return str(value)
        
        return str(value)
    
class FieldSetValidator():
    """
    This base class is for validating sets of fields.
    """
    
    def validate(self, name, values):
        """
        Validate the values. Should throw a ArgValidationException if the data is invalid.
        
        Arguments:
        name -- The name of the object, used for error messages
        values -- The value to convert (in a dictionary)
        """
        
        pass

def log_function_invocation(fx):
    """
    This decorator will provide a log message for when a function starts and stops.
    
    Arguments:
    fx -- The function to log the starting and stopping of
    """
    
    def wrapper(self, *args, **kwargs):
        logger.debug( "Entering: " + fx.__name__ )
        r = fx(self, *args, **kwargs)
        logger.debug( "Exited: " + fx.__name__ )
        
        return r
    return wrapper

def setup_logger(level, name, use_rotating_handler=True):
    """
    Setup a logger for the REST handler.
    
    Arguments:
    level -- The logging level to use
    name -- The name of the logger to use
    use_rotating_handler -- Indicates whether a rotating file handler ought to be used
    """
    
    logger = logging.getLogger(name)
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    
    log_file_path = make_splunkhome_path(['var', 'log', 'splunk', 'tsidx_retention_rest_handler.log'])
    
    if use_rotating_handler:
        file_handler = logging.handlers.RotatingFileHandler(log_file_path, maxBytes=25000000, backupCount=5)
    else:
        file_handler = logging.FileHandler(log_file_path)
        
    formatter = logging.Formatter('%(asctime)s %(levelname)s ' + name + ' - %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

# Setup the handler
logger = setup_logger(logging.INFO, "TSIDXRetentionRestHandler")

class TSIDXRetentionRestHandler(admin.MConfigHandler):
    """
    The REST handler provides functionality necessary to manage the tsidx retention policy.
    """
    
    # Below is the name of the conf file
    CONF_FILE = 'tsidx_retention'
    
    # Below are the list of parameters that are accepted
    PARAM_MAX_TOTAL_SIZE   = 'maxTotalDataSizeMB'
    PARAM_RETENTION_PERIOD = 'retentionTimePeriodInSecs'
    
    # Below are the list of valid and required parameters
    VALID_PARAMS           = [ PARAM_MAX_TOTAL_SIZE, PARAM_RETENTION_PERIOD ]
    
    REQUIRED_PARAMS        = [ PARAM_MAX_TOTAL_SIZE, PARAM_RETENTION_PERIOD ]
    
    # These are parameters that are not persisted to the conf files; these are used within the REST handler only
    UNSAVED_PARAMS         = [ ]
    
    # List of fields and how they will be validated
    FIELD_VALIDATORS = {
        PARAM_MAX_TOTAL_SIZE   : IntegerFieldValidator(min_value=50, max_value=4294967295),
        PARAM_RETENTION_PERIOD : IntegerFieldValidator(min_value=86400, max_value=2147483647)
        }
    
    # These are validators that work across several fields and need to occur on the cleaned set of fields
    GENERAL_VALIDATORS = [ ]
    
    def setup(self):
        """
        Setup the required and optional arguments
        """
        
        if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:
            
            # Set the required parameters
            for arg in TSIDXRetentionRestHandler.REQUIRED_PARAMS:
                self.supportedArgs.addReqArg(arg)
            
            # Set up the valid parameters
            for arg in TSIDXRetentionRestHandler.VALID_PARAMS:
                if arg not in TSIDXRetentionRestHandler.REQUIRED_PARAMS:
                    self.supportedArgs.addOptArg(arg)
    
    @staticmethod
    def convertParams(name, params, to_string=False):
        """
        Convert so that they can be saved to the conf files and validate the parameters.
        
        Arguments:
        name -- The name of the stanza being processed (used for exception messages)
        params -- The dictionary containing the parameter values
        to_string -- If true, a dictionary containing strings is returned; otherwise, the objects are converted to the Python equivalents
        """
        
        new_params = {}
        
        for key, value in params.items():
            
            validator = TSIDXRetentionRestHandler.FIELD_VALIDATORS.get(key)

            if validator is not None:
                if to_string:
                    new_params[key] = validator.to_string(key, value)
                else:
                    new_params[key] = validator.to_python(key, value)
            else:
                new_params[key] = value

        return new_params

    @log_function_invocation
    def handleList(self, confInfo):
        """
        Provide the list of configuration options.
        
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        
        # Read the current settings from the conf file
        confDict = self.readConf(TSIDXRetentionRestHandler.CONF_FILE)
        
        # Set the settings
        if None != confDict:
            for stanza, settings in confDict.items():
                
                vendor_code, attribute_id = None, None
                roles_key = None
                
                for key, val in settings.items():
                    confInfo[stanza].append(key, val)

    @log_function_invocation 
    def handleReload(self, confInfo):
        """
        Reload the list of configuration options.
        
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        
        # Refresh the configuration (handles disk based updates)
        entity.refreshEntities('properties/' + TSIDXRetentionRestHandler.CONF_FILE, sessionKey=self.getSessionKey())
    
    def clearValue(self, d, name):
        """
        Set the value of in the dictionary to none
        
        Arguments:
        d -- The dictionary to modify
        name -- The name of the variable to clear (set to none)
        """
        
        if name in d:
            d[name] = None
        
    @log_function_invocation
    def handleEdit(self, confInfo):
        """
        Handles edits to the configuration options
        
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        
        try:
                
            name = self.callerArgs.id
            args = self.callerArgs
            
            # Load the existing configuration
            confDict = self.readConf(TSIDXRetentionRestHandler.CONF_FILE)
            
            # Get the settings for the given stanza
            is_found = False
            
            if name is not None:
                for stanza, settings in confDict.items():
                    if stanza == name:
                        is_found = True
                        existing_settings = copy.copy(settings) # In case, we need to view the old settings
                        break # Got the settings object we were looking for
            
            # Stop if we could not find the name  
            if not is_found:
                raise admin.NotFoundException("A stanza for the given name '%s' could not be found" % (name) )
            
            # Get the settings that are being set
            new_settings = {}
            
            for key in args.data:
                new_settings[key] = args[key][0]
            
            # Create the resulting configuration that would be persisted if the settings provided are applied
            settings.update( new_settings )
            
            # Check the configuration settings
            cleaned_params = TSIDXRetentionRestHandler.checkConf(new_settings, name, confInfo, existing_settings=existing_settings)
            
            # Get the validated parameters
            validated_params = TSIDXRetentionRestHandler.convertParams( name, cleaned_params, True )
            
            # Write out the updated conf
            self.writeConf(TSIDXRetentionRestHandler.CONF_FILE, name, validated_params )
            
        except admin.NotFoundException, e:
            raise e
        except Exception, e:
            logger.exception("Exception generated while performing edit")
            
            raise e
        
    @staticmethod
    def checkConf(settings, stanza=None, confInfo=None, onlyCheckProvidedFields=False, existing_settings=None):
        """
        Checks the settings and raises an exception if the configuration is invalid.
        
        Arguments:
        settings -- The settings dictionary the represents the configuration to be checked
        stanza -- The name of the stanza being checked
        confInfo -- The confinfo object that was received into the REST handler
        onlyCheckProvidedFields -- Indicates if we ought to assume that this is only part of the fields and thus should not alert if some necessary fields are missing
        existing_settings -- The existing settings before the current changes are applied
        """

        # Add all of the configuration items to the confInfo object so that the REST endpoint lists them (even if they are wrong)
        # We want them all to be listed so that the users can see what the current value is (and hopefully will notice that it is wrong)
        for key, val in settings.items():
        
            # Add the value to the configuration info
            if stanza is not None and confInfo is not None:
            
                # Handle the EAI:ACLs differently than the normal values
                if key == 'eai:acl':
                    confInfo[stanza].setMetadata(key, val)
                elif key in TSIDXRetentionRestHandler.VALID_PARAMS and key not in TSIDXRetentionRestHandler.UNSAVED_PARAMS:
                    confInfo[stanza].append(key, val)

        # Below is a list of the required fields. The entries in this list will be removed as they
        # are observed. An empty list at the end of the config check indicates that all necessary
        # fields where provided.
        required_fields = TSIDXRetentionRestHandler.REQUIRED_PARAMS[:]
        
        # Check each of the settings
        for key, val in settings.items():
            
            # Remove the field from the list of required fields
            try:
                required_fields.remove(key)
            except ValueError:
                pass # Field not available, probably because it is not required
        
        # Stop if not all of the required parameters are not provided
        if onlyCheckProvidedFields == False and len(required_fields) > 0: #stanza != "default" and 
            raise admin.ArgValidationException("The following fields must be defined in the configuration but were not: " + ",".join(required_fields) )
        
        # Clean up and validate the parameters
        cleaned_params = TSIDXRetentionRestHandler.convertParams(stanza, settings, False)
        
        # Run the general validators
        for validator in TSIDXRetentionRestHandler.GENERAL_VALIDATORS:
            validator.validate( stanza, cleaned_params, existing_settings )
        
        # Remove the parameters that are not intended to be saved
        for to_remove in TSIDXRetentionRestHandler.UNSAVED_PARAMS:
            if to_remove in cleaned_params:
                del cleaned_params[to_remove]
        
        # Return the cleaned parameters    
        return cleaned_params
        
    @staticmethod
    def stringToIntegerOrDefault( str_value, default_value=None ):
        """
        Converts the given string to an integer or returns none if it is not a valid integer.
        
        Arguments:
        str_value -- A string value of the integer to be converted.
        default_value -- The value to be used if the string is not an integer.
        """
        
        # If the value is none, then don't try to convert it
        if str_value is None:
            return default_value
        
        # Try to convert the string to an integer
        try:
            return int(str(str_value).strip())
        except ValueError:
            # Return none if the value could not be converted
            return default_value            
      
# initialize the handler
admin.init(TSIDXRetentionRestHandler, admin.CONTEXT_NONE)
