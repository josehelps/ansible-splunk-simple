import splunk.admin as admin
import splunk.entity as entity
import splunk
import logging
import logging.handlers
import os
import re
import copy
import json
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

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

def setup_logger(level, name, file_name, use_rotating_handler=True):
    """
    Setup a logger for the REST handler.
    
    Arguments:
    level -- The logging level to use
    name -- The name of the logger to use
    file_name -- The file name to log to
    use_rotating_handler -- Indicates whether a rotating file handler ought to be used
    """
    
    logger = logging.getLogger(name)
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    
    log_file_path = make_splunkhome_path(['var', 'log', 'splunk', file_name])
    
    if use_rotating_handler:
        file_handler = logging.handlers.RotatingFileHandler(log_file_path, maxBytes=25000000, backupCount=5)
    else:
        file_handler = logging.FileHandler(log_file_path)
        
    formatter = logging.Formatter('%(asctime)s %(levelname)s ' + name + ' - %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

# Setup the handler
logger = setup_logger(logging.DEBUG, "DataModelSimpleRestHandler", "data_model_simple_rest_handler.log")


class DataModelSimpleRestHandler(admin.MConfigHandler):
    """
    The REST handler provides a simpler way to access data models that doesn't require parsing JSON.
    """
    
    FIELDS_TO_EXCLUDE = ['_time']

    def setup(self):
        pass

    def addFieldName(self, field_name, lineage, fields):
        """
        Add a fully qualified field name to the list.
        
        Arguments:
        field_name -- The unqualified name of a field
        lineage -- The list of parent objects that contain the field
        fields -- The list of fields; the new field will be added to this list
        """
        
        if lineage is None or len(lineage) == 0:
            return fields.append(field_name + "|" + field_name)
        else:
            return fields.append(".".join(lineage) + "." + field_name + "|" + field_name)

    def getQualifiedName(self, data_model_object, data_model_objects, lineage=None):
        """
        Get the fully qualified name of the object including all of the parent names (e.g. Authentication.Default_Authentication.Successful_Default_Authentication)
        
        Arguments:
        data_model_object -- The data model to get the name for; this ought to be an extract from the JSON of the data model
        data_model_objects -- The list of data model objects (used so that the parents can be found)
        lineage -- The list of parent names
        """
        
        if lineage is None:
            lineage = []
            
        # Recurse up the parent
        if 'parentName' in data_model_object:
        
            # Find the parent
            for model_object in data_model_objects:
                if model_object['objectName'] == data_model_object['parentName']:
                    self.getQualifiedName(model_object, data_model_objects, lineage)
                    break
            
        # Update the lineage of parent/children heirarchy
        lineage.append(data_model_object['objectName'])
        
        # Return the list as a string
        return ".".join(lineage)

    def getFieldNames(self, data_model_object, data_model_objects, lineage=None, recursive=True):
        """
        Get the field names for the given data model object.
        
        Arguments:
        data_model_object -- The data model to get the name for; this ought to be an extract from the JSON of the data model
        data_model_objects -- The list of data model objects (used so that the parents can be found)
        lineage -- The list of parent names
        recursive -- Indicates if the function should recurse on the parents
        """
        
        if lineage is None:
            lineage = []
        
        # Get the fields
        fields = []
        
        # Get the fields from the parent
        if 'parentName' in data_model_object and recursive:
            
            # Populate the base event fields
            if data_model_object['parentName'] == 'BaseEvent':
                self.addFieldName("host", [], fields)
                self.addFieldName("source", [], fields)
                self.addFieldName("sourcetype", [], fields)
                
            else:
                # Find the model associated with the parent
                for model_object in data_model_objects:
                    #logger.info("Looking for parent of %s named %s against potential parent %s", data_model_object['objectName'], data_model_object['parentName'], model_object['objectName'])
                    
                    if model_object['objectName'] == data_model_object['parentName']:
                        
                        # Found the parent, recurse on it
                        fields.extend( self.getFieldNames( model_object, data_model_objects, lineage ) )

        # Update the lineage of parent/children heirarchy
        lineage.append(data_model_object['objectName'])
                
        for field in data_model_object['fields']:
                    
            if field['fieldName'] not in DataModelSimpleRestHandler.FIELDS_TO_EXCLUDE:
                self.addFieldName(field['fieldName'], lineage, fields)
                
        # Get the output fields    
        for output_field in data_model_object['calculations']:
                    
            for field in output_field['outputFields']:
                if field['fieldName'] not in DataModelSimpleRestHandler.FIELDS_TO_EXCLUDE:
                    self.addFieldName(field['fieldName'], lineage, fields)
                    
        return fields

    @log_function_invocation
    def handleList(self, confInfo):
        """
        Provide the list of configuration options.
        
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        
        try:
            # Get the entities
            data_models = entity.getEntities('data/models', count=-1, sessionKey=self.getSessionKey())
            
            for model_name in data_models:
                
                try:
                    # Get the description of the JSON for parsing
                    if 'eai:data' in data_models[model_name]:
                        description = json.loads( data_models[model_name]['eai:data'])
                        
                        # Get the display name if provided
                        if 'displayName' in description:
                            displayName = description['displayName']
                        else:
                            displayName = model_name
                            
                        # Append the display name so that it is returned to the REST response
                        confInfo[model_name].append('displayName', displayName)
                        
                    else:
                        logger.info("Model %s does not include eai:data", model_name)
                        description = []
                        continue
                    
                except ValueError:
                    logger.error("Could not decode JSON for model %s", model_name)
                    description = []
                    continue
                
                # Handle each object defined in the JSON
                for d in description['objects']:
                    
                    # Get the object name
                    name = self.getQualifiedName(d, description['objects'])
                                    
                    # Get the display name
                    if 'displayName' in d:
                        objectName = d['displayName']
                    else:
                        objectName = d['objectName']
                    
                    confInfo[model_name].append("object.%s.name" % (name), objectName)
                    
                    # Get the parent name
                    confInfo[model_name].append("object.%s.parent" % (name), d['parentName'])
                    
                    # Get the fields
                    fields = self.getFieldNames(d, description['objects'])
                    
                    # Append the fields
                    confInfo[model_name].append("object.%s.attributes" % (name), fields)
                    
        except Exception as e:
            logger.exception("Error while listing data models")
            raise e
      
# initialize the handler
admin.init(DataModelSimpleRestHandler, admin.CONTEXT_NONE)
