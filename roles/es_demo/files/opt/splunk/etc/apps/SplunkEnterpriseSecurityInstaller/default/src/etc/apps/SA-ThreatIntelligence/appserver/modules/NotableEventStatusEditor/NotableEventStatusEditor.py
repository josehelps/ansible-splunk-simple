import logging
import controllers.module as module
import cherrypy

import splunk.bundle as bundle
import splunk.admin as admin
import splunk.entity as en

import json

# Import the code for editing notable statuses
import sys
import os
sys.path.append( os.path.join("..", "..", "..", "bin") )

from notable_event_status import NotableEventStatus, StatusTransition, parse_transition_str, create_transition_capability_str

logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.modules.NotableEventStatusEditor')
   
TRANSITION_ENABLED = True
TRANSITION_DISABLED = False
TRANSITION_IMPORTED = None
    
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
    
def is_role_enabled(transitions, status, role):
    
    status = get_role_status(transitions, status, role)
    
    if status == TRANSITION_ENABLED:
        return True
    elif status == TRANSITION_IMPORTED:
        return False
    else:
        return False
    
def get_role_status(transitions, status, role):
    
    if transitions is None:
        return TRANSITION_DISABLED
    
    # Find the appropriate transition if found
    for t in transitions:
        if status.id == t.to_status:
            
            # See if the role is included
            if role in t.roles:
                return TRANSITION_ENABLED
            elif role in t.imported_roles:
                return TRANSITION_IMPORTED
            else:
                return TRANSITION_DISABLED
    
    # If no transition was explicitly set
    return TRANSITION_DISABLED

def escape_message( msg ):
    return msg.replace("'", "").replace('"', "")
    
def none_to_blank( txt ):
    if txt is None:
        return ""
    else:
        return txt
    
def output_if_true( content_true, boolean, content_false="" ):
    if boolean:
        return content_true
    else:
        return content_false
    
def get_transition_label( id ):
    for s in notable_statuses:
        if s.id == id:
            return s.name
    
    return id

def get_transition_roles( notable_status ):
    return NotableEventStatus.get_allowed_roles( notable_status.id, transition_map, roles)

def get_option_name(status, role):
    return status.id + "_for_role_" + role

def get_transitions_enabled_list(orig_list, enabled_list):
    
    new_list = {}
    
    for o in orig_list:
        new_list[o] = o in enabled_list
    
    return new_list

def get_id(status):
    if status.id is None:
        return "NA"
    else:
        return status.id

