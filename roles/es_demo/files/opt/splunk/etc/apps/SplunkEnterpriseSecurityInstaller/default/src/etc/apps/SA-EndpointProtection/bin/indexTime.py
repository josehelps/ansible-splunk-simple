'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''

import httplib2
import logging
import logging.handlers
import os
import splunk.auth as auth
import splunk.util as util
import sys
import time	

from splunk import search
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('indexTime')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'indexTime.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()

if __name__ == '__main__':

    logger.info('Starting indexTime')
    
    debug = False
    DEFAULT_NAMESPACE = 'SA-EndpointProtection'
    DEFAULT_OWNER = 'nobody'
    DEFAULT_EARLIEST = '-72h'
    DEFAULT_LATEST = '+72h'
    DEFAULT_INDEX = 'endpoint_summary'
    DEFAULT_SEARCH_NAME = 'Endpoint - Index Time Delta 2 - Summary Gen'
    
    ## Override Defaults w/ opts below
    if len(sys.argv) > 1:
        for a in sys.argv:
            if a.startswith('namespace='):
                where = a.find('=')
                DEFAULT_NAMESPACE = a[where+1:len(a)]
            elif a.startswith('owner='):
                where = a.find('=')
                DEFAULT_OWNER = a[where+1:len(a)]
            elif a.startswith('earliest='):
                where = a.find('=')
                DEFAULT_EARLIEST = a[where+1:len(a)]
                ## Todo: Add timeParser validation
            elif a.startswith('latest='):
                where = a.find('=')
                DEFAULT_LATEST = a[where+1:len(a)]
                ## Todo: Add timeParser validation
            elif a.startswith('index='):
                where = a.find('=')
                DEFAULT_INDEX = a[where+1:len(a)]
  
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
        
    logger.info('Building base search')
    baseSearch = 'earliest=' + DEFAULT_EARLIEST + ' latest=' + DEFAULT_LATEST + ' | eval timeDiff=_time-_indextime | stats min(timeDiff) as min_timeDiff,max(timeDiff) as max_timeDiff,sum(timeDiff) as sum_timeDiff,count by host,sourcetype | eval _time=now()'
    logger.info('Base search successfully built: %s' % (baseSearch))
    
    logger.info('Building collection search')
    summaryIndex = 'collect index=' + DEFAULT_INDEX + ' marker="search_name=\\"' + DEFAULT_SEARCH_NAME + '\\""'
    logger.info('Collection search successfully built: %s' % (summaryIndex))
    
    ## get the current date and time
    nowTime = util.mktimegm(time.gmtime())

    logger.info('Building final search')
    query = 'search _indextime>' + str(nowTime-86400) + ' ' + baseSearch + ' | ' + summaryIndex
    logger.info('Final search successfully build %s' %(query))	
    
    logger.info('Dispatching job')
    
    try:
        job = search.dispatch(query, hostPath=None, sessionKey=sessionKey, namespace=DEFAULT_NAMESPACE, owner=DEFAULT_OWNER)
    
    except Exception as e:
        logger.critical(e)
        exit(2)
        
    logger.info("Successfully dispatched job %s" % (job.id))