#   Version 4.0
 
# Input tail operator
#
# o Adds everything if finds to splunk
#

import os, sys, logging as logger
import splunk.Intersplunk
import splunk.entity as en

logger.basicConfig(level=logger.INFO,
                   format='%(asctime)s %(levelname)s %(message)s',
                   filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','inputs.log'),
                   filemode='a')

def dictToKV(d):
    s = ""
    if d != None:
        for attr,val in d.items():
            s +=  ' %s="%s"' % (attr, val)
    return s

def addInput(sessionKey, source, namespace, owner, sourcetype, index):
    mon = en.getEntity('/data/inputs/monitor/','_new', sessionKey=sessionKey)
    mon["name"] = source
    if sourcetype != None:
        mon["sourcetype"] = sourcetype
    if index != None:
        mon["index"] = index
    mon.namespace = namespace
    mon.owner = owner
    en.setEntity(mon, sessionKey=sessionKey)

def deleteInput(sessionKey, source, namespace, owner):
    mon = en.deleteEntity('/data/inputs/monitor/', source, namespace, owner, sessionKey)

# return true if mysource, or a substring of it (e.g. directory), is already tailed
def alreadyTailed(tails, mysource):
    for tail in tails:
        if tail == mysource or (mysource.startswith(tail) and os.path.isdir(tail)):
            return True
    return False

def getTails(sessionKey, owner, namespace):
    monitors = en.getEntities('/data/inputs/monitor', sessionKey=sessionKey, owner=owner, namespace=namespace)
    return monitors.keys()
    
# tail all results, not already tailed
def addAll(results, index, sourcetype, args, sessionKey, owner, namespace):
    try:
        tails = getTails(sessionKey, owner, namespace)
        for result in results:
            try:
                mysource = result.get('source', None)
                if mysource == None:
                    continue
                # if no 'index' argument get value from source
                if index == None:
                    index = result.get('index', None)
                if not alreadyTailed(tails, mysource):
                    addInput(sessionKey, mysource, namespace, owner, sourcetype, index)
                    result['sourcetype'] = sourcetype
                    result['index'] = index
                    logger.info('Adding monitor: namespace=%s owner=%s source=%s index=%s sourcetype=%s. Args:%s' % (namespace, owner, mysource, index, sourcetype, dictToKV(args)))
                    result['status'] = 'added'
                else:
                    result['status'] = 'already_added'
            except Exception, e:
                msg = 'Error in adding monitor: %s.  namespace=%s owner=%s. Result: %s Args:%s' % (e, namespace, owner, str(result), dictToKV(args))
                import traceback
                stack =  traceback.format_exc()
                logger.error(stack)

                result['message'] = msg
                logger.error(msg)
    except Exception, e:
        logger.error('Error in adding monitor: %s' % str(e))
        logger.error('Sessionkey %s Owner %s Namespace %s' % (sessionKey, owner, namespace))
        import traceback
        stack =  traceback.format_exc()
        logger.error(stack)
        


# remove tail of all results, already tailed
def removeAll(results, args, sessionKey, owner, namespace):
    try:
        tails = getTails(sessionKey, owner, namespace)
        for result in results:
            try:
                mysource = result.get('source', None)
                if mysource == None:
                    continue
                if alreadyTailed(tails, mysource):
                    deleteInput(sessionKey, mysource, namespace, owner)
                    logger.info('Removed monitor: source=%s. Args:%s' % (mysource, dictToKV(args)))
                    result['status'] = 'removed'
                else:
                    result['status'] = 'already_removed'                    
            except Exception, e:
                msg = 'Error in removing monitor: %s. namespace=%s owner=%s. Result: %s Args:%s' % (e, namespace, owner, str(result), dictToKV(args))
                result['message'] = msg
                logger.error(msg)
    except Exception, e:
        logger.error('Error in removing monitor: %s.  Args:%s' % (str(e), dictToKV(args)))

def execute():
    results = []
    try:
        if len(sys.argv) < 2:
            results = splunk.Intersplunk.generateErrorResults('Missing "add" or "remove" argument.')
        else:
            subcommand = sys.argv[1].lower()
            if subcommand != 'add' and subcommand != 'remove':
                results = splunk.Intersplunk.generateErrorResults('Invalid argument ("%s").  Expected "add" or "remove" argument.' % subcommand)
            else:
                results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

                sessionKey = settings.get("sessionKey", None)
                owner      = settings.get("owner", "admin")
                namespace  = settings.get("namespace", "search")

                if sessionKey == None:
                    return splunk.Intersplunk.generateErrorResults("username/password authorization not given to 'input'.")

                dummykeywords, args = splunk.Intersplunk.getKeywordsAndOptions()
                index = args.get('index', None)
                sourcetype = args.get('sourcetype', None)
                if subcommand == 'add':
                    addAll(results, index, sourcetype, args, sessionKey, owner, namespace)
                else:
                    removeAll(results, args, sessionKey, owner, namespace)                    
                # outputresults
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        results = splunk.Intersplunk.generateErrorResults(str(e) + ". Traceback: " + str(stack))
    splunk.Intersplunk.outputResults(results)

if __name__ == '__main__':

    ## if sessionKey == None:
    ##    print "TESTING HARD CODE SESSION KEY !!!!!!!!"
    ##    sessionKey = splunk.auth.getSessionKey('admin', 'changeme')

    execute()