class NotableEventStatusEditor(module.ModuleHandler):
    
    def performCapabilityChanges(self, resulting_capabilities_by_role, namespace):
        StatusTransition.update_transitions( resulting_capabilities_by_role, namespace )

    
    """
    Accepts the calls from the form and updates or creates the status entry accordingly.
    """
    
    def generateResults(self, name=None, description=None, id=None, enabled=None, end=None, is_default=False, namespace=None, owner=None, **args):
        response = {}

        
        #                                                                           
        #   We need to do some complicated processing to figure out how to change the roles. The problem with web forms is that
        #   they do not provide information about which items are unchecked. That is, when an item is unchecked it is just not 
        #   returned as opposed to be being returned with a value of false. To deal with this, the form includes a list of all
        #   of the items that were originally present, and we must deduce which ones were unchecked.
        #
        #   Additionally, we need to aggregate the items by role since the capabilities are set on a per-role basis.
        #
        #   Below is a diagram illustrating how to the roles are to be processed:
        #                                                                           
        #   *****************                                                        
        #   * Original      *                                                        
        #   * transitions   *                                                        
        #   * (before edits)**                                                       
        #   *               * **    ****************          ****************   
        #   *****************   **  * Complete     *          *              *
        #                        **** transition   ************ Changes per  *************  Apply changes to each role
        #                        **** state set    *          * role         *                                 
        #   *****************   **  *              *          *              *                                 
        #   * New           * **    ****************          ****************                                 
        #   * transitions   **                                                       
        #   * (after edits) *                                                        
        #   *               *                                                        
        #   *****************                                                        
        #                                                                           

        # The following variable will be used to determine if we are past the point of saving the notable event status and are working on transitions
        # This is necessary so that we produce the correct error message if the user does not have the correct capability 
        saved_notable = False

        try:
            
            # Set the ID to none if it is blank
            if id is None or (id is not None and len(id.strip()) == 0):
                is_new = True
                id = None
            else:
                is_new = False
            
            # Set the enabled status if it was not defined
            if enabled is None and is_default:
                
                # This sets the status to enabled if it is default since default statuses cannot be disabled
                enabled = True
                
            elif enabled is None:
                
                # Set the status to disabled by default if the user did not define it since the lack of this field likely means they want to disable it
                enabled = False
            
            if end is None or is_default:
                # Set the end status to false if the user did not define it since the lack of this field likely means they want to disable it
                end = False
            
            # Create the notable entry
            notable_status = NotableEventStatus(id, name, description, enabled, is_default, end=end)
            
            if id not in [0, "0"]: # Don't let someone edit the unassigned status since it is static
                
                if is_new and not NotableEventStatus.is_label_unique(name):
                    response["message"] = "Notable event status label is not unique. Please change the label to be unique."
                    response["success"] = False
                    
                    return json.dumps(response)
                else:
                    notable_status.save()
            
            saved_notable = True # Note that we are now working on the transitions now since we saved the notable event status instance
            
            if notable_status.id is not None:
                # Get the original list of transitions
                in_scope_transitions = []
                
                if 'transitions_orig' in args:
                    
                    for t in args['transitions_orig']:
                        in_scope_transitions.append( t.replace( "_NA_", "_" + notable_status.id + "_") )
                        
                else:
                    # The list of in scope transitions was not provided, so do not continue
                    return
                
                # Get the enabled transition lists
                enabled_transitions = []
                
                if 'transitions_new' in args:
                    
                    for t in args['transitions_new']:
                        if t.startswith("imported_") == False: # Don't bother with the imported roles
                            enabled_transitions.append( t.replace( "_NA_", "_" + notable_status.id + "_") )
                
                # Get the necessary changes
                resulting_capabilities = get_transitions_enabled_list(in_scope_transitions, enabled_transitions)
                
                # Aggregate the list of transitions by role (so we can call the endpoint accordingly)
                resulting_capabilities_by_role = {}
                
                for r in resulting_capabilities.keys():
                    
                    # Parse the transition string and create the capability name
                    status_from, status_to, role = parse_transition_str(r)
                    capability = create_transition_capability_str(status_from, status_to)
                    
                    # Determine if the role already exists and edit it if it does...
                    if role in resulting_capabilities_by_role:
                        resulting_capabilities_by_role[role][capability] = resulting_capabilities[r]
                        
                    # ... otherwise, create a new entry
                    else:
                        resulting_capabilities_by_role[role] = {capability : resulting_capabilities[r] }
                    
                # Take the list of roles and edit the roles accordingly
                self.performCapabilityChanges(resulting_capabilities_by_role, namespace)
            
            # Return a success message
            if is_new:
                response["message"] = "Notable event status successfully created"
            else:
                response["message"] = "Notable event status successfully saved"
                
            response["success"] = True

        except Exception, e :
            
            # Return a message noting that operation failed because the user does not have permission
            if str(e).find("AuthorizationFailed") >= 0:
                
                response["success"] = False
                
                if saved_notable:
                    response["message"] = "You do not have permission to create notable event status transitions"
                else:
                    response["message"] = "You do not have permission to create notable event statuses"
                
                return json.dumps(response)
            
            # This will be the error message returned
            result = "Error: "
            
            # Let's get the stacktrace so that debugging is easier
            import traceback,sys
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
            
            # Log the error
            logger.error("Error occurred while saving the notable event status\n" + result)
            
            # Create the resulting message
            response["success"] = False
            response["message"] = "Error occurred while saving the notable event status"
            response["details"] = result.replace("'", '"')[0:400]

        return json.dumps(response)
    