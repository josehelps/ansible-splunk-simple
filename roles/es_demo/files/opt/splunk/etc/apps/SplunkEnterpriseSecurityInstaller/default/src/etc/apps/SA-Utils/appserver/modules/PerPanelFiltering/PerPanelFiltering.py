import controllers.module as module
import cherrypy
import splunk.auth as auth
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import csv
import json
import logging
import splunk.clilib.bundle_paths as bp
import splunk.util as util
import traceback
import time
import os
import logging.handlers
import splunk
import splunk.entity as entity
import sys

# Import the lookup files helper
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "bin"]))
import lookupfiles

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('per_panel_filtering')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'per_panel_filtering.log']), maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

# Setup the handler
logger = setup_logger(logging.DEBUG)


class PerPanelFiltering(module.ModuleHandler):

    @staticmethod
    def getCapabilities4User(user=None, session_key=None):
        roles = []
        capabilities = []
        
        ## Get user info              
        if user is not None:
            logger.info('Retrieving role(s) for current user: %s' % (user))
            userDict = entity.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
        
            for stanza, settings in userDict.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            logger.info('Successfully retrieved role(s) for user: %s' % (user))
                            roles = val
             
        ## Get capabilities
        for role in roles:
            logger.info('Retrieving capabilities for current user: %s' % (user))
            roleDict = entity.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
            
            for stanza, settings in roleDict.items():
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            logger.info('Successfully retrieved %s for user: %s' % (key, user))
                            capabilities.extend(val)
            
        return capabilities

    def getCSVReader(self, csv_file) :
        """
        Returns a CSV reader and a file handle to the incident_review csv file.
        
        WARNING: make sure to close the file_handle when you are done with it ("file_handle.close()") in a finally block
        
        Arguments:
        csv_file -- The name of the file to open a reader for
        """
        
        #    1.1 -- Get the location of the lookup file
        file_path = make_splunkhome_path( [ os.path.normpath(csv_file) ] )
        
        #    1.3 -- Get file handle
        file_handle = open(file_path, "r")
        
        #    1.4 -- Open the CSV
        reader = csv.reader(file_handle, lineterminator='\n')
        
        return reader, file_handle
        
    def getCSVHeader(self, csv_file) :
        """
        Get the header line from the provided file name.
        
        Arguments:
        csv_file -- The name of the file to get the headers from
        """
        
        logger.debug("Getting header from: " + str(csv_file));
        
        reader, reader_fh = self.getCSVReader(csv_file)
        
        try:
            first = True
        
            for line in reader:
                if first:
                    return line
        finally:
            if reader_fh is not None:
                reader_fh.close()

    def copyFileToFH(self, source_file, destination_file_handle, add_final_endline_if_necessary=True):
        """
        Copy the file to the file in the destination file-handle.
        
        Arguments:
        source_file -- The file to copy from
        destination_file_handle -- The handle of the file to copy to
        add_final_endline_if_necessary -- The file will be appended with an endline if it does not end with a blank line
        """
    
        # We are going to keep track of whether the line we wrote is empty since we may need to add a blank line at the end
        final_endline = False
    
        with open(source_file, 'r') as f:
                        
            for line in f:
                destination_file_handle.write(line)
                
                # If the line ended with an endline then note it as such
                if line.endswith("\n"):
                    final_endline = True
                else:
                    final_endline = False
                
        # Add a blank line to the end if it doesn't exist and if we were asked to
        if add_final_endline_if_necessary and not final_endline:
            destination_file_handle.write("\n")
        
    @staticmethod
    def hasCapabilities(user=None, session_key=None):
        
        logger.debug("Checking permissions for user=%s", user )
        
        capabilities = PerPanelFiltering.getCapabilities4User(user, session_key)

        return 'edit_per_panel_filters' in capabilities

    def generateResults(self, fields, values, lookup_file=None, lookup_name=None, owner="nobody", namespace=None, **args):
        """
        Update the lookup file to apply the per-panel-filtering.
        
        Arguments:
        fields -- The list of fields that are to be used for the purposes of filtering
        values -- The values to filter. Each value should be a bar separated list of fields and the number of fields in each value must be the same as the number of fields.
        lookup_file -- The lookup file name (ppf_foo.csv). This should not be a full path, just the file name. This argument is unnecessary if lookup_name is provided.
        lookup_name -- The transforms.conf name of the lookup file. This argument is unnecessary if lookup_file is provided.
        owner -- The owner of the lookup file (defaults to "nobody")
        namespace -- The namespace (app name) where the lookup file resides in
        """
        
        # Make sure that that parameters are correct
        if namespace is None:
            raise Exception("Namespace cannot be none")
        
        if lookup_file is None and lookup_name is None:
            raise Exception("Either lookup file or lookup name must be provided (both cannot be none)")

        # An owner of none is equivalent to "nobody" so treat them as such
        if owner is None:
            owner = "nobody"
        
        # Get the session key and user name
        session_key = splunk.getSessionKey()
        user = auth.getCurrentUser()['name']
        
        # Ensure that the user has the proper permissions
        if not PerPanelFiltering.hasCapabilities(user, session_key):
            message = 'User %s does not have the capability (edit_per_panel_filters) required to modify per-panel-filters' % (user)
            logger.critical(message)
            raise Exception(message)
        
        # Get the lookup file from the definition
        if lookup_file is None or len(lookup_file) == 0:
            lookup_file = lookupfiles.get_lookup_table_location( lookup_name, namespace, owner, key=session_key, fullpath=False )
        
        # Get the fields in an array if only a single value was provided
        if isinstance(fields, basestring):
            fields = [ fields ]
            
        # Get the values in an array if only a single value was provided
        if isinstance(values, basestring):
            values = [ values ]
            
        # Get the time
        nowTime = util.mktimegm(time.gmtime())
        
        # Prepare a response
        response = {}

        # Define the temp file handle early so that we can ensure it is closed in the finally block
        temp_file_handle = None

        # Perform the save
        try:
        
            # Create the temporary file
            temp_file_handle = lookupfiles.get_temporary_lookup_file()
            temp_file_name = temp_file_handle.name
                
            # Derive the paths
            temp_file_full_path = make_splunkhome_path(['var', 'run', 'splunk', 'lookup_tmp', temp_file_name])
            destination_full_path = os.path.join( make_splunkhome_path(['etc', 'apps', namespace, 'lookups', lookup_file] ) )
            
            # Copy the existing file to the temporary one
            self.copyFileToFH(destination_full_path, temp_file_handle)
                
            # Add the row to the temporary file
            if temp_file_handle is not None and os.path.isfile(temp_file_name):
                
                # Get the header so that we can place the data in correct columns
                header = self.getCSVHeader(destination_full_path)
                
                csv_writer = csv.writer(temp_file_handle, lineterminator='\n')
              
                # Check length of fields
                if len(fields) and set(fields).issubset(set(header)):
                    
                    # Create the result row
                    resultContainer = []
                        
                    for x in range(0, len(header)):
                        resultContainer.append('')
                        
                        if header[x] == 'create_time':
                            resultContainer[x] = nowTime
                        
                        elif header[x] == 'start_time':
                            resultContainer[x] = nowTime
                        
                        elif header[x] == 'filter':
                            resultContainer[x] = 'whitelist'
                        
                        elif header[x] == 'creator':
                            resultContainer[x] = user
                    
                    # Write out the values
                    for value in values:
                        
                        # Split the value
                        value = value.split('|')
                    
                        # Make sure we got all of the fields
                        if len(value) == len(fields):
                            
                            # Clone the result
                            result = resultContainer[:]
                            
                            for x in range(0, len(fields)):
                                field = fields[x]
                                    
                                # Update result with value(s) provided
                                result[header.index(field)] = value[x]
                                
                            # Write the result
                            csv_writer.writerow(result)
                        
            # Swap the lookup files
            temp_file_handle.close()
            
            # Determine if the lookup file exists, create it if it doesn't
            if not os.path.exists(destination_full_path):
                shutil.move(temp_file_full_path, destination_full_path)
                logger.info('Per-panel filtering lookup file updated successfully, user=%s, namespace=%s, lookup_file=%s', user, namespace, lookup_file)
            
            # Edit the existing lookup otherwise
            else:
                lookupfiles.update_lookup_table(filename=temp_file_name, lookup_file=lookup_file, namespace=namespace, owner=owner, key=session_key)
                logger.info('Per-panel filtering lookup file updated successfully, user=%s, namespace=%s, lookup_file=%s', user, namespace, lookup_file)
                
            # We are done...
            response["message"] = "Panel filtering applied successfully"
            response["success"] = True

        except Exception, e :
            
            tb = traceback.format_exc()
            
            response["message"] = str(e)
            response["trace"] = tb
            response["success"] = False

        finally:
            if temp_file_handle is not None:
                temp_file_handle.close()

        # Return 
        return json.dumps(response)
