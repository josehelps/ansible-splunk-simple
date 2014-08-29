"""
This class deletes TSIDX namespace files that ought to be deleted per the retention policy.

Here is how the system works. The tsidx_retention.conf file indicates the retention policies for TSIDX namespaces. TThe retention policy consists of two parameters that are set on a per-namespace level:

 1) retentionTimePeriodInSecs: indicates when to start deleting files once they get too old (based on the latest event in the namespace file)
 2) maxTotalDataSizeMB: indicates when to start deleting files based on size

Files will be deleted if they match either of the retentionTimePeriodInSecs or maxTotalDataSizeMB. This means that files may be deleted even if they contain events younger
that the retention period if they get too big (and vice-versa). Deleting files based on the retention period is easy; we just find the files that are too old and delete them.
We will use the date of the latest event in the namespace for determining if the data is past the retention period.

Deleting files based on the max size is more difficult though because a namespace is composed of a series of files and we cannot edit the files to reduce their size to get them
below the limit. Instead, we have to delete files (starting with the oldest) until we get close to the limit.

To do this:

 1) First, we get all of the files associated with the namespace and we sort them by date such with the latest file first.
 2) Next, we iterate through the files until we hit the size limit. Then, we delete all files after hitting the size limit.

Consider the following namespace which has five (5) files. Assume that the limit is 250 MB and that the files are 100 MB each.

                                namespace: sa_authentication
                                +-----------------------+
                                |                       |  <-- This is the latest file (has the latest events)
                                | file[1]: 100 MB       |      The files are sorted is descending order so the next files will 
                                |                       |      be progressively older
                                +-----------------------+
                                |                       |
                                | file[2]: 100 MB       |
                                |                       |
                                +-----------------------+
                                |                       |
    size limit (250 MB) -->     | file[3]: 100 MB       |
                                |                       |
    start deleting here -->     +-----------------------+
                                |                       |
                                | file[4]: 100 MB       |   <-- Will be deleted
                                |                       |
                                +-----------------------+
                                |                       |
                                | file[5]: 100 MB       |   <-- Will be deleted
                                |                       |
                                +-----------------------+
   

Below is a list of the classes included:
+-----------------------+----------------------------------------------------------------------------------------------------------------------------------------------+
|         Class         |                                                                   Purpose                                                                    |
+-----------------------+----------------------------------------------------------------------------------------------------------------------------------------------+
| TSIDXFile             | Represents a file that is part of a TSIDX namespace. Note that a TSIDX namespace is composed of a series of these individual files.          |
| TSIDXRetentionPolicy  | Specifies a retention policy similar to the one that Splunk uses for indexes.                                                                |
| TSIDXNamespaceFileSet | Represents a TSIDX namespace and the files contained within it. This class includes a list of the files associated with the TSIDX namespace. |
| TSIDXCleanUp          | The main class for performing the deletion of TSIDX namespace files.                                                                         |
+-----------------------+----------------------------------------------------------------------------------------------------------------------------------------------+

The table above was made using http://www.sensefulsolutions.com/2010/10/format-text-as-table.html

"""

import splunk.clilib.bundle_paths as bundle_paths
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import IntField, EpochField, Field
import splunk.util
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

import datetime
import re
import os
import logging
from logging import handlers
import traceback
import sys

def setup_logger():
    """
    Setup a logger.
    """
    
    logger = logging.getLogger('tsidx_clean_up')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
    
    file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'tsidx_clean_up.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

class TSIDXFile(SplunkAppObjModel):
    resource              = '/data/tsidxstats/namespaces'
    file_size_on_disk     = IntField()
    file_size             = IntField()
    latest                = EpochField()
    earliest              = EpochField()
    tsidx_namespace       = Field()
    file_path             = Field()
    file_name             = Field()
    
    def delete(self):
        """
        Deletes that file that this class represents. If the file does not exist already, then it will return true.
        
        @return: a boolean indicating if the file no longer exists (which implies success)
        """
        
        try:
            os.remove(self.file_path)
            logger.info( "Deleted TSIDX namespace file, namespace_file=%s, namespace=%s" % (self.file_path, self.tsidx_namespace) )
        except OSError as e:
            if e.errno == 2: # No such file or directory
                logger.info( "Could not delete TSIDX namespace file because it no longer exists, namespace_file=%s, namespace=%s" % (self.file_path, self.tsidx_namespace) )
                return True # File does not exist
            else:
                logger.info( "Could not delete TSIDX namespace file, namespace_file=%s, exception=%s, namespace=%s" % (self.file_path, str(e), self.tsidx_namespace) )
                raise e
        
        return not self.exists()
    
    def exists(self):
        """
        Indicates if file that this class represents still exists.
        
        @return: a boolean indicating if the file exists
        """
        
        return os.path.exists(self.file_path)
    
