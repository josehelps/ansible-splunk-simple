'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import logging
import logging.handlers
import os
import random
import splunk.Intersplunk
import splunk.entity as entity
import splunk.util as util
import sys

from time import gmtime, strftime
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

DEFAULT_NAMESPACE = 'SA-Utils'
DEFAULT_OWNER = 'nobody'

## Setup the logger
def setup_logger():
    """
    Setup a logger for the search command
    """
    
    logger = logging.getLogger('getcron')
    logger.setLevel(logging.DEBUG)
    
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'getcron.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()


def getCron4savedsearch(savedsearch, savedsearchesDict={}):
        
    if savedsearchesDict is not None:
        for stanza, settings in savedsearchesDict.items():
            if stanza == savedsearch:
                for key, val in settings.items():
                    if key == 'cron_schedule':
                        return val
    
    return None


if __name__ == '__main__':
    ## Create a unique identifier for this invocation
    nowTime = util.mktimegm(gmtime())
    salt = random.randint(0, 100000)
    invocation_id = str(nowTime) + ':' + str(salt)
    
    ## Log initialization
    logger.info('invocation_id=%s; signature=Starting getcron' % (invocation_id))
    
    namespace = None
    owner = None
    
    DEFAULT_INPUTFIELD = 'savedsearch_name'
    inputField = None
    
    DEFAULT_OUTPUTFIELD = 'cron'
    outputField = None
    
    ## Override Defaults w/ opts below
    if len(sys.argv) > 1:
        for a in sys.argv:
            if a.startswith('namespace='):
                where = a.find('=')
                namespace = a[where+1:len(a)]
            elif a.startswith('owner='):
                where = a.find('=')
                owner = a[where+1:len(a)]
            elif a.startswith('inputField='):
                where = a.find('=')
                inputField = a[where+1:len(a)]
            elif a.startswith('outputField='):
                where = a.find('=')
                outputField = a[where+1:len(a)]
    
    
    ## Get inputField
    if namespace is None:
        namespace = DEFAULT_NAMESPACE
        
    logger.info('invocation_id=%s; signature=namespace retrieved; namespace=%s' % (invocation_id, namespace))
    
    ## Get owner   
    if owner is None:
        owner = DEFAULT_OWNER
    
    logger.info('invocation_id=%s; signature=owner retrieved; owner=%s' % (invocation_id, owner))

    ## Get inputField
    if inputField is None:
        inputField = DEFAULT_INPUTFIELD
        
    logger.info('invocation_id=%s; signature=inputField retrieved; inputField=%s' % (invocation_id, inputField))
    
    ## Get outputField    
    if outputField is None:
        outputField = DEFAULT_OUTPUTFIELD
    
    logger.info('invocation_id=%s; signature=outputField retrieved; outputField=%s' % (invocation_id, outputField))

    ## Retrieve results and settings
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    ## Get session key
    sessionKey = settings.get('sessionKey', None)
        
    ## Verify > 0 results
    if len(results) > 0:
        requiredFields = [inputField]
        
        ## Test first item to verify all required fields are present
        for key in results[0]:
            ## Remove the field from the list of required fields
            try:
                requiredFields.remove(key)
            
            except ValueError:
                pass # Field not available, probably because it is not required
        
        ## Test length of required fields
        if len(requiredFields) > 0:
            logger.warn('invocation_id=%s; signature=inputField unavailable in result set; inputField=%s' % (invocation_id, inputField))
        
        else:
            ## Get saved searches dict
            savedsearchesDict = entity.getEntities('saved/searches', count=-1, sessionKey=sessionKey)
            
            ## Iterate each result
            for x in range(0,len(results)):
                
                ## Iterate each key, val in result
                for key, val in results[x].items():
                    results[x][outputField] = ''
                    
                    if val is None:
                        val = ''
                                            
                    ## If key in fields
                    if key == inputField and len(val) > 0:
                        cron = getCron4savedsearch(val, savedsearchesDict)
                        
                        if cron is not None:
                            results[x][outputField] = cron
                            
                        break
                        
    else:
        logger.warn('invocation_id=%s; signature=Result set empty' % (invocation_id))
    
    ## output
    splunk.Intersplunk.outputResults(results)
    logger.info('invocation_id=%s; signature=Finishing getcron' % (invocation_id))