import logging
import logging.handlers
import os
import splunk.auth as auth
import splunk.rest as rest
import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('governance_makeCSV')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'governance_makeCSV.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()


if __name__ == '__main__':
  logger.info('Starting governance_makeCSV')
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
    
  GOVERNANCE_REST_PATH = 'alerts/governance/_reload'

  logger.info('Making handleReload call to %s to makeCSV' % (GOVERNANCE_REST_PATH))
  
  ## Hit reload @ alerts/governance
  requestData = rest.simpleRequest(GOVERNANCE_REST_PATH, sessionKey=sessionKey)
  
  logger.info('governance_makeCSV completed successfully')