class TSIDXRetentionPolicy(SplunkAppObjModel):
    resource              = '/data/tsidxstats/retention'
    max_size              = IntField(api_name="maxTotalDataSizeMB")
    retention_period      = IntField(api_name="retentionTimePeriodInSecs")
    
    MINIMUM_RETENTION_PERIOD = 86400
    MINIMUM_FILE_SIZE = 50
    
    def is_valid(self):
        """
        Determines if the retention policy is valid. This is necessary to make sure that the user hasn't created a 
        policy that would do something drastic like delete all files.
        
        @return: a boolean indicating if the retention policy is valid
        """
        
        if self.retention_period is None:
            logger.warning("The retention policy is missing a retention period, namespace=%s" % (self.name) )
            return False
        
        if self.retention_period < TSIDXRetentionPolicy.MINIMUM_RETENTION_PERIOD:
            logger.warning("The retention policy period is too small, namespace=%s, retention_period=%i, minimum_retention_period=%i" % (self.name, self.retention_period, TSIDXRetentionPolicy.MINIMUM_RETENTION_PERIOD) )
            return False
        
        if self.max_size is None:
            logger.warning("The retention policy is missing a maximum file size, namespace=%s" % (self.name) )
            return False
        
        if self.max_size < TSIDXRetentionPolicy.MINIMUM_FILE_SIZE:
            logger.warning("The retention policy period is too small, namespace=%s, max_size=%i, minimum_max_size=%i" % (self.name, self.max_size, TSIDXRetentionPolicy.MINIMUM_FILE_SIZE) )
            return False
        
        return True
    
    def get_date_limit(self):
        """
        Get a datetime representing the oldest time where older files will be outside the retention policy (too old).
        
        @return: a datetime representing the oldest date that would be within the retention policy
        """
        
        r = datetime.timedelta(seconds=self.retention_period)
        
        # Make sure to use the Splunk timezone or we will get an error: "can't compare offset-naive and offset-aware datetimes"
        return datetime.datetime.now( splunk.util.localTZ ) - r
    
    
    def is_outside_retention_period(self, datetime):
        """
        Indicates if the given date falls outside of the retention policy (is too old).
        
        @return: boolean indicating if the provided datetime is outside the retention policy
        """

        return datetime < self.get_date_limit()

class TSIDXNamespaceFileSet():
    """
    Represents a TSIDX namespace and the associated files.
    """
    
    def __init__(self, name, files=[]):
        self.name = name
        self.files = files[:]
        
        # Make sure that the files are sorted such that the latest is first
        TSIDXNamespaceFileSet.sort_namespace_files(self.files)
            
    def get_total_size(self, use_disk_size=True):
        """
        Get the total size of the files in the namespace.
        
        @return: the total size of the file
        
        @param use_disk_size: use the actual disk size on disk, not the allocated portion (per TSIDX probe)
        """
        
        size = 0
        
        for tsidx_file in self.files:
            
            if use_disk_size:
                size = size + tsidx_file.file_size_on_disk
            else:
                size = size + tsidx_file.file_size
                
        return size
    
    @staticmethod
    def get_namespace_files(session_key=None):
        """
        Get the namespace files as a TSIDXNamespaceFileSet instances.
        
        @return: a list of TSIDXNamespaceFileSet instances
        
        @param session_key: the session key to use to connect to Splunkd
        """
        
        d = TSIDXNamespaceFileSet.get_namespace_files_as_dict(session_key=session_key)
        namespace_file_sets = []
        
        for name, files in d.items():
            namespace_file_sets.append( TSIDXNamespaceFileSet( name=name, files=files) )
    
        return namespace_file_sets
    
    @staticmethod
    def sort_namespace_files( file_list ):
        """
        Sort the namespace file list. This will sort the files such that the newest file is at index 0 and the oldest is at the high end of the list.
        
        @param file_list: a list of TSIDXFile instances
        """
        # An exception will be thrown if one of list items does not contain the latest field. In this case, what we do (whether we delete it) depends entirely on the size of the file.
        # But to avoid causing the function to fail, we will use the current time instead of the latest time from the file.
        file_list.sort(key=lambda r: r.latest if r.latest else datetime.datetime.now( splunk.util.localTZ ), reverse=True)
    
    @staticmethod
    def get_namespace_files_as_dict(session_key=None):
        """
        Get the namespace files organized into a dictionary where the key is the namespace and the value is a list of TSIDXFile instances.
        
        @return: a dictionary with TSIDXFile instances grouped by the TSIDX namespace name
        
        @param session_key: the session key to use to connect to Splunkd
        """
        
        d = {}
        
        tsidx_files = TSIDXFile.all(sessionKey=session_key)
        
        for tsidx_file in tsidx_files:
            
            # Determine if the namespace is already in the dict and add it if not
            if not tsidx_file.tsidx_namespace in d:
                d[tsidx_file.tsidx_namespace] = []
            
            # Append the TSIDX file instance
            d[tsidx_file.tsidx_namespace].append(tsidx_file)
            
        # Sort the files by the latest date of the events included
        for k, file_list in d.items():
            TSIDXNamespaceFileSet.sort_namespace_files(file_list)
            
        # Return the dictionary of TSIDX instance
        return d

