'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import logging
import logging.handlers
import os
import random
import splunk.Intersplunk
import splunk.util as util
import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from datetime import datetime
from time import gmtime, localtime, strftime

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

## Setup the logger
def setup_logger():
    """
    Setup a logger for the search command
    """
    
    logger = logging.getLogger('sorttimecols')
    logger.setLevel(logging.DEBUG)
    
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'sorttimecols.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()


if __name__ == '__main__':
    ## Create a unique identifier for this invocation
    nowTime = util.mktimegm(gmtime())
    salt = random.randint(0, 100000)
    invocation_id = str(nowTime) + ':' + str(salt)
    
    timeformat = None
    
    DEFAULT_DIRECTION = 'asc'
    ASCENDING_VALUES = ['asc', 'ascending']
    DESCENDING_VALUES = ['desc', 'descending']
    VALID_DIRECTIONS = []
    VALID_DIRECTIONS.extend(ASCENDING_VALUES)
    VALID_DIRECTIONS.extend(DESCENDING_VALUES)
    
    direction = DEFAULT_DIRECTION
    
    ## Log initialization
    logger.info('invocation_id=%s; signature=Starting sorttimecols' % (invocation_id))
    
    ## Override Defaults w/ opts below
    if len(sys.argv) > 1:
        for a in sys.argv:
            if a.startswith('timeformat='):
                where = a.find('=')
                timeformat = a[where+1:len(a)]
            elif a.startswith('direction='):
                where = a.find('=')
                direction = a[where+1:len(a)]
   
    ## Check strptime specifier
    if timeformat is not None:
        testTimestamp = '2005-07-01T00:00:00.000'
        testTimestamp = util.parseISO(testTimestamp)
        testTimestamp = testTimestamp.strftime(timeformat)
    
    else:
        signature = 'Timeformat parameter was not specified'
        logger.error('invocation_id=%s; signature=%s;' % (invocation_id, signature))
        results = splunk.Intersplunk.generateErrorResults('Error; %s' % signature)
        splunk.Intersplunk.outputResults(results)
        sys.exit()
    
    if (testTimestamp == timeformat.replace('%', '')):
        signature = 'Timeformat parameter is an invalid strptime specifier'
        logger.error('invocation_id=%s; signature=%s; timeformat=%s' % (invocation_id, signature, timeformat))
        results = splunk.Intersplunk.generateErrorResults('Error; %s' % signature)
        splunk.Intersplunk.outputResults(results)
        sys.exit()
        
    logger.info('invocation_id=%s; signature=Timeformat retrieved; timeformat=%s' % (invocation_id, timeformat))
            
    ## Check direction
    if direction.lower() not in VALID_DIRECTIONS:
        signature = "Direction parameter must be one of 'desc' or 'asc'"
        logger.error('invocation_id=%s; signature=%s; direction=%s' % (invocation_id, signature, direction))
        results = splunk.Intersplunk.generateErrorResults('Error; %s' % signature)
        splunk.Intersplunk.outputResults(results)
        sys.exit()
        
    logger.info('invocation_id=%s; signature=Direction retrieved; direction=%s' % (invocation_id, direction))
    
    ## Retrieve results and settings
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    ## Get session key
    sessionKey = settings.get('sessionKey', None)

    ## Initialize header
    dateHeader  = []
    otherHeader = []
        
    ## Populate headers
    if len(results) > 0:
        for key in results[0]:
            try:
                newKey = datetime.strptime(key, timeformat)
                                
                if newKey.year < 1970:
                    newKey = newKey.replace(year=1970)
                
                newKey = util.dt2epoch(newKey)
                newKey = int(newKey)
                dateHeader.append(newKey)
                
            except Exception as e:
                logger.warn('invoccation_id=%s; signature=Non-Date Key Found; key=%s; exception=%s' % (invocation_id,key,str(e)))
                otherHeader.append(key)
                    
    else:
        logger.warn('invocation_id=%s; signature=Result set empty' % (invocation_id))
        splunk.Intersplunk.outputResults(results)
        sys.exit()
    
    logger.info('invocation_id=%s; signature=Date Header Populated; dateHeader=%s' % (invocation_id, dateHeader))
    logger.info('invocation_id=%s; signature=Other Header Populated; otherHeader=%s' % (invocation_id, otherHeader))
    
    logger.info('invocation_id=%s; signature=Sorting headers' % (invocation_id))
    
    ## Sort headers
    dateHeader.sort()
    otherHeader.sort()
    
    if direction.lower() in DESCENDING_VALUES:
        dateHeader.reverse()
        otherHeader.reverse()
        
    logger.info('invocation_id=%s; signature=Merging headers' % (invocation_id))
    
    ## Merge headers
    header = []
    header.extend(otherHeader)
    header.extend(dateHeader)
    
    logger.info(header)
    
    logger.info('invocation_id=%s; signature=Creating ordered header dictionary' % (invocation_id))

    ## Create ordered header dictionary
    headerDict = util.OrderedDict()
    
    for key in otherHeader:
        headerDict[key] = key
                
    for key in dateHeader:
        origKey = strftime(timeformat, gmtime(key))
        headerDict[origKey] = origKey
                
    logger.info('invocation_id=%s; signature=Header generated; header=%s; headerDict=%s' % (invocation_id, header, headerDict))
    
    ## Initialize DictWriter
    output = csv.DictWriter(sys.stdout, headerDict, lineterminator='\n')
    
    ## Output header
    output.writerow(headerDict)
   
    ## Iterate results    
    for x in range(0,len(results)):
        outputResult = util.OrderedDict()
        
        ## Iterate ordered header dictionary
        for key in headerDict:
            outputResult[key] = results[x][key]
        
        ## output    
        output.writerow(outputResult)
        
    logger.info('invocation_id=%s; signature=Finishing sorttimecols' % (invocation_id))