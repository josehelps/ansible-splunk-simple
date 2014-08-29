import json
import logging
import logging.handlers
import splunk.Intersplunk
import sys

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))
from cim_models import DataModels


## Setup the logger
def setup_logger():
    """
    Setup a logger for the search command
    """
   
    logger = logging.getLogger('datamodelinfo')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
   
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'datamodelsimple.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
   
    logger.addHandler(file_handler)
   
    return logger

logger = setup_logger()


if __name__ == '__main__':
    
    logger.info('Starting datamodelinfo search command')
    
    return_type = 'models'
    datamodel = None
    obj = None
    nodename = None
    
    ## Override Defaults w/ opts below
    if len(sys.argv) > 1:
        for a in sys.argv:
            if a.startswith('type='):
                where = a.find('=')
                return_type = a[where+1:len(a)]
            elif a.startswith('datamodel='):
                where = a.find('=')
                datamodel = a[where+1:len(a)]
            elif a.startswith('object='):
                where = a.find('=')
                obj = a[where+1:len(a)]
            elif a.startswith('nodename='):
                where = a.find('=')
                nodename = a[where+1:len(a)]
    
    ## if nodename is specified, create obj
    if nodename and not obj:
        obj = nodename.split('.')
        obj = obj[-1]

    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    results = []  # we don't care about incoming results
  
    sessionKey = settings.get('sessionKey', False)
    
    try:
        ## validate sessionKey
        if not sessionKey:
            raise splunk.AuthenticationFailed
            
        if return_type == 'models':
            models = DataModels.getDatamodelList(sessionKey)
            results = [{'datamodel': i} for i in models]
        
        elif return_type == 'objects':
            if datamodel is not None and len(datamodel)>0:
                objects = DataModels.getDatamodelObjectList(datamodel, sessionKey)
                
                ## get the model
                model_id = DataModels.build_id(datamodel, None, None)
                model = DataModels.get(id=model_id, sessionKey=sessionKey)
                    
                ## load the json
                modelJson = json.loads(model.data)
                
                results = [{'object': i, 'lineage': DataModels.getObjectLineage(i, modelJson=modelJson)} for i in objects]

            else:
                e = 'Must specify datamodel for type: objects'
                logger.error(e)
                results = splunk.Intersplunk.generateErrorResults(e)
        
        elif return_type == 'attributes':                     
            if datamodel and obj:
                ## get the model
                model_id = DataModels.build_id(datamodel, None, None)
                model = DataModels.get(id=model_id, sessionKey=sessionKey)
                
                ## load the json
                modelJson = json.loads(model.data)
                
                ## retrieve lineage
                lineage = DataModels.getObjectLineage(obj, modelJson=modelJson, includeBaseObject=True)
         
                if len(lineage)>0:
                    ## string to list
                    lineage = lineage.split('.')
                    
                    if lineage[0]=='BaseEvent':
                        baseEventAttributes = ['_time', '_raw', 'source', 'sourcetype', 'host']
                        results.extend([{'attribute': i, 'lineage': i} for i in baseEventAttributes])
                                                
                    ## discard BaseObject
                    lineage = DataModels.stripBaseObject(lineage, outputMode="list")
                    
                    ## iterate through lineage
                    ## get attributes for each object
                    for x in range(0,len(lineage)):
                        ## create lineage_part
                        lineage_part = lineage[x]
                        ## get attribute lineage
                        ## note the x+1 here which does not overflow
                        ## >>> mylist = ['a', 'b', 'c', 'd', 'e']
                        ## >>> '.'.join(mylist[:5])
                        ## >>> 'a.b.c.d.e'
                        attributeLineage = '.'.join(lineage[0:x+1])
                         
                        ## get attributes for this object
                        attributes = DataModels.getObjectAttributes(lineage_part,modelJson)
    
                        ## add each attribute w/ it's lineage to the list of avail fields
                        for attribute in attributes:
                            results.append({'attribute': attribute, 'lineage': '%s.%s' % (attributeLineage,attribute)})
            
            else:
                e = 'Must specify datamodel and object for type: attributes'
                logger.error(e)
                results = splunk.Intersplunk.generateErrorResults(e)
                            
    except Exception, e:
        logger.error(e)
        results = splunk.Intersplunk.generateErrorResults(str(e))
    
    splunk.Intersplunk.outputResults(results)
    logger.info('Finishing datamodelinfo search command')
