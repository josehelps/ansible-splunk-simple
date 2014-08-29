#   Version 4.0
# 
# CrawlerManager -- data finder
#

import os, re, sys, time
import splunk
import splunk.bundle as bundle
import splunk.entity as en
import splunk.Intersplunk
import logging as logger

logger.basicConfig(level=logger.WARN, format='%(asctime)s %(levelname)s %(message)s',
                   filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','crawl.log'),
                   filemode='a')

class CrawlerManager:
    def __init__(self, sessionKey, owner, namespace, args):

        self.crawlers = []
        self.config = {}
        if sessionKey == None:
            logger.warn("Username/password authorization not given to 'crawl'. Attempting to carry on.")
        try:
            self.config = bundle.getConf('crawl', sessionKey)
        except:
            logger.error("Unable to contact the splunk server.")
            exit(-1)
            
        self.args = args
        self.sessionKey = sessionKey
        self.owner = owner
        self.namespace = namespace

    def addCrawler(self, crawler):
        self.crawlers.append(crawler)

    def getCrawlers(self):
        return self.crawlers
    
    def getConfig(self):
        return self.config

    def execute(self):
        results = []
        actions = []

        # for each crawler, execute and append on actions
        for crawler in self.crawlers:
            actions.extend(crawler.execute())
        results = actions            
        return results

class Crawler:
    def __init__(self, name, mgr, args):
        self.name = name
        self.mgr = mgr
        self.settings = {}
        logger.info("Getting configuration: %s", self.name)
        config = self.mgr.getConfig()
        if self.name not in config:
            logger.error("No stanza settings for %s.  Attempting to carry on." % self.name)
        else:
            stanza = config[self.name]
            # copy stanza settings to editable settings
            for attr,val in stanza.items():
                self.settings[attr] = val
        # override settings with args
        for attr,val in args.items():
            self.settings[attr] = val
    def execute(self):
        raise Exception("not implemented")

    def getSetting(self, attr, default="", lowercase=True):
        val = self.settings.get(attr, None)
        if val == None:
            logger.warn('No setting found in crawl: %s.  Using default: %s' % (attr, default))
            val = default
        if lowercase:
            val = val.lower()
        val = val.strip()
        # if list attr, get vals
        if attr.endswith("_list"):
            val = val.split(", ")
        return val

    def getBoolSetting(self, attr, default=""):
        val = self.getSetting(attr, default)
        return val.startswith("t") or val.startswith("y") or val.startswith("1")
    
    def getNumericSetting(self, attr, default=""):
        try:
            val = self.getSetting(attr, default)
            return int(val)
        except:
            return default

class SampleCrawler(Crawler):
    def __init__(self, mgr, args):
        Crawler.__init__(self, "file", mgr, args)
    def execute(self):
        index = self.getSetting('index', 'preview')
        actions = []
        filename = "bogus.log"
        action = AddTailAction(filename, index)
        actions.append(action)
        return actions

class Action:
    def __init__(self, attrs):
        self.attrs = attrs

    def getAttrs(self):
        return self.attrs
    
    def execute(self):
        raise Exception("not implemented")

class AddTailAction(Action):

    
    def __init__(self, values):
        self.attrs = {}
        self.attrs = values

    def __init__(self, filename, index, modtime=None, size=None, bytes=None, sourcetype=None, crawler_type='file'):
        self.attrs = {}
        if filename.endswith(os.sep):
            filename = filename[:-1]
        else:
            self.attrs['isfile'] = str(True)
        self.attrs['_raw'] = filename
        self.attrs['source'] = filename
        self.attrs['index'] = index
        self.attrs['size'] = size
        self.attrs['bytes'] = bytes
        if sourcetype!=None and len(sourcetype) > 0:
            self.attrs['sourcetype'] = sourcetype
        self.attrs['eventtype'] = 'crawled_%s' % (crawler_type)
        self.attrs['_time'] = modtime
        self.attrs['modtime'] = time.ctime(modtime)

    def __str__(self):
        return "Add Tail: %s" % self.attrs

    def valid(self, sessionKey, owner, namespace, monitors):
        mysource = self.attrs['source']
        for files in self.monitors:
            for filename in files:
                if mysource in filename:
                    return False
        return True

    def execute(self, sessionKey, owner, namespace):
        raise Exception("not implemented")


class AddHostAction(Action):

    def __init__(self, values):
        self.attrs = {}
        self.attrs = values

    # in the future may do something with host
    def valid(self, sessionKey, owner, namespace):
        return True
    def execute(self, sessionKey, owner, namespace):
        # do nothing
        pass
        

def execute():
    import crawl_factory
    results = []
    try:
        
        args = { 'add-all':'fail'} ## 'name':'file_crawler'}
        keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
        args.update(options)

        results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
        results = [] # we don't care about incoming results

        sessionKey = settings.get("sessionKey", None)
        owner      = settings.get("owner", None)
        namespace  = settings.get("namespace", None)
        ########TEST#####################
        # sessionKey = splunk.auth.getSessionKey('admin', 'changeme')
        ########TEST####################
        
        mgr = CrawlerManager(sessionKey, owner, namespace, args)

        if len(keywords) == 0:
            logger.warn("No crawl type specified.  Defaulting to crawling 'files'.")
            keywords = ["files"]
        
        # name = args['name']
        # add crawler for each keyword
        for name in keywords:
            crawler = crawl_factory.getCrawler(name, mgr, args)
            if crawler == None:
                splunk.Intersplunk.generateErrorResults("Unknown crawler '%s'.  Legal values are: %s" % (name, crawl_factory.getCrawlerNames()))
                return
            mgr.addCrawler(crawler)
            
        # do crawl
        actions = mgr.execute()

        monitors = en.getEntities('/data/inputs/monitor', sessionKey=sessionKey, owner=owner, namespace=namespace)
        
        # convert actions to results -- just a dictionary of attributes
        for action in actions:
            result = action.getAttrs()
            status = "not_added"
            try:
                if not action.valid(sessionKey, owner, namespace, monitors):
                    status = "added"
            except:
                status = "unknown"
            result['status'] = status
            results.append(result)
        # outputresults
        splunk.Intersplunk.outputResults(results)
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        splunk.Intersplunk.generateErrorResults(str(e))
        logger.error(str(e) + ". Traceback: " + str(stack))
if __name__ == '__main__':
    execute()

