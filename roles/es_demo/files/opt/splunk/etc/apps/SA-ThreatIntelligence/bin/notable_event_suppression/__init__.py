import logging
import logging.handlers
import lxml.etree as et
import os
import re
import splunk.admin as admin
import splunk.entity as en
import splunk.rest as rest
import splunk.search as search
import splunk.util as util
from splunk import ResourceNotFound
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
    """
    Setup a logger for the REST handler.
    """
   
    logger = logging.getLogger('notable_event_suppression')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
   
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'notable_event_suppression.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
   
    logger.addHandler(file_handler)
   
    return logger

logger = setup_logger()


class UnauthorizedUserException(Exception):
    pass


class NotableEventSuppression:
    """
    Represents a Notable Event Suppression
    """
    
    ## Defaults:
    DEFAULT_NAMESPACE = 'SA-ThreatIntelligence'
    DEFAULT_OWNER = 'nobody'
    EVENTTYPES_REST_URL = 'alerts/suppressions'
    SUPPRESSION_START = "notable_suppression-"
    
    suppressionRE = re.compile('^notable_suppression-(.+)$')
    sourceRE = re.compile('source=[\'"]([^\'"]+)')
    startRE = re.compile('_time\s*>[=]?\s*(\d+(?:\.\d+)?)')
    endRE = re.compile('_time\s*<[=]?\s*(\d+(?:\.\d+)?)')
    
    def __init__(self, id, enabled, description=None, search=None):        
        ## ID/Stanza
        self.id = id
        
        ## Human-readable name
        self.name = id
        
        nameMatch = NotableEventSuppression.suppressionRE.match(id)
        
        if nameMatch:
            self.name = nameMatch.group(1)
        else:
            logger.error("The Notable Event Suppression does not match expected convention")
            
        ## Enabled
        self.enabled = enabled
        
        ## Human-readable description
        if description is None:
            description = ''
        self.description = description
        
        ## Search
        if search is None:
            self.search = ''
            self.source = ''
            
        else:
            self.search = search
            
            sourceMatch = NotableEventSuppression.sourceRE.findall(search)
            
            if len(sourceMatch) == 1:
                self.source = sourceMatch[0]
            
            else:
                self.source = ''
        
        ## Start Time
        self.start = ''
        
        startMatch = NotableEventSuppression.startRE.findall(search)
        if len(startMatch) > 0:
            self.start = startMatch[0]
            
        else:
            logger.warn("Could not determine start time of suppression '%s' from search '%s'" % (id, search))
                    
        ## End Time
        self.end = ''
        
        endMatch = NotableEventSuppression.endRE.findall(search)
        if len(endMatch) > 0:
            self.end = endMatch[0]
            
        else:
            logger.warn("Could not determine expiration time of suppression '%s' from search '%s'" % (id, search))
    
    def save(self, new=False, session_key=None, namespace=None, owner=None):
        """
        Saves the notable event status. If an ID is set, then the existing status will be updated. Otherwise, a new one will be created.
        """
        
        ## Get the owner and namespace
        if namespace is None:
            namespace = NotableEventSuppression.DEFAULT_NAMESPACE
            
        if owner is None:
            owner = NotableEventSuppression.DEFAULT_OWNER
        
        ## Try to get the session key if not provided
        session_key = NotableEventSuppression.__get_session_key__(session_key)

        ## If the ID is not set, create a new entry
        if new:
            ## Get the default entity
            notable_suppression = en.getEntity(NotableEventSuppression.EVENTTYPES_REST_URL, '_new', sessionKey=session_key)
        
        ## Otherwise, edit the existing entity
        else:
            ## Get the existing entity
            notable_suppression = en.getEntity(NotableEventSuppression.EVENTTYPES_REST_URL, self.id, namespace=namespace, owner=owner, sessionKey=session_key)
                
        ## Update the entity
        notable_suppression = self.__populate_entity__(notable_suppression, new)
                
        ## Save the entity
        en.setEntity(notable_suppression, sessionKey=session_key)
            
        return True
        
    def __populate_entity__(self, entity, new=False, namespace=None, owner=None):
        
        # Set the namespace
        if entity.namespace is None and namespace is None:
            entity.namespace = NotableEventSuppression.DEFAULT_NAMESPACE
        elif namespace is not None:
            entity.namespace = namespace
        else:
            entity.namespace = NotableEventSuppression.DEFAULT_NAMESPACE
        
        # Set the owner
        if entity.owner is None and owner is None:
            entity.owner = NotableEventSuppression.DEFAULT_OWNER
        elif owner is not None:
            entity.owner = owner
        else:
            entity.owner = NotableEventSuppression.DEFAULT_OWNER
        
        if new:
            entity["name"] = self.id
            
        entity["disabled"] = not self.enabled
        entity["description"] = self.description 
        entity["search"] = self.search
        
        return entity
                       
    ## Parses time strings using /search/timeparser endpoint
    @staticmethod
    def timeParser(ts='now', session_key=None):
        getargs = {}
        getargs['time'] = ts

        tsStatus, tsResp = rest.simpleRequest('/search/timeparser', sessionKey=session_key, getargs=getargs)
        
        root = et.fromstring(tsResp)  
    
        ts = root.find('dict/key')
        if ts != None:
            return util.parseISO(ts.text, strict=True)
  
        else:
            logger.warn("Could not retrieve timestamp for specifier '%s' from /search/timeparser" % (getargs['time']) )
            return False               

    @staticmethod
    def enable(id, session_key=None):
        """
        Enable the given suppression.
        """

        return NotableEventSuppression.set_suppression(id, True, session_key)
    
    @staticmethod
    def disable(id, session_key=None):
        """
        Disable the given suppression.
        """
        
        return NotableEventSuppression.set_suppression(id, False, session_key)
    
    @staticmethod
    def set_suppression(id, enable, session_key=None):
        """
        Enables/disable the given suppression. Returns true if the suppression was successfully disabled.
        """        
        # Try to get the session key if not provided
        session_key = NotableEventSuppression.__get_session_key__(session_key)
        
        # Get the appropriate entity
        entity = en.getEntity(NotableEventSuppression.EVENTTYPES_REST_URL, id, namespace=NotableEventSuppression.DEFAULT_NAMESPACE, owner=NotableEventSuppression.DEFAULT_OWNER, sessionKey=session_key)
        
        # Disable/enable the suppression
        entity['disabled'] = not enable
        en.setEntity(entity, sessionKey=session_key)
        
        return True
    
    @staticmethod
    def __get_session_key__(session_key=None, thrown_exception=True):
        
        # Try to get the session key if not provided
        if session_key is None:
            import splunk
            session_key, sessionSource = splunk.getSessionKey(return_source=True)
        
        # Do not continue if we could not get a session key and the caller wants us to thrown an exception
        if session_key is None and thrown_exception:
            raise NoSessionKeyException("Could not obtain a session key")
        
        # Return the session key
        return session_key
    
    @staticmethod
    def is_enabled(suppression_dict):
        """
        Determine if the given suppression is enabled
        """
        
        # Get the disabled flag
        if 'disabled' in suppression_dict:
            return not NotableEventSuppression.get_boolean(suppression_dict['disabled'], False)
        else:
            return False
    
    @staticmethod
    def get_metadata(session_key=None):
        """
        Dispatch a metadata search to retrieve firstTime values
        per sources (correlation search names) in the notable event index
        """
        logger.info('Dispatching metadata search')
        job = search.dispatch('| metadata type=sources index=notable | fields firstTime, source', sessionKey=session_key)
        
        logger.info('Waiting for metadata search')
        search.waitForJob(job)
        
        logger.info('Returning metadata search results')
        return job.results
     
    @staticmethod
    def is_expired(suppression, metadata=[], session_key=None):
        """
        Determine if the given suppression is expired
        """
        source = ''
        firstTime = 0
        matchFound = False
        
        ## If suppression has an end time
        if suppression.end != '':
            
            ## Convert to integer
            try:
                suppression.end = int(suppression.end)
                
            except:
                logger.error("Suppression end time %s could not be converted to an integer value for comparison" % (suppression.end))
                return False
            
            ## If suppression has a source defined
            if len(suppression.source) > 0:
                logger.info("Searching metadata results for source '%s'" % (suppression.source))   
                ## Iterate metadata
                for result in metadata:
                    source = str(result.get('source'))
                    tempFirstTime = str(result.get('firstTime', 0))
                    
                    ## If metadata source suppression source matches                       
                    if source == suppression.source:
                        logger.info("Metadata source match found with notable event firstTime %s for source '%s'" % (tempFirstTime, suppression.source))
                        matchFound == True
                        
                        try:
                            firstTime = int(tempFirstTime)
                            
                        except:
                            pass

            ## IF suppression has NO source defined or no match was found in available data
            if len(suppression.source) == 0 or not matchFound:
                logger.warn("Suppression '%s' has no source defined or a source match was not found; using earliest firstTime to determine expiration" % (suppression.id))
                
                first = True
                
                ## Iterate metadata
                for result in metadata:
                    try:
                        tempFirstTime = int(str(result.get('firstTime', 0)))
                        
                        if first:
                            firstTime = tempFirstTime
                            first = False
                        
                        else:
                            ## If metadata firstTime less than stored firstTime
                            if tempFirstTime < firstTime:
                                firstTime = tempFirstTime
                                
                    except:
                        pass

            ## If firstTime greater than suppression end time
            logger.debug("suppression=%s; suppression.source=%s; suppression.end=%s; firstTime=%s" % (suppression.id, suppression.source, suppression.end, firstTime))
            if firstTime > suppression.end:
                return True
                
            else:
                return False
        
        else:
            logger.warn("Could not determine if suppression '%s' is expired because it has no end time defined" % (suppression.id))
            return False
        
    @staticmethod
    def get_boolean(value, default=None):
        """
        Convert the given string value to a boolean. Return the default value if the value does not appear to be a boolean.
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
        
    @staticmethod
    def __create_from_dict__(id, notable_suppression):
        return NotableEventSuppression(id, not NotableEventSuppression.get_boolean(notable_suppression['disabled']), notable_suppression['description'], notable_suppression['search'])
        
    @staticmethod
    def get_notable_suppression(id=id, session_key=None):
        """
        Get the given notable event suppression.
        """
        
        notable_suppression = en.getEntity(NotableEventSuppression.EVENTTYPES_REST_URL, id, namespace=NotableEventSuppression.DEFAULT_NAMESPACE, owner=NotableEventSuppression.DEFAULT_OWNER, sessionKey=session_key)
        
        return NotableEventSuppression.__create_from_dict__(id, notable_suppression)

    @staticmethod
    def disable_expired_suppressions(metadata=None, session_key=None):
        """
        Disables suppressions rules that have expired. Returns a tuple with the number of rules detected as expired followed by the number that had been enabled (but were changed to disabled).
        """        
        logger.info('Retrieving suppressions')
        suppressions = NotableEventSuppression.get_notable_suppressions(session_key=session_key)
        
        logger.info('Detecting expired suppressions')
        expired_count = 0
        enabled_count = 0
                
        if metadata is None:
            metadata = NotableEventSuppression.get_metadata(session_key=session_key)
        
        for suppression in suppressions:
            if len(suppression.end) > 0:
                if NotableEventSuppression.is_expired(suppression, metadata, session_key):
                    expired_count += 1
                    logger.info("Detected expired suppression '%s'; event time(s) exceed suppression end time" % (suppression.id))
                                    
                    if not suppression.enabled:
                        logger.info("Suppression '%s' is already disabled" % (suppression.id)) 
                    
                    else:
                        NotableEventSuppression.disable(suppression.id, session_key=session_key)
                        logger.info("Successfully disabled suppression '%s'" % (suppression.id))
                        enabled_count += 1
                        
        return expired_count, enabled_count
        
    @staticmethod
    def is_name_allocated( name, session_key=None, namespace=None, owner=None):
        
        ## Get the owner and namespace
        if namespace is None:
            namespace = NotableEventSuppression.DEFAULT_NAMESPACE
            
        if owner is None:
            owner = NotableEventSuppression.DEFAULT_OWNER
        
        ## Try to get the session key if not provided
        session_key = NotableEventSuppression.__get_session_key__(session_key)
        
        try:
            en.getEntity(NotableEventSuppression.EVENTTYPES_REST_URL, NotableEventSuppression.SUPPRESSION_START + str(name), namespace=namespace, owner=owner, sessionKey=session_key)
        except ResourceNotFound:
            # This exception indicates that the name does not exist yet
            return False
        
        # The name is unique
        return True
        
    @staticmethod
    def generate_suppression_name( name ):
        """
        Will automatically generate a unique name for the suppression rule that does not conflict with any existing rules.
        """
        
        generated_name = name
        
        if name is None:
            generated_name = ""
        
        # Normalize the name
        regex = re.compile("[^a-zA-Z0-9]+")
        generated_name = regex.sub("_", generated_name)
        
        # Determine if the name exists and try incrementing an integer until it is unique
        for i in range(0, 160000):
            tmp_name = generated_name
            
            if i > 0:
                tmp_name = tmp_name + "_" + str(i)
            
            if not NotableEventSuppression.is_name_allocated( tmp_name ):
                return tmp_name
        
        # Name could not be allocated
        return None
    
    @staticmethod
    def get_notable_suppressions(page=1, entries_per_page=50, sort_by=None, session_key=None):
        """
        Returns a list of the notable suppressions.
        """
        ## Retrieve
        suppressions_list = en.getEntities(NotableEventSuppression.EVENTTYPES_REST_URL, count=-1, namespace=NotableEventSuppression.DEFAULT_NAMESPACE, owner=NotableEventSuppression.DEFAULT_OWNER, sessionKey=session_key)
        
        notable_suppressions = []
        
        # Process each suppression
        for id in suppressions_list:
            
            suppressionMatch = NotableEventSuppression.suppressionRE.match(id)
            
            if suppressionMatch:
                notable_suppression = suppressions_list[id]
            
                # Add the suppression to the list
                notable_suppressions.append( NotableEventSuppression.__create_from_dict__(id, notable_suppression) )
                
        # Return the list of suppressions
        return notable_suppressions
      
    ## get capabilities method    
    @staticmethod
    def getCapabilities4User(user=None, session_key=None):
        roles = []
        capabilities = []
        
        ## Get user info              
        if user is not None:
            logger.info('Retrieving role(s) for current user: %s' % (user))
            userDict = en.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
        
            for stanza, settings in userDict.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            logger.info('Successfully retrieved role(s) for user: %s' % (user))
                            roles = val
             
        ## Get capabilities
        for role in roles:
            logger.info('Retrieving capabilities for current user: %s' % (user))
            roleDict = en.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
            
            for stanza, settings in roleDict.items():
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            logger.info('Successfully retrieved %s for user: %s' % (key, user))
                            capabilities.extend(val)
            
        return capabilities