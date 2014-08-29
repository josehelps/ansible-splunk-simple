import cherrypy
import json
import logging
import splunk
import time
import controllers.module as module

logger = logging.getLogger('splunk.module.SOLNSearchSwapper')

class SOLNSearchSwapper(module.ModuleHandler):

    def generateResults(self, host_app=None, client_app=None, savedSearchName=None, useHistory=None):

        if savedSearchName: 
            jsonSearch = None
 	    owner = 'nobody'
            try: 
                savedSearchObject = splunk.search.getSavedSearch(label = savedSearchName, namespace = client_app, owner = owner)

                jsonSearch = splunk.appserver.mrsparkle.util.resurrectFromSavedSearch(
                    savedSearchObject = savedSearchObject,
                    hostPath = splunk.mergeHostPath(),
                    namespace = client_app,
                    owner = owner)
        
                job = splunk.search.getJobForSavedSearch(
                    savedSearchName,
                    useHistory="True", 
                    namespace=client_app,
                    owner=owner,
                    search='name=scheduler*')

                if (job):
                    jsonSearch["job"] = job.toJsonable(timeFormat='unix')

                return json.dumps(jsonSearch)

            except Exception, e:
                logger.exception(e)
                return ""
        else:
            logger.warn('savedSearchName was not passed from the caller')
            return ""

