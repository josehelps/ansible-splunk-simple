import cherrypy
import sys
import os
import splunk
import traceback
import json
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route


import logging
import splunk, splunk.search, splunk.util
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# Setup the logger
def setup_logger():
    """
    Setup a logger for the REST handler.
    """
    
    logger = logging.getLogger('splunk.SAThreatIntelligence.NotableEventsController')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'notable_events_controller.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
   
    logger.addHandler(file_handler)
   
    return logger

logger = setup_logger()

class NotableEvents(controllers.BaseController):
    '''Notable event update Controller'''

    @route('/:update_status=update_status')
    @expose_page(must_login=True, methods=['GET', 'POST'])
    def update_status(self, **kwargs):
        
        # Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        # Get the ruleUIDs
        args = kwargs
        
        # jQuery may add "[]" to the arguments when an array of similar argument names are provided, handle this case
        if 'ruleUIDs[]' in kwargs:
            args['ruleUIDs'] = kwargs['ruleUIDs[]']
            del args['ruleUIDs[]']
            
        # Otherwise, ruleUIDs should just be "ruleUIDs"
        elif 'ruleUIDs' in kwargs:
            args['ruleUIDs'] = kwargs['ruleUIDs']
        
        # Default to JSON since that is what Javascript usually wants
        if 'output_mode' not in args:
            args['output_mode'] = 'json'
        
        try:
            serverResponse, serverContent = splunk.rest.simpleRequest('/services/notable_update', sessionKey=session_key, postargs=args)
        except splunk.AuthenticationFailed:
            return None
        except Exception as e:
            logger.exception("Attempt to update notable events failed")
            
            tb = traceback.format_exc()
            
            serverContent = json.dumps({
                                        'message': str(e),
                                        'success': False,
                                        'traceback:': tb })
        
        cherrypy.response.headers['Content-Type'] = 'text/json'
        return serverContent
        