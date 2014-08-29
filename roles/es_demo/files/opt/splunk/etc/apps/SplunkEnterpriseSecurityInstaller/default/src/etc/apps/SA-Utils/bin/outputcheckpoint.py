import logging
import logging.handlers
import csv
import os
import random
import splunk.Intersplunk
import splunk.admin as admin
import splunk.clilib.cli_common
import splunk.util as util
import sys
import time
import traceback

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


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
   
    logger = logging.getLogger('outputcheckpoint')
    logger.setLevel(logging.DEBUG)
   
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'outputcheckpoint.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
   
    logger.addHandler(file_handler)
   
    return logger

logger = setup_logger()


if __name__ == '__main__':
    ## Create a unique identifier for this invocation
    nowTime = util.mktimegm(time.gmtime())
    salt = random.randint(0, 100000)
    invocation_id = str(nowTime) + ':' + str(salt)
    
    ## Log initialization
    logger.info('invocation_id=%s; signature=Starting outputcheckpoint' % (invocation_id))
    
    ## Defaults
    modinput = None
  
    ## Override Defaults w/ opts below
    if len(sys.argv) > 1:
        for a in sys.argv:
            if a.startswith('modinput='):
                where = a.find('=')
                modinput = a[where+1:len(a)]
                
    ## Create modinput path
    if modinput is not None and len(modinput) > 0:
        
        try:
            splunk_db = splunk.clilib.cli_common.splunk_db
            logger.info('invocation_id=%s; signature=$SPLUNK_DB retrieved successfully; SPLUNK_DB=%s' % (invocation_id, splunk_db))
        except Exception as e:
            signature = 'Could not determine $SPLUNK_DB directory'
            logger.critical('invocation_id=%s; signature=%s; exception=%s' % (invocation_id, signature, str(e)))
            results = splunk.Intersplunk.generateErrorResults('Error; %s' % (signature))
            splunk.Intersplunk.outputResults(results)
            sys.exit(1)
            
        modinput_path = splunk_db + os.sep + 'modinputs' + os.sep + modinput
        
        ## Get organized results
        results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
        
        if len(results) > 0:
            ## make the directory if it does not exist
            try:
                os.mkdir(modinput_path, 0755)
                logger.info('invocation_id=%s; signature=Directory created successfully; directory=%s' % (invocation_id, modinput_path))
            
            except OSError:
                logger.info('invocation_id=%s; signature=Directory already exists; directory=%s' % (invocation_id, modinput_path))
                
            except Exception as e:
                signature = 'Could not create modular input directory'
                logger.critical('invocation_id=%s; signature=%s; directory=%s; exception=%s' % (invocation_id, signature, modinput_path, str(e)))
                results = splunk.Intersplunk.generateErrorResults('Error; %s' % (signature))
                splunk.Intersplunk.outputResults(results)
                sys.exit(1)
                
            ## create a file handler
            checkpoint_file = invocation_id.replace(':', '_') + '.csv'
            checkpoint_path = modinput_path + os.sep + checkpoint_file
            logger.info('invocation_id=%s; signature=Checkpoint path built successfully; file=%s' % (invocation_id, checkpoint_path))
           
            try:
                checkpoint_fh = open(checkpoint_path, 'w')
                logger.info('invocation_id=%s; signature=File handle created successfully; file=%s' % (invocation_id, checkpoint_path))
               
            except Exception as e:
                signature = 'Could not create checkpoint file handle'
                logger.critical('invocation_id=%s; signature=%s; file=%s; exception=%s' % (invocation_id, signature, checkpoint_path, str(e)))
                results = splunk.Intersplunk.generateErrorResults('Error; %s' % (signature))
                splunk.Intersplunk.outputResults(results)
                sys.exit(1)
                
            ## output file
            header = results[0].keys()
            outputResults = csv.DictWriter(checkpoint_fh, sorted(header), lineterminator='\n')
            outputResults.writeheader()
            outputResults.writerows(results)
                
            logger.info('invocation_id=%s; signature=Results written successfully' % (invocation_id))
                   
            ## close fh
            checkpoint_fh.close()
        
        else:
            logger.warn('invocation_id=%s; signature=Results set empty' % (invocation_id))
            
    else:
        signature = 'Modular input not specified; modinput=%s' % (modinput)
        logger.critical('invocation_id=%s; signature=%s' % (invocation_id, signature))
        results = splunk.Intersplunk.generateErrorResults('Error; %s' % (signature))
         
    splunk.Intersplunk.outputResults(results)