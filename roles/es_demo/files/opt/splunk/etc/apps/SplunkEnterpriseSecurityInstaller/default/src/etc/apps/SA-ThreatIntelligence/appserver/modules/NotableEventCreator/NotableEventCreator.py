'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''

import logging
import controllers.module as module
import cherrypy
import splunk.rest as rest
import json
import traceback
import splunk
import splunk.auth as auth
import splunk.util as util

from splunk.models.field import Field
from splunk.models.base import SplunkAppObjModel

logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.modules.NotableEventCreator')


class ServerInfo(SplunkAppObjModel):
    resource = 'server/info'
    
    server_name = Field(api_name="serverName")


class NotableEventCreator(module.ModuleHandler):

    # Below is a dictionary that maps special field names to the one that should be used in the summary indexed event. Note: a value of None will prevent the field from being persisted.
    SPECIAL_FIELDS_MAP = { 
        "_cd" : "orig_cd",
        "_raw"   : "orig_raw",
        "_time" : "orig_time",
        "control" : "orig_control",
        "date_" : "orig_date",
        "default_owner" : "orig_default_owner",
        "drilldown_search" : "orig_drilldown_search",
        "drilldown_name" : "orig_drilldown_name",
        "event_id" : "orig_event_id",
        "event_hash" : "orig_event_hash",
        "eventtype" : "orig_eventtype",
        "governance" : "orig_governance",
        "host"   : "orig_host",
        "index" : "orig_index",
        "linecount" : "orig_linecount",
        "punct" : None, # Dropped this field since has been known to cause Splunk's parsing to fail, see SOLNESS-1931
        "owner" : "orig_owner",
        "rule_description" : "orig_rule_description",
        "rule_name" : "orig_rule_name",
        "rule_title" : "orig_rule_title",
        "security_domain" :"orig_security_domain",
        "source" : "orig_source",
        "sourcetype" : "orig_sourcetype",
        "splunk_server" : "orig_splunk_server",
        "status" : "orig_status",
        "tag" : "orig_tag",
        "timeendpos" : "orig_timeendpos",
        "timestartpos" : "orig_timestartpos"
    }

    def convert_special_fields(self, name):
        """
        Convert the field to one that can be persisted. This is necessary because some fields 
        (like _raw, host) are special fields that cannot be summary indexed without conflicting
        with a native Splunk field.
        
        Arguments:
        name -- field name to convert
        """
        
        # If the field is a special field, then change the name
        try:
            # Convert the old tag fields
            if name.startswith("tag::"):
                return "orig_" + name
            elif name.startswith("date_"):
                return None
            else:
                return self.SPECIAL_FIELDS_MAP[name]
        except KeyError:
            # The field was not found. This indicates that it does not need to be converted so return the original.
            return name

    def getMetaFields(self):
        """
        Get the special fields that indicates the index, source, sourcetype and host as a dictionary.
        """
        
        # Get a session key
        sessionKey, sessionSource = splunk.getSessionKey(return_source=True)
        
        # Prepare the fields necessary for the indexed event
        index         = "notable"
        source        = "Manual Notable Event - Rule"
        sourcetype    = "stash_new"
        host          = ServerInfo.all(sessionKey=sessionKey)[0].server_name
        
        
        args = {'index'      : index,
                'source'     : source,
                'sourcetype' : sourcetype,
                'host'		 : host,
                }
        
        return args
    
    def lower_case(self, string_value):
        """
        Convert the given string value to lower case (but don't throw an exception if it is None).
        
        Arguments:
        string_value -- The string to lower
        """
        
        if string_value is not None:
            return string_value.lower()
        else:
            return None

    def getFields(self, title, body, security_domain, urgency, owner, status, drilldown_name, drilldown_url, other_fields):
        """
        Get the fields of the event. The names will be escaped if necessary. Some fields (like punct)
        will be dropped entirely.
        
        Arguments:
        title -- The title of the event
        body -- The body of the event
        security_domain -- The security domain of the event
        urgency -- The urgency of the event
        owner -- The owner of the event
        status -- The default status of the event
        other_fields -- Miscellaneous other fields
        drilldown_name -- The name of the drilldown field
        drilldown_url -- The url of the drilldown field
        """
        
        fields ={'rule_description': body,
                 'rule_title'      : title,
                 'security_domain' : self.lower_case(security_domain), # Make sure to lower the domain (SOLNESS-3240)
                 'owner'           : owner,
                 'status'          : status,
                 'urgency'         : urgency
                 }
        
        if drilldown_url is not None:
            fields['drilldown_url'] = drilldown_url
            
        if drilldown_name is not None:
            fields['drilldown_name'] = drilldown_name
            
        # Pass through the fields
        for k, v in other_fields.items():
            
            # Convert the name if necessary
            new_name = self.convert_special_fields(k)
            
            ## Convert orig_time to epoch
            if new_name == 'orig_time':
            	try:
            		v = str(util.dt2epoch(util.parseISO(v, strict=True)))
            	
            	except:
            		new_name = None

            # If the name is none, then it ought to be excluded            	
            if new_name is not None:
                fields[new_name] = v            
            
        return fields

    def makeContentBody(self, fields):
        """
        Make a string for the content body.
        
        Arguments:
        fields -- The fields to make the content for
        """
        
        # Make the content body field
        content_body = '\n==##~~##~~  1E8N3D4E6V5E7N2T9 ~~##~~##==\n'
            
        for k, v in fields.items():
            content_body = content_body + k + "=\"" + v + "\", "
            
        return content_body

    def generateResults(self, **args):
        
        # Prepare a response
        response = {}
        
        # Remove fields that are set in the form so that it doesn't get double counted
        title           = args.pop('title', None)
        body            = args.pop('body', None)
        security_domain = args.pop('security_domain', 'threat')
        urgency         = args.pop('urgency', None)
        owner           = args.pop('owner', None)
        status          = args.pop('status', None)
        drilldown_name  = args.pop('drilldown_name', None)
        drilldown_url   = args.pop('drilldown_url', None)
        
        # Verify the provided fields
        if title is None or len(title) == 0:
            response["message"] = "The title of the notable event was not provided (cannot be blank)"
            response["success"] = False
            
            return json.dumps(response)
        
        if body is None or len(body) == 0:
            response["message"] = "The body of the notable event was not provided (cannot be blank)"
            response["success"] = False
            
            return json.dumps(response)
        
        # Save the event
        try:
            
            # Make the fields
            fields = self.getFields(title, body, security_domain, urgency, owner, status, drilldown_name, drilldown_url, args)
                    
            # Make the content body field
            content_body = self.makeContentBody(fields)
            
            # Alright, let's do this thing
            response, content = rest.simpleRequest("/services/receivers/simple", getargs=self.getMetaFields(), method="POST", jsonargs=content_body)
            
            if response.status == 200:
                
                user = auth.getCurrentUser()['name']
                logger.info("Notable event successfully created, user=%s" % (user))
            
                # Indicate that the action was a success
                response["message"] = "Notable event created successfully"
                response["success"] = True
            else:
                
                logger.warn("Notable event could not be created")
                
                # Indicate that the action was a failure
                response["message"] = "Notable event could not be created: " + str(content)
                response["success"] = False

        except Exception, e :
            
            tb = traceback.format_exc()
            
            response["message"] = str(e)
            response["trace"] = tb
            response["success"] = False

        # Return 
        return json.dumps(response)