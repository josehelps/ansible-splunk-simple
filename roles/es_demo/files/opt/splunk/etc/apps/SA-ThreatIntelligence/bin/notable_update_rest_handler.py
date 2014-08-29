import json
import os
import re
import csv
from time import strftime, gmtime, strptime
import time
import calendar
import urllib

import traceback,sys
import splunk.entity as entity
import splunk, splunk.search, splunk.util
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

import portalocker
import logging

# Setup the logger
def setup_logger():
    """
    Setup a logger for the REST handler.
    """
    
    logger = logging.getLogger('splunk.SAThreatIntelligence.NotableEventUpdateHandler')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'notable_event_update_rest_handler.log']), maxBytes=25000000, backupCount=5)
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
        
        diff_string = str( round( diff, 6) ) + " seconds"
        
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
        self.start_time = time.time()
    
    def __exit__(self, type, value, traceback):
        
        # Determine how long the operation took
        time_spent = time.time() - self.start_time
        
        # See if we can find a logger as a global variable
        if self.logger is None:
            try:
                self.logger = logger
            except NameError:
                raise Exception("Could not get a logger instance for the purposes of recording performance")
        
        # Log the time spent
        self.logger.debug( self.title + ", duration=%.6f" % ( time_spent) )
        

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

class SearchNotFoundException(Exception):
    pass

class NotEventSearchException(Exception):
    pass

class SearchNotDoneException(Exception):
    pass

class LogReviewStatus():
    
    def __init__(self, time, rule_id, owner, urgency, status, comment, user):
        self.time = time
        self.rule_id = rule_id
        self.owner = owner
        self.urgency = urgency
        self.status = status
        self.comment = comment
        self.user = user
    
class LogReviewStatusChanges:
    
    def __init__(self):
        self.success_count = 0
        self.messages = {}
        
    def incrementFailureCountEx(self, messages_list):
        
        for m in messages_list:
            self.incrementFailureCount(m)
           
    def getSuccessCount(self):
        return self.success_count       
     
    def getFailureCount(self):
        
        failures = 0
        
        for k in self.messages:
            failures = failures + self.messages[k]
            
        return failures
        
    def incrementFailureCount(self, message):
        
        # Increment the message if it already exists
        if message in self.messages:
            self.messages[message] = self.messages[message] + 1
        else:
            self.messages[message] = 1
            
    def getMessagesAsString(self, separator="; ", addSuccessInfo=True, errorMessageStart="Unable to change %d events: "):
        
        msg = None
        
        # Add the information about the items successfully changed
        if addSuccessInfo:
            if self.success_count > 0:
                msg = "%d events were successfully changed" % (self.success_count)
        
        # Add the error message start message
        if errorMessageStart is not None and self.getFailureCount() > 0:
            if msg is None:
                msg = errorMessageStart % (self.getFailureCount())
            else:
                msg = msg + separator + errorMessageStart % (self.getFailureCount())
        
        # Add the error messages
        errors_msg = None
        
        for m in self.messages:
            
            if self.messages[m] == 1:
                m = m + " (%d event)" % (self.messages[m])
            else:
                m = m + " (%d events)" % (self.messages[m])
            
            if errors_msg is None:
                errors_msg = m
            else:
                errors_msg = errors_msg + separator + m
            
        # Construct the final message
        if msg is not None and errors_msg is not None:
            return msg + errors_msg
        elif msg is not None:
            return msg
        else:
            return errors_msg

    def incrementSuccessCount(self):
        self.success_count = self.success_count + 1

class NoRuleIDException(Exception):
    pass

