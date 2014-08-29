'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import controllers.module as module
import cherrypy
import json
import os
import csv
from time import strftime, gmtime, strptime
import time
import calendar

import traceback,sys
import splunk.entity as entity
import splunk, splunk.search, splunk.util
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

import portalocker


class LogReviewPopup(module.ModuleHandler):

    DEFAULT_NAMESPACE = 'SA-ThreatIntelligence'
    DEFAULT_OWNER = 'nobody'
    LOG_REVIEW_REST_URL = '/alerts/log_review/'

    def __init__(self, *args):
        module.ModuleHandler.__init__(self, *args)
    
    @staticmethod
    def __get_session_key__(session_key=None):
        """
        Get a session key.
        
        Arguments:
        session_key -- The session key to be used if it is not none
        """
        
        # Try to get the session key if not provided
        # Also can be obtained through: cherrypy.session['sessionKey']
        if session_key is None:
            session_key, sessionSource = splunk.getSessionKey(return_source=True)
        
        # Return the session key
        return session_key
    
    @staticmethod
    def isUrgencyOverrideAllowed():
        """
        Determines if urgency overrides are allowed.
        """
        
        notable_en = entity.getEntity(LogReviewPopup.LOG_REVIEW_REST_URL, 'notable_editing', namespace = LogReviewPopup.DEFAULT_NAMESPACE, owner = LogReviewPopup.DEFAULT_OWNER, count=-1)
        
        if 'allow_urgency_override' in notable_en:
            return LogReviewPopup.get_boolean( notable_en['allow_urgency_override'] )
        else:
            return True
    
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
    
    @staticmethod
    def commentLengthRequired(session_key=None):
        """
        Returns the length of the comment required.
        
        Arguments:
        session_key -- The session key to be used
        """
        
        # Get the session key
        session_key = LogReviewPopup.__get_session_key__(session_key)
        
        # Get the configuration from the log_review endpoint
        comment_en = entity.getEntity(LogReviewPopup.LOG_REVIEW_REST_URL, 'comment', namespace = LogReviewPopup.DEFAULT_NAMESPACE, owner = LogReviewPopup.DEFAULT_OWNER, sessionKey = session_key, count=-1)

        # Determine if a comment is required
        is_required = LogReviewPopup.get_boolean( comment_en['is_required'] )
        
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

    
    def generateResults(self, host_app, client_app, status, comment, newOwner=None, urgency=None, ruleUIDs=None, searchID=None, **args):
        
        response = {
                  "success": False, 
                  "message": _("The module code has been deprecated in favor of the notable_events controller (see web.conf)")
                }
                
        return json.dumps(response)
        
