'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''

'''
This page provides an editor for creating and editing suppression rules. Below are the arguments accepted:

  wz                     : Wizard mode, if this argument is provided then the ability to edit to search will be disabled (use when you are providing the contents of search on behalf of the user)
  description            : The description field
  search                 : The search that will make up the eventtype
  id                     : The id of an existing search to edit
  search_description     : A description of what the provided search string will match. This is listed under the search.
  start_time             : The time that ought to be used for the start time. If not provided, then the current time will be used

'''

import logging
import controllers.module as module
import cherrypy
from datetime import datetime
import time
import traceback
import re
import splunk.bundle as bundle
import splunk.admin as admin
import splunk.entity as en

import json

# Import the code for editing notable statuses
import sys
import os
sys.path.append( os.path.join("..", "..", "..", "bin") )

from notable_event_suppression import NotableEventSuppression
from shortcuts import Invocation

logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.modules.NotableEventSuppressionEditor')

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
    
def escape_message( msg ):
    return msg.replace("'", "").replace('"', "")
    
def none_to_default( txt, default="" ):
    if txt is None:
        return default
    else:
        return txt
    
def output_if_true( content_true, boolean, content_false="" ):
    if boolean:
        return content_true
    else:
        return content_false
    
class SuppressionDateInvalid(Exception):
    pass

class SuppressionStartDateInvalid(SuppressionDateInvalid):
    pass

class SuppressionEndDateInvalid(SuppressionDateInvalid):
    pass
    
class NotableEventSuppressionEditor(module.ModuleHandler):
    
    def has_end_time(self, search):
        endRE = re.compile('_time\s*<[=]?\s*(\d+(?:\.\d+)?)')
        
        if len(endRE.findall(search)) > 0:
            return True
        else:
            return False
        
    def has_start_time(self, search):
        startRE = re.compile('_time\s*>[=]?\s*(\d+(?:\.\d+)?)')
        
        if len(startRE.findall(search)) > 0:
            return True
        else:
            return False
    
    def add_end_time(self, search, expiration_date):
        
        # Add the expiration if defined
        if expiration_date is not None and len(expiration_date.strip()) > 0:
            
            try:
                # Parse the expiration date
                dt = datetime.strptime(expiration_date, "%m/%d/%Y")
            except ValueError as e:
                raise SuppressionEndDateInvalid("The expiration date is invalid: " + str(e))
            
            # Convert the datetime to an epoch
            dt_epoch = int(time.mktime(dt.timetuple()))
            
            if dt_epoch < int(time.time()):
                raise SuppressionEndDateInvalid("The expiration date must be later than today")
    
            # Add the expiration date to the search
            search = search + (" _time<%s" % ( str(dt_epoch)))
            
        return search
    
    def add_start_time(self, search, start_time=None):
        
        from splunk.util import parseISO, dt2epoch
        
        # Don't bother adding a start time if one already exists
        if self.has_start_time(search):
            return search
        
        # Add the start time
        try:
            if start_time is not None:
                t = int(dt2epoch(parseISO(start_time)))
            else:
                t = str(int(time.time()))
        except Exception as e:
            raise SuppressionStartDateInvalid("The start date is invalid: " + str(e))
        
        return search + (" _time>=%s" % (t))
    
    def generateResults(self, search, description, name=None, id=None, enabled=True, expiration_date=None, user=None, namespace=None, owner=None, start_time=None, **args):
        response = {}
        
        ## Get invocation_id
        invocation_id = Invocation.getInvocationID()
        
        if user is None:
            user = ''
        
        if id is None or len(id.strip()) == 0:
            is_new = True
            action = 'create'
            
            id = NotableEventSuppression.SUPPRESSION_START + name
            
        else:
            is_new = False
            action = 'edit'
                
        try:
            status = 'success'
            
            # Save the entry
            if is_new:
                
                # Add the expiration date if provided
                resulting_search = self.add_end_time(search, expiration_date)
                
                # Add the the current date
                resulting_search = self.add_start_time(resulting_search, start_time)
                
                # Raise an error if the user attempted to define an expiration time even though one already exists in the search
                if self.has_end_time(search) and expiration_date is not None and len(expiration_date.strip()) > 0:
                    response["message"] = "An expiration date is already defined in the search; clear the expiration date field or remove the expiration date from the search syntax"
                    response["success"] = False
                    
                    return json.dumps(response)
                
                # If creating a new instance, then create a new one
                suppression = NotableEventSuppression(id, enabled, description, resulting_search)
                
                suppression.save(new=True)
                
                signature = 'Notable event suppression successfully created'    
                
            else:
                # Load the existing entry
                suppression = NotableEventSuppression.get_notable_suppression(id=id)
                
                suppression.search = search
                suppression.description = description
                
                suppression.save()
                
                signature = 'Notable event suppression successfully saved'
            
            logger.info('invocation_id=%s; suppression=%s; action=%s; status=%s; signature=%s; user=%s;' % (invocation_id, id, action, status, signature, user)) 
            response["message"] = signature #signature.replace('"', ' ').replace("'", ' ')[0:100]
            response["success"] = True
        
        except SuppressionDateInvalid, e:
            response["success"] = False
            response["message"] = str(e)
                
            return json.dumps(response)
        
        except Exception, e :
            
            status = 'failure'
            signature = "Unable to save the event suppression"
            
            logger.error('invocation_id=%s; suppression=%s; action=%s; status=%s; signature=%s; user=%s;' % (invocation_id, id, action, status, signature, user)) 
            
            # Return a message noting that the operation failed because the user does not have permission
            if str(e).find("AuthorizationFailed") >= 0:
                
                response["success"] = False
                response["message"] = "You do not have permission to edit notable event suppressions; make sure you have permission to create and edit eventtypes"
                
                return json.dumps(response)
            
            # Return a message noting that the operation failed because the search was rejected by Splunk
            if str(e).find("Error while parsing eventtype search") >= 0:
                
                response["success"] = False
                response["message"] = "The provided search is not valid"
                
                return json.dumps(response)
            
            # Return the default error message
            response["message"] = signature
            #tb = traceback.format_exc()
            #response["trace"] = tb # Don't include the traceback since the editor may not show the error message if it is excessively long
            response["success"] = False

        return json.dumps(response)