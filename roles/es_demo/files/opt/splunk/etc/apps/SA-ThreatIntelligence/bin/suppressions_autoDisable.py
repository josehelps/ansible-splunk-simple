'''
Copyright (C) 2005 - 2011 Splunk Inc. All Rights Reserved.
'''
import logging
import logging.handlers
import os
import splunk.auth as auth
import splunk.entity as en
import sys

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from notable_event_suppression import NotableEventSuppression

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('notable_event_suppression_autoDisable')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'notable_event_suppression_autoDisable.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()



if __name__ == '__main__':

    logger.info('Starting notable_event_suppression_autoDisable')
    debug = False
  
    ## Get session key sent from splunkd
    sessionKey = sys.stdin.readline().strip()
          
    if len(sessionKey) == 0:
        sys.stderr.write("Did not receive a session key from splunkd. " +
                "Please enable passAuth in inputs.conf for this " +
                "script\n")
        exit(2)
    
    elif sessionKey == 'debug':
        debug = True
        sessionKey = auth.getSessionKey('admin', 'changeme')
    
    
    expired_count, enabled_count = NotableEventSuppression.disable_expired_suppressions(session_key=sessionKey)
                    
    logger.info("%s expired suppressions detected; %s were enabled (now disabled)" % (expired_count, enabled_count))
    