class TSIDXCleanUp():
    """
    This class performs a clean up on the TSIDX namespace file
    """
    
    def __init__(self, namespace_file_sets=None, retention_policies=None, session_key=None):
        """
        Creates an instance of the TSIDX clean up class for cleaning up TSIDX files that are old.
        
        @param namespace_file_sets: a list of TSIDXNamespaceFileSet instances that represents the namespaces on the host; this will be populated automatically if not provided
        @param retention_policies: a list of TSIDXRetentionPolicy instances that should be used for deleting TSIDX namespace files; this will be populated automatically if not provided
        @param session_key: the session key to use to connect to Splunkd
        """
        
        # Set the namespace file list
        if namespace_file_sets is not None:
            self.namespace_file_sets = namespace_file_sets
        else:
            self.namespace_file_sets = TSIDXNamespaceFileSet.get_namespace_files(session_key=session_key)
            
        # Set up the retention policies
        if retention_policies is not None:
            self.retention_policies = retention_policies
        else:
            self.retention_policies = TSIDXRetentionPolicy.all(sessionKey=session_key)
            
        # Save the session key
        self.session_key = session_key
                
    def get_retention_policy(self, namespace):
        """
        Get the retention policy for the given namespace.
        
        @return: the retention policy for the given namespace (or the default one)
        
        @param namespace: the TSIDX namespace to get the retention policy for
        """
        
        # Find the policy that for this namespace
        for policy in self.retention_policies:
            if policy.name == namespace:
                return policy
            
        # If we didn't find a specific policy, then get the default one
        for policy in self.retention_policies:
            if policy.name == "default":
                return policy
                
    def do_clean_up(self):
        """
        Delete TSIDX namespace files that fall outside of the retention policy.
        
        @return: two integers indicating the number of files successfully deleted and the number of files that could be deleted (files_deleted, files_that_could_not_deleted)
        """
        
        # These keep counts so that we can report on what happened
        files_deleted = 0 # The number of files successfully deleted
        files_that_could_not_deleted = 0 # The number of files that we tried to delete but couldn't
        
        # Examine each of the namespaces...
        for namespace_file_set in self.namespace_file_sets:
            
            # Get the applicable retention policy
            retention_policy = self.get_retention_policy(namespace_file_set.name)
            
            # Don't try to do anything if the retention policy is invalid
            if not retention_policy.is_valid():
                logger.warning("A retention policy entry is invalid and will be skipped, retention_policy=%s" % (retention_policy.name))
                return 0, 0
            
            # The following two vars are used for deleting files once the size limit has been reached
            size_limit_reached = False
            total_size = 0
            
            # Purge files that are older than the retention policy
            # Note that these must be sorted with the latest files first
            for namespace_file in namespace_file_set.files:
                
                # By default, we will not delete anything unless a retention policy says to
                should_delete = False
                
                # Determine if the file is outside the retention policy
                if namespace_file.latest and retention_policy.is_outside_retention_period( namespace_file.latest ):
                    should_delete = True
                    logger.info('Namespace file found that is outside of the retention period and will be deleted, retention_policy=%s, namespace_file="%s"' % ( retention_policy.name, namespace_file.file_path ))
                    # Note that if the current file is outside the retention period, then all files following should too since they should be even older.
                    
                # Determine if the size limit was reached
                elif size_limit_reached:
                    should_delete = True
                    logger.info('Namespace file found that will be deleted in order to bring the disk usage closer to the size limit, retention_policy=%s, file_size=%i, namespace_file="%s"' % ( retention_policy.name, namespace_file.file_size_on_disk, namespace_file.file_path ))
                
                # Delete the file if we found that it can be removed
                if should_delete:
                    
                    # Try to delete the file
                    if namespace_file.delete():
                        files_deleted = files_deleted + 1
                    else:
                        files_that_could_not_deleted = files_that_could_not_deleted + 1
                        
                # Add up the file size so that we can determine if we reached the file-size limit yet
                # check namespace_file.file_size_on_disk is None or not
                file_size = namespace_file.file_size_on_disk if namespace_file.file_size_on_disk else 0
                total_size = total_size + file_size

                # Convert the units from bytes to MB
                total_size_mb = total_size / 1024.0 / 1024.0
                
                # If we hit the file size limit, then set size_limit_reached to true so we know to start deleting files to keep the size down
                if total_size_mb >= retention_policy.max_size:
                    size_limit_reached = True
        
        # Return counts indicating the number files deleted and not deleted
        logger.info("TSIDX clean up executed successfully, files_deleted=%s, files_that_could_not_deleted=%s" % (files_deleted, files_that_could_not_deleted))
        return files_deleted, files_that_could_not_deleted
    
if __name__ == '__main__':
    
    try:
        
        # Get session key sent from splunkd
        session_key = sys.stdin.readline().strip() 
        # Make sure we actually got a session key         
        if len(session_key) == 0:
            logger.critical( "Did not receive a session key from splunkd. Please enable passAuth in inputs.conf for this script")
            sys.stderr.write("Did not receive a session key from splunkd. Please enable passAuth in inputs.conf for this script")
            exit(2)
        
        clean_up = TSIDXCleanUp(session_key=session_key)
        clean_up.do_clean_up()
        
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error('Error generated when running TSIDX clean up. stacktrace= %s' % (stacktrace))