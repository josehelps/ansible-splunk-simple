import splunk.bundle as bundle

import splunk.admin as admin
import splunk.entity as en

import re

import copy

# The following imports are used for the logger
import time
import logging
import logging.handlers
import os
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

def setup_logger(level, name):
    """
    Setup a logger for the REST handler.
    """
    
    logger = logging.getLogger( name )
    logger.setLevel(level)
    
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'notable_event_status.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter( name + ': %(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

# Setup the handler
logger = setup_logger(logging.DEBUG, "NotableEventStatus")

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

def create_transition_str(status_from, status_to, role):
    
    if hasattr(status_from, "id"):
        status_from = status_from.id
        
    if hasattr(status_to, "id"):
        status_to = status_to.id
    
    return "transition_from_%s_to_%s_for_role_%s" % (status_from, status_to, role)

def create_transition_capability_str(status_from, status_to):
    
    if hasattr(status_from, "id"):
        status_from = status_from.id
        
    if hasattr(status_to, "id"):
        status_to = status_to.id
    
    return "transition_reviewstatus-%s_to_%s" % (status_from, status_to)

def parse_transition_str( trans_str ):
    regex = re.compile("transition_from_([0-9a-zA-Z]*)_to_([0-9a-zA-Z]*)_for_role_(.*)")
    
    r = regex.search( trans_str )
    
    status_from, status_to, role = r.groups()
    
    return status_from, status_to, role

@time_function_call
def get_transition_capabilities( status=None, session_key=None ):
    """
    Get a list of the transition capabilities
    """
    # Get the session key
    session_key = NotableEventStatus.__get_session_key__(session_key)
    
    # Get the related status
    if status is not None and hasattr(status, "id"):
        status = status.id
        
    # Get the capabilities
    capabilities = en.getEntities('alerts/transitions/capabilities', count=-1, sessionKey=session_key)
    
    # Find the capabilities that relate to review statuses
    transition_capabilities = []
    
    # This is the capability we are looking for
    if status is not None:
        to_find = "transition_reviewstatus-" + status
    else:
        to_find = "transition_reviewstatus-"
    
    # Find the relevant capabilities
    for capability in capabilities:
        capability = capability.replace('capability::', '')
                
        # See if the capability matches, store it if it does
        if to_find in capability:
            transition_capabilities.append(capability)
        
    # Return the list of valid matches
    return transition_capabilities

def enabled_to_boolean( status ):
    if status.lower() == "enabled":
        return True
    else:
        return False
    
def boolean_to_enabled( status ):
    if status:
        return "enabled"
    else:
        return "disabled"

class StatusTransition:
    
    NAME_PARSE_REGEX = regex = re.compile("transition_reviewstatus-([a-zA-Z0-9]*)_to_([a-zA-Z0-9]*)")
    
    cached_transition_roles = None # Caches the transitions so that we can reduce the number of REST calls
    
    def __init__(self, name, from_status = None, to_status = None, roles=[], imported_roles=[]):
        self.name = name
        
        if from_status is None or to_status is None:
            self.from_status, self.to_status = StatusTransition.parse_name( name )
        else:
            self.from_status = from_status
            self.to_status = to_status
            
        self.roles = roles[:]
        self.imported_roles = imported_roles[:]
        
    @staticmethod
    def parse_name(name):
        """
        Parses the status transition IDs from the name.
        """
        r = StatusTransition.NAME_PARSE_REGEX.search(name)
        
        if r is None:
            raise Exception("The name %s is not valid" % (name))
        else:
            return r.groups()
        
    def __str__(self):
        return self.name + "{" + str(self.roles) + "}"
    
    def __repr__(self):
        return self.__str__()

    @staticmethod
    def append_transition_list(name, role, transitions, create_if_not_found=True, id=None, is_imported=False):
        """
        Populates the given transition array with StatusTransition instances that correspond to the capability name and role provided.
        """
        found = False
    
        # Find the transition if one matches
        for t in transitions:
            
            # Determine if the given transition is equivalent
            if name == t.name:
                found = True
                
                # Determine if the given role is in the list already
                if is_imported:
                    if role not in t.imported_roles:
                        t.imported_roles.append(role)
                        return True
                        break
                else:
                    if role not in t.roles:
                        t.roles.append(role)
                        return True
                        break
                    
        # If one was not found, then add it to the list
        if found == False:
            
            if is_imported:
                new_trans = StatusTransition(name, imported_roles=[role])
            else:
                new_trans = StatusTransition(name, roles=[role])
                
            # Only add the transition if we are not filtering it
            if id is None or id.lower() == new_trans.from_status.lower():
                transitions.append(new_trans)
                return new_trans
        
    @staticmethod
    @time_function_call
    def __get_roles__(session_key=None):
        """
        Get a list of the roles
        """
        
        # Get the session key
        session_key = NotableEventStatus.__get_session_key__(session_key)
        
        roles = en.getEntities('alerts/transitions/roles/', count=-1, sessionKey=session_key)
        
        roles_list = []
        
        for role, settings in roles.items():
            roles_list.append( role )
            
        return roles_list
    
    @staticmethod
    def get_allowed_roles( status_to, transition_map, roles=None, session_key=None):
        """
        Returns a list of roles with a boolean indicating if the given role is allowed to perform the transition.
        """
        
        # If the roles were not provided, load them
        if roles is None:
            roles = StatusTransition.__get_roles__(session_key)
            
        # Created the basic roles dictionary
        roles_allowed = {}
        
        for r in roles:
            roles_allowed[ r ] = False
            
        # Update the values according to the actual settings
        # Iterate through the transition map and find the entries that match the given status
        for t in transition_map:

            if t.to_status == status_to:
                
                for r in t.roles:
                    roles_allowed[r] = True
                    
                for r in t.imported_roles:
                    roles_allowed[r] = True
                    
        # Return the resulting roles dictionary
        return roles_allowed
    
    
    @staticmethod
    @time_function_call
    def update_transitions(resulting_capabilities_by_role, namespace, session_key=None):
        """
        Updates the transitions based on the provided dictionary. The dictionary must contains the roles to be edited
        as the key with a dictionary for each that represents the capabilities to set. Below is an example:
        
        
        {
            'user' : { 
                        'transition_reviewstatus-0_to_3' : True,
                        'transition_reviewstatus-0_to_2' : False
                     },
            'admin' : { 
                        'transition_reviewstatus-0_to_3' : True,
                        'transition_reviewstatus-0_to_2' : True
                     },
        }
        
        """
        
        # Get the session key
        session_key = NotableEventStatus.__get_session_key__(session_key)
        
        # Process each role
        for role in resulting_capabilities_by_role.keys():            
            # Determine if the role needs to be changed
            conf_changed = False
            
            # Get the role entity
            with TimeLogger("Getting entity alerts/transitions/roles for " + str(role), logger):
                role_entity = en.getEntity('alerts/transitions/roles', role, namespace = namespace, owner = NotableEventStatus.DEFAULT_OWNER, sessionKey=session_key)
            
            # Get the existing capabilities
            role_capabilities = role_entity['capabilities']
            imported_capabilities = role_entity['imported_capabilities']
            
            # Iterate through the list and apply the changes
            for capability in resulting_capabilities_by_role[role].keys():
            
                # Determine if the item ought to be included
                capability_enabled = resulting_capabilities_by_role[role][capability]
                
                # Change the capabilities accordingly but only if they changed
                if capability_enabled and (capability not in role_capabilities and capability not in imported_capabilities):
                    conf_changed = True
                    logger.debug("Changing " + str(capability) + " for " + str(role) + " to enabled")
                    role_entity[capability] = boolean_to_enabled(capability_enabled)
                    
                elif not capability_enabled and (capability in role_capabilities): # We cannot undo imported capabilities so don't bother checking them
                    conf_changed = True
                    logger.debug("Changing " + str(capability) + " for " + str(role) + " to disabled")
                    role_entity[capability] = boolean_to_enabled(capability_enabled)
            
            # Write out the conf items
            if conf_changed:
                with TimeLogger("Setting entity alerts/transitions/roles for " + str(role), logger):
                    result = en.setEntity(role_entity, sessionKey=session_key)
            
        ## Refresh the capabilities so that Splunk begins to use them
        ## Commenting as the handleEdit w/in transitioners rest handler should perform this refresh
        # StatusTransition.__refresh_capabilities__(session_key=session_key)

    @staticmethod
    def __refresh_capabilities__(session_key=None):
        en.refreshEntities('/authentication/providers/services', sessionKey=session_key)

    @staticmethod
    @time_function_call
    def get_enabled_transitions( session_key=None ):
        """
        Obtains a list of the transitions that are enabled
        """
        
        # Get the session key
        session_key = NotableEventStatus.__get_session_key__(session_key)
        
        ## Commenting as the handleList w/in transitioners rest handler should perform this refresh
        #StatusTransition.__refresh_capabilities__(session_key)
        
        transitions = en.getEntities('alerts/transitions/capabilities', count=-1, sessionKey=session_key)
        
        transitions_final = []
        
        for t, settings in transitions.items():
            t = t.replace('capability::', '')
            
            for key, val in settings.items():
                if key == 'disabled':
                    if not NotableEventStatus.get_boolean(val):
                        transitions_final.append( t )
                
        return transitions_final
         
    @staticmethod
    @time_function_call
    def get_transition_map(session_key=None, return_roles_too=False, id=None, include_imported_capabilities=False, force_reload=False):
        """
        Returns an array of transitions that represents which roles can transition which notable event statuses.
        
        If "return_roles_too" is set to true, then the list of roles will be returned in the second argument of a tuple.
        
        Arguments:
        session_key -- The session key to use in the REST calls
        return_roles_too -- Returns a list of roles will be returned in the second argument of a tuple if true
        id -- The id to filter the transitions to (otherwise, all will be returned)
        include_imported_capabilities -- Include the capabilities even if they are imported (otherwise, only those directly assocaited with the role are returned)
        force_reload -- If true, the transitions will be reloaded from REST. Otherwise, cache entries will be used if available.
        """
       
        # Get the session key
        session_key = NotableEventStatus.__get_session_key__(session_key)
        
        # This is the resulting set of transitions
        transitions = []
        
        # Get a list of all of the roles and their respective capabilities
        if force_reload or StatusTransition.cached_transition_roles is None:
            StatusTransition.cached_transition_roles = en.getEntities('alerts/transitions/roles', count=-1, sessionKey=session_key)
        
        roles = StatusTransition.cached_transition_roles
        
        for role, settings in roles.items():
            
            # Get the capabilities
            capabilities = settings['capabilities'][:]
            imported_capabilities = settings['imported_capabilities'][:]
            combined_capabilities = capabilities[:]
            
            # Combine the capabilities into a single array
            for c in imported_capabilities:
                if c not in capabilities:
                    combined_capabilities.append(c)
            
            # Append the given transition
            for capability in capabilities: # Only list the actual capabilities since imported capabilities cannot be toggled off
                
                # Make sure that capability is a status transition
                if "transition_reviewstatus" in capability:
                    StatusTransition.append_transition_list(capability, role, transitions, id=id, is_imported=False)
                    
            # Add the imported capabilities if requested
            if include_imported_capabilities:
                for capability in imported_capabilities:
                    
                    # Make sure that capability is a status transition
                    if "transition_reviewstatus" in capability:
                        StatusTransition.append_transition_list(capability, role, transitions, id=id, is_imported=True)
        
        # Return the transitions
        if return_roles_too:
            return transitions, roles
        else:
            return transitions

class NotableEventStatus:
    """
    Represents a notable event status
    """
    
    DEFAULT_NAMESPACE = 'SA-ThreatIntelligence'
    DEFAULT_OWNER = 'nobody'
    REVIEW_STATUSES_REST_URL = '/alerts/reviewstatuses/'
    
    def __init__(self, id, name, description, enabled=True, is_default=False, transitions=None, hidden = None, selected = None, end = False):
        self.id = id
        self.name = name
        self.description = description
        self.enabled = enabled
        self.is_default = is_default
        self.transitions = transitions
        
        self.hidden = hidden
        self.selected = selected
        self.end = end
        
    @staticmethod
    def is_label_unique( label, session_key = None ):
        """
        Determines if the given label is unique.
        """
        
        return NotableEventStatus.get_notable_status_by_label(label, session_key) is None
            
        
    @time_function_call
    def save(self, namespace=None, session_key=None, owner=None):
        """
        Saves the notable event status. If an ID is set, then the existing status will be updated. Otherwise, a new one will be created.
        """
        
        # Get the owner and namespace
        if namespace is None:
            namespace = NotableEventStatus.DEFAULT_NAMESPACE
            
        if owner is None:
            owner = NotableEventStatus.DEFAULT_OWNER
        
        # Try to get the session key if not provided
        session_key = NotableEventStatus.__get_session_key__(session_key)
        
        # Do not allow users to set the default status as disabled
        if self.is_default and not self.enabled:
            raise Exception("You cannot create a status that is both default and disabled")
        
        # If the ID is not set, create a new entry
        if self.id is None:
            
            # Unset the default status of the current status if this one must be the default instead
            if self.is_default:
                NotableEventStatus.unset_current_default( session_key=session_key )
            
            # Get the default entity
            notable_status = en.getEntity(NotableEventStatus.REVIEW_STATUSES_REST_URL, '_new', namespace=namespace, sessionKey=session_key)
            
            # Update the entity
            notable_status = self.__populate_entity__(notable_status)
                
            # Save the entity
            en.setEntity(notable_status, sessionKey=session_key)
            
            return True
        
        # Otherwise, edit the existing entity
        else:
            
            # Get the existing entity
            notable_status = en.getEntity(NotableEventStatus.REVIEW_STATUSES_REST_URL, self.id, namespace=namespace, owner=owner, sessionKey=session_key)
            
            # Unset the default status of the current status was not already the default
            if self.is_default and not NotableEventStatus.get_boolean(notable_status['default']):
                NotableEventStatus.unset_current_default( session_key=session_key )
            
            # Update the entity
            notable_status = self.__populate_entity__(notable_status, session_key=session_key)
            
            # Save the entity
            en.setEntity(notable_status, sessionKey=session_key)
            
            return True
        
    def __populate_entity__(self, entity, namespace=None, owner=None, session_key=None):
        
        # Set the namespace
        if entity.namespace is None and namespace is None:
            entity.namespace = NotableEventStatus.DEFAULT_NAMESPACE
        elif namespace is not None:
            entity.namespace = namespace
        else:
            entity.namespace = NotableEventStatus.DEFAULT_NAMESPACE
        
        # Set the owner
        if entity.owner is None and owner is None:
            entity.owner = NotableEventStatus.DEFAULT_OWNER
        elif owner is not None:
            entity.owner = owner
        else:
            entity.owner = NotableEventStatus.DEFAULT_OWNER
        
        if self.id is None: # Set a name so that Splunk does not complain, this will be overwritten by the REST handler though
            self.id = str( NotableEventStatus.getUID( session_key=session_key ) )
            entity["name"] = self.id
            entity["hidden"] = False
          
        # Do not set the default status as enabled by default per SOLNESS-1390
        # entity["selected"] = self.is_default
        entity["default"] = self.is_default
        entity["description"] = self.description
        entity["disabled"] = not self.enabled
        entity["end"] = self.end
        entity["label"] = self.name
        
        return entity
        
    @staticmethod
    @time_function_call
    def getUID(reviewstatuses=None, session_key=None):
        """
        Returns a unique identifier to be used as a stanza name
        """
      
        # Get the review statuses if not provided
        if reviewstatuses is None:
            reviewstatuses = en.getEntities(NotableEventStatus.REVIEW_STATUSES_REST_URL, namespace = NotableEventStatus.DEFAULT_NAMESPACE, owner = NotableEventStatus.DEFAULT_OWNER, sessionKey = session_key, count=-1)
          
        # This will be the new UID
        uid = 0
      
        # Build the list of integers
        for reviewstatus in reviewstatuses:
            try:
                
                # Get the stanza as an integer
                statusInt = int(reviewstatus)
                
                # If this is higher than the existing maximum then set this as the highest UID
                if statusInt > uid:
                    uid = statusInt
                  
            except:
                # The status is not an integer so skip it
                pass
      
        return (uid + 1) 
        
    @staticmethod
    def enable(id, session_key=None):
        """
        Enable the given status.
        """
        
        return NotableEventStatus.set_status(id, True, session_key)
    
    @staticmethod
    def disable(id, session_key=None):
        """
        Disable the given status.
        """
        
        return NotableEventStatus.set_status(id, False, session_key)
    
    @staticmethod
    def set_default(id, session_key=None):
        """
        Set the status identified by the given ID to the default
        """
        
        # Unset the current existing default status
        NotableEventStatus.unset_current_default( session_key=session_key )
        
        # Set the new status
        return NotableEventStatus.set_default_status( id, True, session_key)
    
    @staticmethod
    @time_function_call
    def unset_current_default(session_key=None):
        """
        Unsets the default status flag on all current default statuses.
        """
        
        # Get the existing default status
        default_statuses = NotableEventStatus.get_default_statuses( session_key=session_key )
        
        # Un set the current status
        for status in default_statuses:
            status.is_default = False
            status.save( session_key=session_key )
    
    @staticmethod
    def unset_default(id, session_key=None):
        """
        Set the status identified by the given ID such that it is not set as the default.
        """
        
        return NotableEventStatus.set_default_status( id, False, session_key)
    
    @staticmethod
    @time_function_call
    def set_default_status(id, default, session_key=None):
        """
        Toggle the status field for the given ID.
        """
        
        # Try to get the session key if not provided
        session_key = NotableEventStatus.__get_session_key__(session_key)
        
        # Get the appropriate entity
        entity = en.getEntity(NotableEventStatus.REVIEW_STATUSES_REST_URL, id, namespace = NotableEventStatus.DEFAULT_NAMESPACE, owner = NotableEventStatus.DEFAULT_OWNER, sessionKey = session_key)
        
        # Disable/enable the search
        entity['default'] = default
        # Do not set the default status as enabled by default per SOLNESS-1390
        # entity['selected'] = default
        en.setEntity(entity, sessionKey = session_key)
        
        return True
    
    @staticmethod
    def get_default_status(session_key=None):
        """
        Get the default status.
        """
        
        # Get all the statuses so that the default can be found
        statuses = NotableEventStatus.get_notable_statuses()
        
        # Find the default status
        for status in statuses:
            if status.is_default:
                return status
        
        # No default status found
        return None
    
    @staticmethod
    def get_default_statuses(session_key=None):
        """
        Get the statuses with the default parameter set.
        """
        
        # Get all the statuses so that the default can be found
        statuses = NotableEventStatus.get_notable_statuses()
        default_statuses = []
        
        # Find the default status
        for status in statuses:
            if status.is_default:
                default_statuses.append(status)
        
        # Return the list of the default statuses
        return default_statuses
    
    @staticmethod
    def get_end_statuses(session_key=None):
        """
        Get the statuses with the end parameter set.
        """
        
        # Get all the statuses so that the default can be found
        statuses = NotableEventStatus.get_notable_statuses()
        end_statuses = []
        
        # Find the default status
        for status in statuses:
            if status.end:
                end_statuses.append(status)
        
        # Return the list of the end statuses
        return end_statuses
    
    @staticmethod
    @time_function_call
    def set_status(id, enable, session_key=None):
        """
        Enables/disable the given status. Returns true if the status was successfully disabled.
        """
        
        # Try to get the session key if not provided
        session_key = NotableEventStatus.__get_session_key__(session_key)
        
        # Get the appropriate entity
        entity = en.getEntity(NotableEventStatus.REVIEW_STATUSES_REST_URL, id, namespace = NotableEventStatus.DEFAULT_NAMESPACE, owner = NotableEventStatus.DEFAULT_OWNER, sessionKey = session_key)
        
        # Disable/enable the search
        entity['disabled'] = not enable
        en.setEntity(entity, sessionKey = session_key)
        
        # Refresh Splunk
        ## Commenting as the handleCreate/handleEdit w/in reviewstatuses rest handler should perform this refresh
        #StatusTransition.__refresh_capabilities__(session_key)
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
    def is_enabled(status_dict):
        """
        Determine if the given status is enabled
        """
        
        # Get the disabled flag
        if 'disabled' in status_dict:
            return not NotableEventStatus.get_boolean(status_dict['disabled'], False)
        else:
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
    def __create_from_dict__( status_id, notable_status, session_key=None):
        
        session_key = NotableEventStatus.__get_session_key__(session_key, False)
        
        if session_key is not None:
            transitions = StatusTransition.get_transition_map(session_key, id=status_id)
        else:
            transitions = None
        
        return NotableEventStatus(status_id, notable_status['label'], notable_status['description'], not NotableEventStatus.get_boolean(notable_status['disabled']), NotableEventStatus.get_boolean(notable_status['default']), transitions, hidden=NotableEventStatus.get_boolean(notable_status['hidden']), selected=NotableEventStatus.get_boolean(notable_status['selected']), end=NotableEventStatus.get_boolean(notable_status['end']))
        
    @staticmethod
    def get_notable_status_by_label(label, session_key=None):
        """
        Gets the notable status with the given label.
        """
        
        statuses = NotableEventStatus.get_notable_statuses(session_key=session_key)
        
        for status in statuses:
            
            if status.name == label:
                return status
            
        return None
        
    @staticmethod
    @time_function_call
    def get_notable_status(id, session_key=None):
        """
        Get the given notable event status.
        """
        
        notable_status = en.getEntity(NotableEventStatus.REVIEW_STATUSES_REST_URL, id, namespace = NotableEventStatus.DEFAULT_NAMESPACE, owner = NotableEventStatus.DEFAULT_OWNER, sessionKey = session_key)
        
        return NotableEventStatus.__create_from_dict__(id, notable_status, session_key)
        
    @staticmethod
    @time_function_call
    def get_notable_statuses(enabled_statuses_only=False, session_key=None):
        """
        Returns a list of the notable statuses.
        """
        
        statuses_list = en.getEntities(NotableEventStatus.REVIEW_STATUSES_REST_URL, namespace = NotableEventStatus.DEFAULT_NAMESPACE, owner = NotableEventStatus.DEFAULT_OWNER, sessionKey = session_key, count=-1)
        
        notable_statuses = []
        
        # Process each search
        for status_id in statuses_list:
            
            notable_status = statuses_list[status_id]
            
            # Create the notable status instance
            ns = NotableEventStatus.__create_from_dict__(status_id, notable_status)
            
            # Add the search to the list
            if enabled_statuses_only == False or ns.enabled:
                notable_statuses.append( ns )
                
        # Return the list of searches
        return notable_statuses
       
    @staticmethod
    @time_function_call
    def getCapabilities4User(user=None, session_key=None):
        roles = []
        capabilities = []
        
        ## Get user info              
        if user is not None:
            #logger.info('Retrieving role(s) for current user: %s' % (user))
            userDict = en.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
        
            for stanza, settings in userDict.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            #logger.info('Successfully retrieved role(s) for user: %s' % (user))
                            roles = val
             
        ## Get capabilities
        for role in roles:
            #logger.info('Retrieving capabilities for current user: %s' % (user))
            roleDict = en.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
            
            for stanza, settings in roleDict.items():
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            #logger.info('Successfully retrieved %s for user: %s' % (key, user))
                            capabilities.extend(val)
            
        return capabilities