class NotableEventUpdate(splunk.rest.BaseRestHandler):

    """
    This REST handler provides services for modifying the status of notable events.
    """

    # Below are the column numbers in the incident review csv file
    CSV_INCIDENT_REVIEW_TIME = 0
    CSV_INCIDENT_REVIEW_RULE_ID = 1
    CSV_INCIDENT_REVIEW_OWNER = 2
    CSV_INCIDENT_REVIEW_URGENCY = 3
    CSV_INCIDENT_REVIEW_STATUS = 4
    CSV_INCIDENT_REVIEW_COMMENT = 5
    CSV_INCIDENT_REVIEW_USER = 6
    
    # This defines how long we will wait (in seconds) for the locked incident review lookup file to become available before giving up
    FILE_LOCK_TIMEOUT = 10
    
    # The following defines the default status if one is not defined at all
    DEFAULT_NOTABLE_EVENT_STATUS = '0' # zero corresponds to "Unassigned"
    
    # The variables below are used when connecting to the REST endpoint
    DEFAULT_NAMESPACE = 'SA-ThreatIntelligence'
    DEFAULT_OWNER = 'nobody'
    REVIEW_STATUSES_REST_URL = '/alerts/reviewstatuses/'
    LOG_REVIEW_REST_URL = '/alerts/log_review/'

    def handle_GET(self):
        return self.handle_POST()
    
    def handle_POST(self):
        sys.__stdout__.write(" ")
        sys.__stdout__.flush()
        
        # Get the arguments
        host_app   = self.args.get('host_app', None)
        client_app = self.args.get('client_app', None)
        status     = self.args.get('status', None)
        comment    = self.args.get('comment', '')
        urgency    = self.args.get('urgency', None)
        searchID   = self.args.get('searchID', None)
        newOwner   = self.args.get('newOwner', None)
        
        # Multiple ruleUIDs are provided as separate parameters. However, the request object only shows one. Thus, we must parse the payload ourselves and get them.
        ruleUIDs = []
        
        regex = re.compile("ruleUIDs[=]([^&]+)*")
        
        for ruleUID in regex.findall(self.request['payload']):
            ruleUIDs.append(urllib.unquote(ruleUID))
            
        # If no ruleUIDs were provided, then this mean the user wants to edit all of the events in the search. Set ruleUIDs to None to signal that no filtering of 
        # events to edit should be done.
        if len(ruleUIDs) == 0:
            ruleUIDs = None
        
        # Make the call
        response_data = self.makeChanges(host_app, client_app, status, comment, newOwner, urgency, ruleUIDs, searchID)
        
        # Setup the response
        self.response.setHeader('content-type', 'application/json')
        self.response.setStatus(200)
        self.response.write(json.dumps(response_data))
    
    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        splunk.rest.BaseRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
        
        # The following variables store cached data that can be used to reduce the frequency of REST calls to SplunkD
        self.correlation_searches = None
        self.status_label_map = None
        
    @time_function_call
    def getCapabilities4User(self, user=None):
        """
        Obtains a list of capabilities in an list for the given user.
        
        Arguments:
        user -- The user to get capabilities for (as a string)
        """
        
        roles = []
        capabilities = []

        # Get the session key
        sessionKey = self.sessionKey

        ## Get user info              
        if user is not None:
            logger.debug('Retrieving role(s) for current user: %s' % (user))
            userEntities = entity.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=sessionKey)

            for stanza, settings in userEntities.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            logger.debug('Successfully retrieved role(s) for user: %s' % (user))
                            roles = val
        
        ## Get capabilities
        for role in roles:
            logger.debug('Retrieving capabilities for current user: %s' % (user))
            roleEntities = entity.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=sessionKey)
          
            for stanza, settings in roleEntities.items():
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            logger.debug('Successfully retrieved %s for user: %s' % (key, user))
                            capabilities.extend(val)

        return capabilities

    @time_function_call
    def getStatusLabelMap(self, force_refresh=False):
        """
        Obtains a list of the review statuses in dictionary with the key set to the label (or the stanza if the label is undefined).
        
        Arguments:
        force_refresh -- Reload the review statuses from the REST endpoint (otherwise, cached entries will be used if available)
        """
        
        # Return the cached results if we have them
        if force_refresh == False and self.status_label_map is not None:
            return self.status_label_map
        
        # Refresh The list
        logger.debug("Reloading the review statuses list")
        reviewStatusesEntities = entity.getEntities('admin/reviewstatuses', count=-1, sessionKey=self.sessionKey)
        reviewStatusesMap = {}
        
        # Convert the list into a dictionary
        for stanza, settings in reviewStatusesEntities.items():
            if ("label" in settings):
                reviewStatusesMap[stanza] = settings["label"]
            else :
                reviewStatusesMap[stanza] = stanza
                
        # Save the review statuses map to the shared variable so that we can use it in the future and avoid another call to the REST end-point
        self.status_label_map = reviewStatusesMap
        
        logger.debug("%s review statuses loaded" % (len(self.status_label_map)) )
        
        return self.status_label_map

    def getLookupsFilePath(self):
        """
        Returns the full path to the lookups file.
        """
        
        return make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "incident_review.csv"])

    @time_function_call
    def getCSVReader(self) :
        """
        Returns a CSV reader and a file handle to the incident_review csv file.
        
        WARNING: make sure to close the file_handle when you are done with it ("file_handle.close()") in a finally block
        """
        
        #    1.1 -- Get the location of the lookup file
        file_path = self.getLookupsFilePath()
        
        #    1.3 -- Get file handle
        file_handle = open(file_path, "r")
        
        #    1.4 -- Open the CSV
        reader = csv.reader(file_handle, lineterminator='\n')
        
        return reader, file_handle
    
    @time_function_call
    def getCSVWriter(self) :
        """
        Returns a CSV writer and a file handle to the incident_review csv file.
        
        WARNING: make sure to close the file_handle when you are done with it ("file_handle.close()") in a finally block
        """
    
        #    1.1 -- Get the location of the lookup file
        file_path = self.getLookupsFilePath()
        
        #    1.2 IF THE FILE WAS MISSING WE USED TO REPLACE IT (W/HEADERS). 
        #    However if the file is missing the whole incident_review view 
        #    dies, hence the code was having no practical effect. 
        #    this it was deleted -- p4 describe 102882 

        #    1.3 -- Get file handle
        file_handle = open(file_path, "a+")
        
        #    1.4 -- Open the CSV
        writer = csv.writer(file_handle, lineterminator='\n')
        
        file_handle.seek(file_handle.tell())
        
        return writer, file_handle

    @staticmethod
    def get_boolean(value, default=None):
        """
        Convert the given string value to a boolean. Return the default value if the value does not appear to be a boolean.
        
        Arguments:
        value -- The value as a string to convert to a boolean
        default -- The default value if it cannot be converted
        """
        
        v = value.strip().lower()
        
        # See if the value is true
        if v == "true":
            return True
        elif v == "1":
            return True
        elif v == "t":
            return True
        
        # See if the value is false
        elif v == "false":
            return False
        elif v == "0":
            return False
        elif v == "f":
            return False
        
        # Otherwise, return the default value
        else:
            return default

    @time_function_call
    def getDefaultCorrelationSearchStatus(self, correlation_search, force_refresh=False):
        """
        Get the default status for the given correlation search.
        
        Arguments:
        correlation_search -- The correlation search to obtain to the default status for
        force_refresh -- If true, the correlation searches will be reloaded from splunkd
        session_key -- The session key to use
        """
        
        # Get the correlation searches information
        correlation_searches = self.getCorrelationSearches(force_refresh)
        logger.debug("Retrieving the default status for correlation search: %s" % (correlation_search) )
        
        # Get the default status if it is defined in the list of correlation searches
        if correlation_search in correlation_searches:
            
            # Return the status
            return correlation_searches[correlation_search]['default_status']
        
        else:
            logger.warn("Could not get default status for %s since it could not be found" % (correlation_search) )

    @time_function_call
    def isUrgencyOverrideAllowed(self):
        """
        Determines if urgency overrides are allowed.
        """
        
        notable_en = entity.getEntity(self.LOG_REVIEW_REST_URL, 'notable_editing', namespace = self.DEFAULT_NAMESPACE, owner = self.DEFAULT_OWNER, count=-1, sessionKey=self.sessionKey)
        
        if 'allow_urgency_override' in notable_en:
            return self.get_boolean( notable_en['allow_urgency_override'] )
        else:
            return True

    @time_function_call
    def commentLengthRequired(self):
        """
        Returns the length of the comment required.
        
        Arguments:
        session_key -- The session key to be used
        """
        
        # Get the session key
        session_key = self.sessionKey
        
        # Get the configuration from the log_review endpoint
        comment_en = entity.getEntity(self.LOG_REVIEW_REST_URL, 'comment', namespace = self.DEFAULT_NAMESPACE, owner = self.DEFAULT_OWNER, sessionKey = session_key, count=-1)

        # Determine if a comment is required
        is_required = self.get_boolean( comment_en['is_required'] )
        
        # If a comment is not required then return 0
        if is_required is None or not is_required:
            return 0
        
        # Determine what length of a comment is required
        if comment_en['minimum_length'] is None:
            return 0
        else:
            minimum_length = comment_en['minimum_length']
        
            # Convert the length to an integer
            try:
                return int(minimum_length)
            except ValueError:
                
                # The minimum length is invalid, print an error message
                logger.warn( "The value for the minimum length is invalid: %s" % (minimum_length) )
                return 0

    @time_function_call
    def getDefaultStatus(self, force_refresh=False, session_key=None):
        """
        Returns the status ID of the default system-wide review status.
        
        Arguments:
        force_refresh -- If true, the review statuses will be reloaded from splunkd
        session_key -- The session key to be used
        """
        
        # Get the cached status
        if force_refresh == False and hasattr(self, "default_status"):
            return self.default_status
        
        # Get the session key
        session_key = self.sessionKey
        
        # Get the list of statuses
        logger.debug("Getting the default status")
        statuses_list = entity.getEntities(self.REVIEW_STATUSES_REST_URL, namespace = self.DEFAULT_NAMESPACE, owner = self.DEFAULT_OWNER, sessionKey = session_key, count=-1)
        
        # Get the first status defined a default (there should be only one)
        for status_id in statuses_list:
            
            # Get the status as a dictionary
            notable_status = statuses_list[status_id]
            
            # Get the disabled 
            if 'disabled' in notable_status:
                disabled = self.get_boolean( notable_status['disabled'])
            else:
                disabled = False
            
            # Get the default status
            if 'default' in notable_status:
                default = self.get_boolean( notable_status['default'])
            else:
                default = False
            
            # If the status is both enabled and default then return it as the default
            if disabled == False and default:
                
                # Cache the default status
                self.default_status = status_id
                
                return status_id

    def blankToNone(self, value, strip_first=False):
        """
        Returns none if the given value is an empty string.
        
        Arguments:
        value -- The string to be considered if it is empty
        strip_first -- If true, strip will be called on the string before determining if is blank.
        """
        
        # Return none if the value is already none
        if value is None:
            return None
        
        # Strip the whitespace if requested
        if strip_first:
            value = value.strip()
        
        # If the value is empty then return None
        if len(value) == 0:
            return None
        
        # Otherwise, return the value
        else:
            return value

    def parseDateTime(self, date):
        """
        Parse the date from a string into a float.
        
        Arguments:
        date -- The date as a string to be parsed (using strptime)
        """
        
        ts = strptime(date, '%m/%d/%Y %H:%M:%S GMT')
        return calendar.timegm(ts) 

    def addIfNewer(self, statuses_dict, new_status):
        """
        Adds the given status to the dictionary if it is later than another entry in the dictionary that has the same rule_id. Returns true if the item was added.
        
        Arguments:
        statuses_dict --A dictionary containing LogReviewStatus objects with the key set to the rule_id
        new_status -- A LogReviewStatus object
        """
        
        # This boolean indicates if the item already existed
        existing_newer_found = False
        
        # Search the list and determine if a newer exist
        existing_status = statuses_dict.get(new_status.rule_id, None)
        
        if existing_status is not None and existing_status.time >= new_status.time:
            existing_newer_found = True
        
        # Do not add the item if it already exists
        if existing_newer_found:
            return False
        
        # Add the entry if it is newer
        else:
            statuses_dict[new_status.rule_id] = new_status
            return True

    @time_function_call
    def readCurrentValues(self, ruleUIDs, file_handle=None, reader=None):
        """
        Read the current values from the incident review lookup file.
            
        Arguments:
        ruleUIDs -- A list of the events to change (as a list of strings)
        file_handle -- A handle to the incident review lookup file (will be used to instantiate a CSV reader if a reader is not provided)
        reader -- A CSV reader object based on the incident review
        """
        
        # Just use the reader if provided, otherwise, load one from the file handle
        if reader is None:
            reader = csv.reader(file_handle, lineterminator='\n')
        
        # Load the CSV of statuses
        existing_statuses = {}
        
        # This variable will help us remember if we are on the first row so that we can skip it
        first_row = True
        line = 0
        
        for status_row in reader:
            
            line = line + 1
            
            # Skip the first row since it contains the header
            if first_row:
                first_row = False
                continue
            
            # Don't bother loading the item unless it is one of them in the list
            if ruleUIDs is None or status_row[self.CSV_INCIDENT_REVIEW_RULE_ID] in ruleUIDs:
                
                try:
                    # Parse out the time
                    t = self.parseDateTime( status_row[self.CSV_INCIDENT_REVIEW_TIME] )
    
                    # Populate the fields to make the status
                    rule_id = status_row[self.CSV_INCIDENT_REVIEW_RULE_ID]
                    owner = status_row[self.CSV_INCIDENT_REVIEW_OWNER]
                    urgency = status_row[self.CSV_INCIDENT_REVIEW_URGENCY]
                    status = status_row[self.CSV_INCIDENT_REVIEW_STATUS]
                    comment = status_row[self.CSV_INCIDENT_REVIEW_COMMENT]
                    user  = status_row[self.CSV_INCIDENT_REVIEW_USER]
                    
                    # Create the status
                    existing_status = LogReviewStatus(t, rule_id, owner, urgency, status, comment, user )
                    
                    # Add the status if it is newer than the existing items
                    self.addIfNewer( existing_statuses, existing_status )
                    
                except IndexError:
                    # Could not find one of the rows, go ahead and skip it
                    logger.warn( "An entry in the incident review is invalid, line=%d" % (line) )
                
        # Return the statuses list
        return existing_statuses
        
    @time_function_call
    def getCurrentValues(self, ruleUIDs=None):
        """
        Get a dictionary containing the most recent status entry for each rule UID provided. If the ruleUID provided is None, then the newest of all entries will be returned.
        
        Arguments:
        ruleUIDs -- A list of ruleUIDs that correspond to the status entries that are to be returned (a list of strings)
        """
        
        # These variables will retain the instances related to the CSV file reading
        file_handle = None
        
        logger.debug("Getting current incident review statuses from the lookup file...")
        
        try:
            with portalocker.Lock(self.getLookupsFilePath(), timeout=self.FILE_LOCK_TIMEOUT, mode="r", truncate=None) as file_handle:
                
                # Get the statuses
                existing_statuses = self.readCurrentValues(ruleUIDs, file_handle=file_handle)
                
        except RuntimeError: 
            # File-locking is not supported, default to the existing method of reading in the file
            logger.debug("Reading the lookup file without locking support")
            
            file_handle = None
            
            try:
                reader, file_handle = self.getCSVReader()
                
                existing_statuses = self.readCurrentValues(ruleUIDs, reader=reader)
            finally:
                
                if file_handle is not None:
                    file_handle.close()
            
        # Return the statuses list
        logger.debug("Done getting current incident review statuses from the lookup file") 
        return existing_statuses

    @time_function_call
    def getCorrelationSearches(self, force_refresh=False):
        """
        Obtains a list of correlation searches from splunkd via REST. Cached results may be returned (if available) unless force_refresh is set to true.
        
        Arguments:
        force_refresh -- If true, reload the correlation searches info
        """
        
        # Return the cached results if we have them
        if force_refresh == False and self.correlation_searches is not None:
            return self.correlation_searches
        
        # Get the correlation searches data from the REST endpoint
        logger.debug("Reloading the correlation searches")
        self.correlation_searches = entity.getEntities('alerts/correlationsearches', count=-1, sessionKey=self.sessionKey )
        logger.debug("%s correlation searches loaded" % (len(self.correlation_searches)) )
        
        return self.correlation_searches
    
    def getCorrelationSearchRuleName(self, correlation_search_name, force_refresh=False):
        """
        Get the nice name of the correlation search (the "rule_name" field).
        
        Arguments:
        correlation_search_name -- The name of the correlation to get the rule_name for
        force_refresh -- If true, reload the correlation searches info
        """
        
        # Get the list
        correlation_searches = self.getCorrelationSearches(force_refresh)
            
        # Iterate through the list and find the entry
        for name, settings in correlation_searches.items():
            if correlation_search_name == name:
                return settings['rule_name']
            
        # Couldn't find it, sorry
        return None
        
    
    @time_function_call
    def getStatus(self, rule_id, correlation_search, existing_statuses, force_refresh=False):
        """
        Get the status code for the notable event with the given ID. This function will return the first status it can find from the following sources:
        
         1) The status of the latest notable event per the incident review list
         2) The default status assigned for the given correlation search
         3) The system-wide default status
         4) The status of "Unassigned" (0)
        
        Arguments:
        rule_id -- The value of the event (as a string); is used to find if an existing entry exists in the incident review lookup table
        correlation_search -- The correlation search that the given rule_id corresponds to (as a string); used to get the default status that is assigned to the given correlation search
        existing_statuses -- List of existing statuses from the incident review lookup (a dictionary of LogReviewStatus objects with the key being the rule_id); used to obtain the current status of the event
        force_refresh -- If true, reload the information about the correlation searches
        """
        
        # Determine if the correlation search has an existing status in incident review
        if rule_id in existing_statuses:
            existing_status_entry = existing_statuses[rule_id]
            logger.debug("Found existing status (%s) for %s" % (existing_status_entry.status, rule_id) )
        else:
            existing_status_entry = None
        
        # Return the status if it is not blank
        if existing_status_entry is not None and len(existing_status_entry.status) > 0:
            logger.debug("Returning status from: existing entry, status=%s, rule_id=%s" %(existing_status_entry.status, rule_id) )
            return existing_status_entry.status
        
        # If a status was not found in the incident review then use the default that is assigned for the correlation search
        status = self.getDefaultCorrelationSearchStatus(correlation_search, force_refresh)
        
        if status is not None:
            logger.debug("Returning status from: correlation search default, status=%s, rule_id=%s" %(status, rule_id) )
            return status
        else:
            logger.debug("Could not find correlation search default status for search '%s', rule_id=%s" %(correlation_search, rule_id) )
        
        # Use the default status if we could not get a status
        status = self.getDefaultStatus()
        
        if status is not None:
            logger.debug("Returning status from: system default, status=%s, rule_id=%s" %(status, rule_id) )
            return status
        
        # If we were unable to find a status, then return the default
        logger.debug("Returning status from: module default, status=%s, rule_id=%s" %(self.DEFAULT_NOTABLE_EVENT_STATUS, rule_id) )
        return self.DEFAULT_NOTABLE_EVENT_STATUS

    @time_function_call
    def updateEvent(self, rule_id, urgency, status, comment, newOwner, writer, reviewTime, currentUser = None, existing_statuses = None, correlation_search_name=None) :
        """
        Update the incident review history for the given rule ID.
        
        Arguments:
        rule_id -- The rule ID to modify
        urgency -- The urgency to set the events to
        status -- The status to assign the events to
        comment -- A comment describing the change
        newOwner -- The owner to assign the events to
        writer -- A CSV writer instance to write the events out to
        reviewTime -- A string representing the review time
        currentUser -- The user performing the changes
        existing_statuses -- List of existing statuses from the incident review lookup (a dictionary of LogReviewStatus objects with the key being the rule_id); used to obtain the current status of the event
        correlation_search_name -- The name of the correlation search
        """
        
        # Get the existing status if it exists
        existing_status = None
        
        if rule_id in existing_statuses:
            existing_status = existing_statuses[rule_id]
            
        # Use the existing statuses if it exists
        if existing_status is not None:
            
            writer.writerow( [reviewTime,
                              rule_id,
                              self.valueIfNotNone(newOwner, existing_status.owner),
                              self.valueIfNotNone(urgency, existing_status.urgency),
                              self.valueIfNotNone(status, existing_status.status),
                              comment,
                              currentUser,
                              correlation_search_name] )
        else:
            writer.writerow( [reviewTime, rule_id, newOwner, urgency, status, comment, currentUser, correlation_search_name] )

        
        return True

    @time_function_call
    def getSearchResults(self, searchID):
        """
        Get the search results for the given search ID.
        
        Arguments:
        searchID -- A search ID containing the results that should be obtained
        """
        
        job = splunk.search.getJob(searchID, sessionKey=self.sessionKey)
        
        if not job.isDone:
            raise SearchNotDoneException("Search is not done, search must be completed before results can be processed")
        
        if job.reportSearch:
            logger.warn("The search ID %s is not an event search but one that provides processed results; only an event search can be used for editing notable events" % (searchID))
            raise NotEventSearchException("Search must be an event search that provides raw events (not results)")

        return getattr(job, 'events')

    @time_function_call
    def setStatusBySearchID(self, searchID, urgency, status, comment, newOwner, writer, reviewTime, currentUser = None, force_refresh = False, rule_ids_to_change=None, existing_statuses=None) :
        """
        Set the status of the events that match a search with the given ID.
        
        Arguments:
        searchID -- A search ID containing the results that should be modified
        urgency -- The urgency to set the events to
        status -- The status to assign the events to
        comment -- A comment describing the change
        newOwner -- The owner to assign the events to
        writer -- A CSV writer instance to write the events out to
        reviewTime -- A string representing the review time
        currentUser -- The user performing the changes
        rule_ids_to_change -- A list of rules IDs that ought to be changed (a list of strings); if none, then all events matching the search will be modified (none is the default)
        """
        
        # This class instance will record the number of events successfully changed
        status_change_meta = LogReviewStatusChanges()
        
        # Get the search job (this will throw a splunk.ResourceNotFound exception if the search cannot be found)
        try:
            dataset = self.getSearchResults(searchID)
        except splunk.ResourceNotFound:
            
            logger.warn("The search ID %s is no longer accessible, please refresh and try editing the events again", (searchID))
            status_change_meta.incrementFailureCountEx(["The search is no longer accessible, please refresh and try editing the events again"])
            return status_change_meta
        
        except NotEventSearchException:
            
            status_change_meta.incrementFailureCountEx(["The search is not an event search; searches returning results (instead of events) cannot be used"])
            return status_change_meta
        
        except SearchNotDoneException:
            
            status_change_meta.incrementFailureCountEx(["The search is not done; the search must be completed before results can be processed"])
            return status_change_meta
        
        # Get the existing statuses so that the entries can inherit items as necessary
        if existing_statuses is None:
            existing_statuses = self.getCurrentValues(rule_ids_to_change)
        
        # Get the user capabilities
        capabilities = self.getCapabilities4User(currentUser)
        
        # Make sure the comment is the minimum length (if defined)
        minimum_length = self.commentLengthRequired()
        
        if len(comment.strip()) < minimum_length:
            
            # Return a message noting that the minimum length was not met
            status_change_meta.incrementFailureCountEx(["comment length does not meet minimum requirement (must be %d characters long or more)" % (minimum_length)])
            return status_change_meta
        
        # Determine if urgency changes are allowed
        allowUrgencyChanges = self.isUrgencyOverrideAllowed()
        
        # If we are not allowed to change the urgency, then set it to none to indicate that it ought not be changed
        if allowUrgencyChanges == False:
            urgency = None
        
        # Make a copy of the rules IDs that we are planning to change so that we can exit early from looping through the search results once we get done editing the entries
        rule_ids_to_change_left = None
        
        if rule_ids_to_change is not None:
            rule_ids_to_change_left = rule_ids_to_change[:] # Make a copy, we don't want to edit the original
    
        c = 0
        
        # Create a status entry for each event
        for event in dataset:
            c = c + 1
            
            # Stop processing the events if already handled all of the events we expected to handle
            if rule_ids_to_change_left is not None and len(rule_ids_to_change_left) == 0:
                break
            
            # Get the rule UID
            if 'rule_id' in event:
                
                # Get the rule UID
                rule_id = str(event['rule_id'])
                
                # Only change the given event if it is in the list to change
                if rule_ids_to_change is not None and rule_id not in rule_ids_to_change:
                    continue
                
                # Get the correlation search name
                if 'source' in event:
                    correlation_search = str(event['source'])
                else:
                    correlation_search = None
                    
                # Get the "rule_name" of the search
                if correlation_search is not None:
                    correlation_search_name = self.getCorrelationSearchRuleName(correlation_search)
                else:
                    correlation_search_name = None
            
                # Make sure that the user has the capability
                capability_issues = self.checkTransition( rule_id, correlation_search, status, capabilities, existing_statuses, force_refresh)
                
                # Stop if the permission check failed
                if capability_issues is not None and len(capability_issues) > 0:
                    status_change_meta.incrementFailureCountEx(capability_issues)
                
                # Increment the counter if the event got updated correctly
                elif self.updateEvent( rule_id, urgency, status, comment, newOwner, writer, reviewTime, currentUser, existing_statuses, correlation_search_name=correlation_search_name ):
                    status_change_meta.incrementSuccessCount()
                     
                    # Remove the item that we changed so that we can determine if we get to exit the loop early
                    if rule_ids_to_change_left is not None:
                        rule_ids_to_change_left.remove(rule_id)
                    
                # Event was not updated successfully
                else:
                    status_change_meta.incrementFailureCount('notable event could not be updated')
                
            else:
                status_change_meta.incrementFailureCount("rule_id field not found in the event")
        
        logger.debug("Evaluated %i events for editing", c)
        
        # Return the count of the events that were updated
        return status_change_meta
    
    def valueIfNotNone(self, value, existing_value):
        value = self.blankToNone( value )
        
        if value is None:
            return existing_value
        else:
            return value
    
    @time_function_call
    def setStatusByIDs(self, ruleUIDs, urgency, status, comment, newOwner, writer, reviewTime, currentUser = None, existing_statuses=None) :
        """
        Set the status of the events with the given rule IDs
        
        Arguments:
        ruleUIDs -- A list of the events to change (as a list of strings)
        urgency -- The urgency to set the events to
        status -- The status to assign the events to
        comment -- A comment describing the change
        newOwner -- The owner to assign the events to
        writer -- A CSV writer instance to write the events out to
        reviewTime -- A string representing the review time
        currentUser -- The user performing the changes
        """
        
        # Get the existing statuses
        if existing_statuses is None:
            existing_statuses = self.getCurrentValues(ruleUIDs)
        
        # This class provides information on the operations performed
        status_change_meta = LogReviewStatusChanges()
        
        # Make sure the comment is the minimum length (if defined)
        minimum_length = self.commentLengthRequired()
        
        if len(comment.strip()) < minimum_length:
            
            # Return a message noting that the minimum length was not met
            status_change_meta.incrementFailureCountEx(["comment length does not meet minimum requirement (must be %d characters long or more)" % (minimum_length)])
            return status_change_meta
        
        # Append the new entries
        for ruleUID in ruleUIDs:
            
            existing_status = None
            
            # Get the existing status if it exists
            if ruleUID in existing_statuses:
                existing_status = existing_statuses[ruleUID]
            
            # Use the existing statuses if it exists
            if existing_status is not None:
                
                writer.writerow( [reviewTime,
                                  ruleUID,
                                  self.valueIfNotNone(newOwner, existing_status.owner),
                                  self.valueIfNotNone(urgency, existing_status.urgency),
                                  self.valueIfNotNone(status, existing_status.status),
                                  comment,
                                  currentUser,
                                  ""] )
            else:
                writer.writerow( [reviewTime, ruleUID, newOwner, urgency, status, comment, currentUser, ""] )
            
            # Increment the number of events updated
            status_change_meta.incrementSuccessCount()
                
        # Return the number of events updated
        return status_change_meta
    
    @time_function_call
    def commitChanges(self, urgency, status, comment, newOwner, currentUser = None, ruleUIDs = None, searchID = None) :
        """
        Commit the changes to the incident review lookup. Returns a LogReviewStatusChanges instance that describes the result of the operation.
        
        Arguments:
        urgency -- The urgency to set the events to
        status -- The status to assign the events to
        comment -- A comment describing the change
        newOwner -- The owner to assign the events to
        currentUser -- The user performing the changes
        ruleUIDs -- A list of the events to change (as a list of strings)
        searchID -- A search ID containing the results that should be modified
        """
        
        # Get the current user
        if currentUser is None:
            currentUser = self.request['userName']
        
        # Get the time to be used
        reviewTime = strftime('%m/%d/%Y %H:%M:%S', gmtime()) + ' GMT'
        
        # Get the existing statuses
        existing_statuses = self.getCurrentValues(ruleUIDs)
        
        # Process the results
        try:
            
            # Try with locking support
            with portalocker.Lock(self.getLookupsFilePath(), timeout=self.FILE_LOCK_TIMEOUT, truncate=None) as file_handle:
                return self.setStatuses(file_handle, urgency, status, comment, newOwner, currentUser, ruleUIDs, searchID, reviewTime, existing_statuses)
        except RuntimeError:
            
            # Try without locking support
            try:
                # File-locking is not supported, default to the existing method of reading in the file
                logger.debug("Writing the lookup file without locking support")
                
                file_handle, writer = self.getCSVWriter()
                return self.setStatuses(file_handle, urgency, status, comment, newOwner, currentUser, ruleUIDs, searchID, reviewTime, existing_statuses, writer)
                
            finally:
            
                # Close the file handle if it isn't null
                if file_handle is not None:
                    file_handle.close()

            
        return LogReviewStatusChanges()
    
    @time_function_call
    def setStatuses(self, file_handle, urgency, status, comment, newOwner, currentUser, ruleUIDs, searchID, reviewTime, existing_statuses, writer=None):
        """
        Commit the changes to the incident review lookup. Returns a LogReviewStatusChanges instance that describes the result of the operation.
        
        Arguments:
        file_handle -- A file handle to the CSV file to be edited (will be NOT closed when the function terminates)
        urgency -- The urgency to set the events to
        status -- The status to assign the events to
        comment -- A comment describing the change
        newOwner -- The owner to assign the events to
        currentUser -- The user performing the changes
        ruleUIDs -- A list of the events to change (as a list of strings)
        searchID -- A search ID containing the results that should be modified
        reviewTime -- The time to be entered as the date/time that the user reviewed the entries
        existing_statuses -- A dict containing LogReviewStatus objects with the key set to the rule_id
        writer -- A reference to the CSV writer (will be instantiated automatically if not provided)
        """
        
        # Initialize the writer
        if writer is None:
            writer = csv.writer(file_handle, lineterminator='\n')
        
        # Print a log message noting that an operation is about to happen
        if ruleUIDs is not None:
            logger.info("About to edit events matching search %s (though only %d events are to be modified)" % ( searchID, len(ruleUIDs) ) )
        else:
            logger.info("About to edit events matching all events matching search %s" % ( searchID ) )
            
        # Refresh the correlation searches list so we don't have to later
        self.getCorrelationSearches(force_refresh=True)
        
        # Perform the changes
        if searchID is None:
            
            result = self.setStatusByIDs(ruleUIDs, urgency, status, comment, newOwner, writer, reviewTime, currentUser, existing_statuses=existing_statuses)
            
            logger.info("Done editing events" )
            return result
        else:
            
            result = self.setStatusBySearchID(searchID, urgency, status, comment, newOwner, writer, reviewTime, currentUser, force_refresh=False, rule_ids_to_change=ruleUIDs, existing_statuses=existing_statuses)
            
            logger.info("Done editing events matching search %s" % ( searchID ) )
            return result
        
    @time_function_call
    def checkTransition(self, rule_id, correlation_search, status, capabilities, existing_statuses = None, force_refresh=False) :
        """
        Check and make sure that the user can transition the given rules. Returns a list of messages that describes the issues found. An empty list indicates that no issues were found.
        
        Arguments:
        
        rule_id -- The rule ID of the event to be checked (string)
        status -- The status that we are checking if we can transition to (a string denoting the status ID, can be none or blank to indicate no change)
        capabilities -- A list of the capabilities that will be checked (a list of strings)
        existing_statuses -- A list of existing statuses of notable events in a dictionary containing LogReviewStatus objects with the key set to the rule_id
        """
        
        # Populate the existing_statuses if not pre-populated
        if existing_statuses is None:
            existing_statuses = self.getCurrentValues()
        
        # Below if the list that will contain all of the problems
        messages = []
        
        # Below is the status label map)
        statusLabelMap = self.getStatusLabelMap(force_refresh)
        
        # Make sure the current user has the edit_notable_events capability
        if ("edit_notable_events" not in capabilities) :
            messages.append(_("you are not authorized to edit notable events"))
            return messages
        
        # Get the current status of the given notable event
        currentStatus = self.getStatus(rule_id, correlation_search, existing_statuses, force_refresh)
        
        # No transition check is needed if we are not changing the status
        if currentStatus == status or status is None or len(status) == 0:
            return messages # No transition checking necessary since we are not changing the status, return the given set of messages
        
        # Get the matching capability
        matchingCapability = "transition_reviewstatus-" + str(currentStatus) + "_to_" + str(status)
        
        # Generate a warning if the capability is not in the list of allowed transitions
        if matchingCapability not in capabilities :
            
            newMessage = None
            
            # Get the current label and status
            try:
                currentStatusLabel = statusLabelMap[currentStatus]
            except KeyError:
                # The current status does not seem to exist. Allow the transition in order to prevent blocking the user from transitioning the
                # event (otherwise, they will never be able to change the given events).
                logger.error("Status with ID %s is not valid, transitioning of this event will be allowed") % (str(currentStatus) )
                currentStatusLabel = "Unknown"
                return messages
                
            # Get the new label and status
            try:
                newStatusLabel = statusLabelMap[status]
            except KeyError:
                logger.error("Status with ID %s is not valid") % (str(status) )
                newMessage = _("No such status could be found with an ID of %s") % (str(currentStatusLabel))
                
            # Create the message unless one has already been created (which would indicate another check has already failed)
            if newMessage is None:
                newMessage = _("transition from %s to %s is not allowed") % (str(currentStatusLabel),str(newStatusLabel))
                logger.info("Transition of event %s from %s to %s is not allowed" % ( rule_id, str(currentStatusLabel), str(newStatusLabel) ))
            
            # Append the message if it is not unique
            if newMessage not in messages:
                messages.append(newMessage)
        else:
            logger.info("Capability %s allows transition of event %s from %s to %s" % ( matchingCapability, rule_id, str(currentStatus), str(status)  ))
        
    
        # Return the messages
        return messages

    @time_function_call
    def makeChanges(self, host_app, client_app, status, comment, newOwner=None, urgency=None, ruleUIDs=None, searchID=None, **args):
        """
        Make changes to the notable events that are requested.
        """
        
        app = client_app
        response = {}

        try:
            
            # 0 -- Precondition checks
            
            #    0.1 -- Make sure the ruleUIDs provided are an array; if it is a string then convert it to an array
            if ruleUIDs is not None and isinstance( ruleUIDs, list ) == False:
                ruleUIDs = [ruleUIDs]
            
            #    0.2 -- Make sure the search ID was provided
            if searchID is None and ruleUIDs is None:
                response = {
                  "success": False, 
                  "message": _("No search ID was provided.")
                }
                
                return response
            
            # 1 -- Replace values that are blank with None
            urgency = self.blankToNone(urgency)
            status = self.blankToNone(status)
            newOwner = self.blankToNone(newOwner)
            
            # 2 -- Check capabilities
            
            #    2.1 -- Get the user name performing the changes
            currentUser = self.request['userName']
            
            #    2.2 -- Check authorization
            # if currentStatus is unassigned then what?  
            # Do we allow a change to ANY other status?
            # because that seems problematic...
            # Perhaps we treat 'unassigned' as 'new'
            
            # Get the capabilities for the current user
            capabilities = self.getCapabilities4User(currentUser)
            
            # See if the user can change events at all; note that this will be checked again for each rule but this prevent us from trying when we know we will fail
            if ("edit_notable_events" not in capabilities) :
                response["success"] = False
                response["message"] = _("Event status could not be updated due to insufficient permissions")
                
                # Return the response
                return response
            
            # 3 -- Perform the changes
            
            # Perform the action
            status_change_summary = self.commitChanges(urgency, status, comment, newOwner, currentUser, ruleUIDs, searchID)
            
            # Add additional details that will be used to display additional messages
            response["details"] = status_change_summary.messages
            response["success_count"] = status_change_summary.success_count
            response["failure_count"] = status_change_summary.getFailureCount()
            
            # Consider the operation a success if some entries were changed so that the view updates
            if status_change_summary.success_count > 0:
                response["success"] = True
            else:
                response["success"] = False
            
            # If we got some errors, then post them
            if ( len(status_change_summary.messages) ) > 0:
                error_message = status_change_summary.getMessagesAsString()
                response["message"] = error_message
            else:
                response["message"] = _("%s updated successfully") % ungettext(_("%(count)s event"), _("%(count)s events"), status_change_summary.success_count) % {'count': status_change_summary.success_count}

            # Return the response
            return response
        
        except (portalocker.LockException, portalocker.utils.AlreadyLocked):
            # Tell the user that we unable to change the lookup file because someone is editing it and the file locked
            response["success"] = False
            response["message"] = "The incident review lookup file is currently being edited, please wait a bit and re-submit your changes"
            
            logger.warn("Incident review lookup is currently locked")
            
            # Return the response
            return response
    
        except Exception as e:
            
            # This will be the error message returned
            result = "Error: "
            
            # Let's get the stacktrace so that debugging is easier
            et, ev, tb = sys.exc_info()
            
            # Change the result to include a description of the stacktrace
            while tb :
                co = tb.tb_frame.f_code
                filename = "Filename = " + str(co.co_filename)
                line_no = "Error Line # = " + str(traceback.tb_lineno(tb))
                result = result + str(filename)
                result = result + str(line_no)
                result = result + "\n"
                
                tb = tb.tb_next

            #Add the exception type and vale to the message
            result = result + "\net = " + str(et)
            result = result + "\nev = " +  str(ev)
            
            # Create the resulting message
            response["success"] = False
            response["message"] = "The update failed:" + str(e)
            response["tb"] = result
            
            # Return the response
            return response