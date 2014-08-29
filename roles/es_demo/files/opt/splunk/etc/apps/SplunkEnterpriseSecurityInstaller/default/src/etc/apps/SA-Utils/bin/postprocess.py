import logging
import logging.handlers
import os
import random
import splunk.Intersplunk
import splunk.admin as admin
import splunk.search
import splunk.util as util
import sys
import time
import traceback

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from postprocess import *

## Setup the logger
def setup_logger():
    """
    Setup a logger for the search command
    """
   
    logger = logging.getLogger('postprocess')
    logger.setLevel(logging.DEBUG)
   
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'postprocess.log']), maxBytes=25000000, backupCount=5)
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
    logger.info('invocation_id=%s; signature=Starting postprocess' % (invocation_id))
    
    ## Defaults
    namespace = PostProcess.DEFAULT_NAMESPACE
    sname = None
    sid = None
    
    searchTemplate = '| loadjob %s | %s'

    ## Override Defaults w/ opts below
    if len(sys.argv) > 1:
        for a in sys.argv:
            if a.startswith('sname='):
                where = a.find('=')
                sname = a[where+1:len(a)]
            elif a.startswith('sid='):
                where = a.find('=')
                sid = a[where+1:len(a)]
                
    ## Get organized results
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

    ## Obtain result count; if zero, do not proceed.
    result_count = len(results)
    
    ## Truncate the results
    results = []
    
    ## Validate sname and sid (zero-length strings also evaluate to False here)
    if sname and sid:
        
        ## Validate result_count separately for more intelligent logging.
        ## Note: this is only valid because our postprocess command uses
        ## results instead of raw events. If we used "events=t" in the command,
        ## we would need separate handling here to check the existence of
        ## event artifacts.
        if result_count > 0:
        
            ## Get session key
            sessionKey = settings.get('sessionKey', None)
       
            ## Get owner
            ## We could have gotten owner from eai:acl; however this way prevents errors and warnings
            ## caused by dispatching searches under owner='nobody'
            owner = PostProcess.getCurrentUser(sessionKey)
        
            if owner is None:
                owner = PostProcess.DEFAULT_OWNER
                      
            logger.info('invocation_id=%s; signature=Retrieved arguments; namespace=%s; sname=%s; sid=%s' % (invocation_id, namespace, sname, sid))
            
            ## Get post processes for savedsearch
            postprocesses = PostProcess.getPostProcesses(sessionKey, namespace=namespace, owner=owner, savedsearch=sname)
            
            logger.info('invocation_id=%s; signature=Retrieved post processes; postprocessDict=%s' % (invocation_id, postprocesses))
            
            ## populate searches2dispatch array
            if postprocesses is not None:
                for stanza, settings in postprocesses.items():
                    
                    ## initialize search
                    search = None
                    
                    ## initialize namespace
                    namespace = PostProcess.DEFAULT_NAMESPACE
                    
                    for key, val in settings.items():
                        if val is None:
                            val = ''
                            
                        if key == PostProcess.PARAM_POSTPROCESS:
                            ## strip whitespace
                            postprocess = val.strip()
                            
                            ## recursively strip leading pipes
                            while postprocess[0] == '|':
                                ## strip leading pipes
                                postprocess = postprocess.lstrip('\|')
                            
                                ## strip whitespace
                                postprocess = postprocess.strip()
                                                    
                            ## verify positive length
                            if len(postprocess) > 0:
                                ## fill search template
                                search = searchTemplate % (sid, postprocess)
                                
                                ## log successful formulation
                                logger.info('invocation_id=%s; signature=Successfully formulated post process job; sname=%s; postprocess=%s; search=%s' % (invocation_id, sname, stanza, search))
                        
                            ## warn if postprocess is of zero length after strips   
                            else:
                                search = None
                                logger.warn('invocation_id=%s; signature=Ignoring empty post process; sname=%s; postprocess=%s' % (invocation_id, sname, stanza))
    
                        ## get namespace
                        elif key == admin.EAI_ENTRY_ACL:
                            if val.has_key('app') and val['app'] is not None and len(val['app']) > 0:
                                namespace = val['app']
    
                    if search is not None:
                        ## dispatch job
                        try:
                            job = splunk.search.dispatch(search, hostPath=None, sessionKey=sessionKey, namespace=namespace, owner=owner)
                            
                            logger.info('invocation_id=%s; signature=Job successfully dispatched; sname=%s; postprocess=%s; response=\n%s' % (invocation_id, sname, stanza, job))
                            
                        except Exception as e:
                            e = 'invocation_id=%s; signature=Error dispatching job; sname=%s; postprocess=%s; exception=%s; traceback=\n%s' % (invocation_id, sname, stanza, str(e), traceback.format_exc())
                            logger.error(e)
        else:
            logger.warn('invocation_id=%s; signature=Postprocess searches not executed because parent search found no results; sname=%s; sid=%s' % (invocation_id, sname, sid))            

    ## if an issue with sname or sid exists                      
    else:
        logger.critical('invocation_id=%s; signature=Search name and/or id is None; sname=%s; sid=%s' % (invocation_id, sname, sid))
        
    splunk.Intersplunk.outputResults(results)