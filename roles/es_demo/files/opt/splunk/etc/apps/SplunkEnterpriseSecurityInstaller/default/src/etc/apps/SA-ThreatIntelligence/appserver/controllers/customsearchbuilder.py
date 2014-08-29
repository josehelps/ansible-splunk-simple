import cherrypy
import json
import logging
import splunk
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.util as util
import sys
import time
import traceback

from logging import handlers
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field
from splunk.rest import simpleRequest

sys.path.append(make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))
from cim_models import DataModels

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.lookups import get_lookup_fields

logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.controllers.CustomSearchBuilder')

class CorrelationSearchesRH(SplunkAppObjModel):
    '''Class for correlation searches built using JSON Advanced Search Specification'''

    resource = '/configs/conf-correlationsearches'

    search = Field()
    
    rule_title = Field()
    rule_description = Field()
    drilldown_name = Field()
    drilldown_search = Field()
               
class InvalidDatamodelObject(Exception):
    pass
    
class InvalidInputlookup(Exception):
    pass

class InvalidSplitBy(Exception):
    pass

class InvalidAggregate(Exception):
    pass
    
class InvalidResultFilter(Exception):
    pass
    
class InvalidOutputMode(Exception):
    pass

class InvalidSearchPart(Exception):
    pass

class CustomSearchBuilder(controllers.BaseController):

    @route('/:get_data_models=get_data_models')
    @expose_page(must_login=True, methods=['GET']) 
    def getDataModelsAndObjects(self, **kwargs):
        
        # Get the session key
        sessionKey = cherrypy.session.get('sessionKey')
        
        # This will contain all of the information about the data-models and the associated objects
        data_models_info = []
        
        # Get the list of data-models
        for data_model in DataModels.getDatamodelList(sessionKey):
            
            try:
                data_models_info.append( {
                                          'name' : data_model,
                                          'objects' : DataModels.getDatamodelObjectList(data_model, sessionKey)
                                          } )
            except:
                pass
        
        return self.render_json(data_models_info)

    @route('/:get_available_fields=get_available_fields')
    @expose_page(must_login=True, methods=['GET']) 
    def getAvailableFieldsFromSpec(self, search_spec, **kwargs):
        
        # Get the session key
        sessionKey = cherrypy.session.get('sessionKey')
        
        # Parse the JSON
        search_spec_parsed = json.loads(search_spec)
        
        try:
            available_fields = CustomSearchBuilder.getAvailableFields(search_spec_parsed, sessionKey=sessionKey)
            
        except (InvalidResultFilter, InvalidAggregate, InvalidDatamodelObject, InvalidInputlookup) as e:
            return self.render_json( {
                                      'success': False,
                                      'message': 'Search specification is invalid: '  + str(e),
                                      })

        except Exception as e:
            return self.render_json( {
                                      'success': False,
                                      'message': 'Search specification could not be converted: ' + str(e),
                                      'traceback' : traceback.format_exc()
                                      })
        
        return self.render_json( {
                                  'success'   : True,
                                  'available_fields' : available_fields,
                                  'message'    : 'Search specification converted successfully'
                                  })

    @route('/:make_search_from_spec=make_search_from_spec')
    @expose_page(must_login=True, methods=['GET']) 
    def makeSearchFromSpec(self, search_spec, **kwargs):
        
        # Get the session key
        sessionKey = cherrypy.session.get('sessionKey')
            
        # Parse the JSON
        search_spec_parsed = json.loads(search_spec)
        
        # Make the correlation search string
        try:
            raw_search, parses = CustomSearchBuilder.makeCorrelationSearch(search_spec_parsed, sessionKey=sessionKey)
            
        except (InvalidResultFilter, InvalidAggregate, InvalidDatamodelObject, InvalidInputlookup) as e:
            return self.render_json( {
                                      'success': False,
                                      'message': 'Search specification is invalid: '  + str(e),
                                      })

        except Exception as e:
            return self.render_json( {
                                      'success': False,
                                      'message': 'Search specification could not be converted: ' + str(e),
                                      'traceback' : traceback.format_exc()
                                      })
        
        return self.render_json( {
                                  'success'    : True,
                                  'raw_search' : raw_search,
                                  'parses'     : parses,
                                  'message'    : 'Search specification converted successfully'
                                  })
    
    @staticmethod
    def getObjectLineage(cs, modelJson=None, sessionKey=None, includeBaseObject=False):
        ## sessionKey only required when 
        ## 1. datamodel/object are present
        ## 2. no modelJson is provided

        ## proceed if datamodel and object are specified
        if cs.get('datamodel', False) and cs.get('object', False):
               lineage = []

               if modelJson is None:
                   ## get the model
                   model_id = DataModels.build_id(cs['datamodel'], None, None)
                   model = DataModels.get(id=model_id, sessionKey=sessionKey)

                   ## load the json
                   modelJson = json.loads(model.data)

               lineage = DataModels.getObjectLineage(cs['object'], modelJson, includeBaseObject=includeBaseObject)

               if len(lineage)>0:
                   return lineage
               
               else:
                   e = "Could not determine lineage for datamodel: %s, object: %s" % (cs['datamodel'],cs['object'])
                   logger.error(e)
                   raise InvalidDatamodelObject(e)
        
        else:
            logger.warn('Both datamodel and object are required to build nodename')
        
        return ''

    @staticmethod
    def isSearchRT(cs):
       return cs.get('earliest', '').startswith('rt') or cs.get('latest', '').startswith('rt')

    @staticmethod
    def isRTPossible(correlationSearchJson):
        ## get correlation search parts
        correlationSearchParts = correlationSearchJson.get('searches', [])
        correlationSearchPartCount = len(correlationSearchParts)
        
        if correlationSearchPartCount==1:
            cs = correlationSearchParts[0]
        
            if cs.get('datamodel', False) and cs.get('object', False):
                return True
        
        return False
                            
    @staticmethod
    def getEarliest(cs):
        earliestTemplate = 'earliest=%s'

        if cs.get('earliest', False):
            return earliestTemplate % cs['earliest']
        
        return ''

    @staticmethod
    def getLatest(cs):
        latestTemplate = 'latest=%s'

        if cs.get('latest', False):
            return latestTemplate % cs['latest']

        return ''

    @staticmethod
    def getSearchBasedTimeFilters(cs):
        ## This is `make_ts_value(2)`
        timequalTemplate   = 'eval %s=case(match("%s", "^\d"), tostring("%s"),  match("%s", "^([@\+-]){1}"), relative_time(time(), "%s"),  true(), time())'
        timefilterTemplate = '| %s | %s | where (%s>=earliestQual AND %s<=latestQual) | fields - earliestQual, latestQual'

        if cs.get('inputlookup', False) and cs['inputlookup'].get('timeField', False):
            timeField = cs['inputlookup']['timeField']

            if cs.get('earliest', False):
                earliest = cs['earliest']
            else:
                earliest = '0'
                logger.warn("No earliest qualifier specified.  Using 0.")

            if cs.get('latest', False):
                latest = cs['latest']
            else:
                latest = '+0s'
                logger.warn("No latest qualifier specified. Using default (now).")
            
            earliestQual = timequalTemplate % ('earliestQual', earliest, earliest, earliest, earliest)
            latestQual = timequalTemplate % ('latestQual', latest, latest, latest, latest)

            ## If this is an all time search, there is no point in doing work
            if earliest=='0' and (latest=='now' or latest=='+0s'):
                return ''
            
            else:
                return timefilterTemplate % (earliestQual, latestQual, timeField, timeField)

        else:
            logger.warn("No time field specified")
        
        return ''

    @staticmethod
    def getEventFilter(cs, tstats=False):
        ## Proper field handling is crucial since this is slated for use in both:
        ## 1. The tstats where clause
        ## 2. Use with "| search" or "| where"
        ##
        ## tstats (like stats) uses double quotes for field names
        ## where uses single quotes for field names
        ## for now we will just replace single quotes w/ double quotes

        ## we also have issues that not all event filters can be injected into tstats

        if cs.get('eventFilter', False):
            if tstats:
                return cs['eventFilter'].replace('\'','"')
            else:
                return cs['eventFilter']
                
        else:
            logger.warn("No event filter specified")
        
        return ''

    @staticmethod
    def getAggregates(cs):

        aggregateString = ''
        
        if cs.get('aggregates', False):
            for aggregate in cs['aggregates']:

                ## We must have a function
                if aggregate.get('function', False):

                    ## We must have an attribute
                    if aggregate.get('attribute', False):
                        
                        ## If we have an alias
                        if aggregate.get('alias', False):
                            aggregateTemplate = '%s(%s) as "%s",'
                            aggregateString += aggregateTemplate % (aggregate['function'],aggregate['attribute'],aggregate['alias'])

                        else:
                            aggregateTemplate = "%s(%s),"
                            aggregateString += aggregateTemplate % (aggregate['function'],aggregate['attribute'])

                    ## Unless function is count
                    elif aggregate['function'] == 'count':

                        ## If we have an alias
                        if aggregate.get('alias', False):
                            aggregateTemplate = '%s as "%s",'
                            aggregateString += aggregateTemplate % (aggregate['function'],aggregate['alias'])

                        else:
                            aggregateTemplate = '%s,'
                            aggregateString += aggregateTemplate % aggregate['function']

                    else:
                        e = 'All functions except count must have an attribute'
                        logger.error(e)
                        raise InvalidAggregate(e)

                else:
                    e = 'Aggregate with no function not possible'
                    logger.error(e)
                    raise InvalidAggregate(e)

        else:
            logger.warn("No aggregates specified")

        return aggregateString.rstrip(',')

    @staticmethod
    def getSplitBy(cs):
        splitbyTemplate = 'by %s'

        if cs.get('splitby', False):
            splitbyString = ''
            for splitby in cs['splitby']:
                if splitby.get('attribute', False):
                    splitbyString += '"%s"' % (splitby['attribute'])
                    splitbyString += ','
                else:
                    e = 'A valid splitby must specify an attribute'
                    logger.error(e)
                    raise InvalidSplitBy

            return splitbyTemplate % (splitbyString).rstrip(',')

        else:
            logger.warn("No splitby specified")
        
        return ''

    @staticmethod
    def getSplitByRename(cs):
        renameTemplate = '| rename %s'
        asTemplate     = '"%s" as "%s",'
        
        renameString = ''
        
        if cs.get('splitby', False):
            for splitby in cs['splitby']:
                if splitby.get('alias', False) and splitby.get('attribute', False):
                    renameString += asTemplate % (splitby['attribute'],splitby['alias'])
        
        if len(renameString)>0:
            return renameTemplate % (renameString.rstrip(','))
        
        return ''        

    @staticmethod
    def getAvailableFields(cs, modelJson=None, sessionKey=None, use_default=False):
        ## sessionKey only required if aggregates are present
        ## aggregates imply a transformation of the results so we know what the search output will look like

        availableFields = []

        ## if aggregates are present
        if cs.get('aggregates', False):
            ## iterate through the aggregates
            for aggregate in cs['aggregates']:
                ## if we have an alias, add that
                if aggregate.get('alias', False):
                    availableFields.append(aggregate['alias'])
                ## if not, add the function attribute
                elif aggregate.get('function', False) and aggregate.get('attribute', False):
                    aggregateTemplate = "%s(%s)"
                    availableFields.append(aggregateTemplate % (aggregate['function'],aggregate['attribute']))
                ## if not, see if the function is count
                elif aggregate.get('function', False) == 'count':
                    availableFields.append(aggregate['function'])

            ## if splitbys are present
            if cs.get('splitby', False):
                for splitby in cs['splitby']:
                    if splitby.get('alias', False):
                        availableFields.append(splitby['alias'])
                    elif splitby.get('attribute', False):
                        availableFields.append(splitby['attribute'])

        ## elif datamodel/object
        elif cs.get('datamodel', False) and cs.get('object', False):

            if modelJson is None:
                ## validate sessionKey
                if not sessionKey:
                    raise splunk.AuthenticationFailed

                ## get the model
                model_id = DataModels.build_id(cs['datamodel'], None, None)
                model = DataModels.get(id=model_id, sessionKey=sessionKey)

                ## load the json
                modelJson = json.loads(model.data)

            ## retrieve lineage
            lineage = DataModels.getObjectLineage(cs['object'], modelJson=modelJson, includeBaseObject=True)
             
            if len(lineage)>0:
                ## string to list
                lineage = lineage.split('.')          
                
                ## per SOLNESS-5244: this list should only include fields avail to
                ## both | datamodel and | tstats with the exception of _raw
                if lineage[0]=='BaseEvent':
                    availableFields.extend(['_time', '_raw', 'source', 'sourcetype', 'host'])

                ## discard BaseObject
                lineage = DataModels.stripBaseObject(lineage, outputMode="list")

                ## iterate through lineage
                ## get attributes for each object
                for x in range(0,len(lineage)):
                    ## create obj
                    obj = lineage[x]
                    ## get attribute lineage
                    ## note the x+1 here which does not overflow
                    ## >>> mylist = ['a', 'b', 'c', 'd', 'e']
                    ## >>> '.'.join(mylist[:5])
                    ## >>> 'a.b.c.d.e'
                    attributeLineage = '.'.join(lineage[0:x+1])
                     
                    ## get attributes for this object
                    attributes = DataModels.getObjectAttributes(obj,modelJson)

                    ## add each attribute w/ it's lineage to the list of avail fields
                    for attribute in attributes:
                        available_field = '%s.%s' % (attributeLineage,attribute)
                        availableFields.append(available_field)
                     
                return availableFields

            else:
                e = "Could not determine lineage for datamodel: %s, object: %s" % (cs['datamodel'],cs['object'])
                logger.error(e)
                raise InvalidDatamodelObject(e)
        
        ## elif inputlookup
        elif cs.get('inputlookup', False) and cs['inputlookup'].get('lookupName', False):
            lookupFields = get_lookup_fields(cs['inputlookup']['lookupName'], 'SA-ThreatIntelligence', 'nobody', sessionKey, use_default)
            if lookupFields is not None:
                availableFields = lookupFields

        return availableFields

    @staticmethod
    def getResultFilter(cs, availableFields=None, modelJson=None, sessionKey=None, use_default=False):
        ## sessionKey only required if
        ## 1.  we have result filters to check
        ## 2.  no modelJson is provided

        filterTemplate = "'%s'%s%s"

        if cs.get('resultFilter', False):

            if cs['resultFilter'].get('field', False) and cs['resultFilter'].get('comparator', False) and cs['resultFilter'].get('value', False):
                
                if availableFields is None:
                    ## if we don't have json, go do work w/ sessionKey
                    if modelJson is None:
                        ## validate sessionKey
                        if not sessionKey:
                            raise splunk.AuthenticationFailed
                           
                        availableFields = CustomSearchBuilder.getAvailableFields(cs, sessionKey=sessionKey, use_default=use_default)
                        
                    ## if we have modelJson, use it
                    else:
                        availableFields = CustomSearchBuilder.getAvailableFields(cs, modelJson=modelJson)
                   
                if cs['resultFilter']['field'] in availableFields:
                     ## Todo: Properly quote value if it is a string
                     return filterTemplate % (cs['resultFilter']['field'], cs['resultFilter']['comparator'], cs['resultFilter']['value'])

                else:
                    e = 'Field %s must be in the list of available fields: %s' % (cs['resultFilter']['field'], availableFields)
                    logger.error(e)
                    raise InvalidResultFilter(e)

            else:
                e = 'Valid result filters must have a field, comparator, and value'
                logger.error(e)
                raise InvalidResultFilter(e)

        else:
            logger.warn('No result filters specified')
        
        return ''

    @staticmethod
    def mapNotableFields(availableFields):
        '''
        ## Performs field renaming prior to events being written to notable index.
        ## Renaming is performed to retain information about the original event,
        ## as well as to satisfy certain requirements of the Notable Event renderer.
        ##
        ## Note that in AddInfoProcessor.cpp, these fields are automatically mapped by the
        ## SummaryIndexProcessor class and thus need not be renamed:
        ##   index       -> orig_index
        ##   source      -> orig_source
        ##   sourcetype  -> orig_sourcetype
        ##   host        -> orig_host
        ##   search_name -> source (set in header of stash file)
        ##
        '''
        mapTemplate    = ''

        fieldTemplate  = '| fields - %s'
        
        renameTemplate = '| rename %s'
        asTemplate     = '"%s" as "%s",'

        ## handle special fields
        specialFields = ['_time', 
                          '_raw',
                          'event_id',
                          'splunk_server',
                          'linecount',
                          'eventtype',
                          'timestartpos',
                          'timeendpos',
                          'event_hash',
                          'rule_name',
                          'rule_title',
                          'rule_description',
                          'drilldown_search',
                          'drilldown_name',
                          'security_domain',
                          'governance',
                          'control',
                          'status',
                          'owner',
                          'default_owner']

        ## initialize some variables so we only do things once
        tag_colon       = False
        date_underscore = False

        ## intialize some strings to be templatized
        renameString   = ''
        discardString  = ''

        for availableField in availableFields:
            if availableField in specialFields:
                if availableField.startswith('_'):
                    renameString += asTemplate % (availableField,'orig' + availableField)
                else:
                    renameString += asTemplate % (availableField,'orig_' + availableField)
                    
            ## handle tag
            elif availableField=='tag':
                mapTemplate  += '| eval tag=mvjoin(tag,"|") '
                renameString += asTemplate % ('tag','orig_tag')
                
            ## handle tag::
            elif not tag_colon and availableField.startswith('tag::'):
                ## only do this once
                renameString += asTemplate % ('tag::*','orig_tag::*')
                tag_colon = True

            ## handle discards
            elif not date_underscore and availableField.startswith('date_'):
                ## only do this once
                discardString += 'date_*,'
                date_underscore = True

            elif availableField == 'punct':
                discardString += 'punct,'

        if len(renameString)>0:
            mapTemplate += (renameTemplate % (renameString.rstrip(',')))

        if len(discardString)>0:
            mapTemplate += (fieldTemplate % (discardString.rstrip(',')))

        return mapTemplate
        
    @staticmethod
    def getConstDedupId(correlationSearchJson):
        ## alert.suppress.fields should be a list
        constDedupString = '| eval const_dedup_id="const_dedup_id"'
        
        ## if alert.suppress exists, if alert.suppress is on, and no alert.suppress.fields specified  
        if correlationSearchJson.get('alert.suppress', False):
            suppress               = util.normalizeBoolean(correlationSearchJson['alert.suppress'], includeIntegers=True)
            suppress_fields        = correlationSearchJson.get('alert.suppress.fields', [])
            suppress_fields_length = len(suppress_fields)
            
            if suppress and (suppress_fields_length==0 or (suppress_fields_length==1 and suppress_fields[0]=="const_dedup_id")):
                return constDedupString
        
        ## else return empty string    
        return ''
    
    @staticmethod
    def getCorrelationSearch(savedsearch, sessionKey):
        ## sessionKey required to do anything
        if not sessionKey:
            raise splunk.AuthenticationFailed

        correlationSearchJson = {}
        savedsearchId = CorrelationSearchesRH.build_id(savedsearch, None, None)
        correlationSearchRaw = CorrelationSearchesRH.get(id=savedsearchId, sessionKey=sessionKey)
        correlationSearchJson = json.loads(correlationSearchRaw.search)

        return correlationSearchJson
        
    @staticmethod
    def getKeyEval(cs):
        template = "| eval cs_key='%s'"
        
        if cs.get('key', False):
            return template % (cs['key'])
         
        return ''

    @staticmethod
    def makeRaw(cs, modelJson, mapNotables=True):
        searchString = ''
    
        ## here is the raw search template
        template = ['| datamodel "%s" "%s" search ',  #0 - datamodel (Datamodel/Object)
                    '| where %s ',                    #1 - where (Event Filter)
                    '| stats %s %s ',                 #2 - stats (Aggregates/Splitby)
                    '%s ',                            #3 - Splitby rename
                    '| where %s ',                    #4 - where (Result Filter)
                    '%s '                             #5 - Map Notable Events
                   ]

        ## check for datamodel and object
        if cs.get('datamodel', False) and cs.get('object', False):
            ## start building string
            searchString += template[0] % (cs['datamodel'],cs['object'])

            ## get event filters
            eventFilter = CustomSearchBuilder.getEventFilter(cs)
            if len(eventFilter) > 0:
                searchString += template[1] % (eventFilter)

            ## get aggregates and splitby
            aggregates = CustomSearchBuilder.getAggregates(cs)
            splitby = CustomSearchBuilder.getSplitBy(cs)

            ## if we have both
            if len(aggregates)>0 and len(splitby)>0:
                searchString += template[2] % (aggregates,splitby)
                
                ## get splitby rename
                splitbyRename = CustomSearchBuilder.getSplitByRename(cs)
                if len(splitbyRename)>0:
                    searchString += template[3] % (splitbyRename)

            ## aggregates only
            elif len(aggregates)>0:
                searchString += '| stats %s ' % (aggregates)

            ## splitby only
            elif len(splitby)>0:
                e = 'Splitby specified with no aggregates'
                logger.error(e)
                raise InvalidSearchPart(e)

            ## get available fields
            availableFields = CustomSearchBuilder.getAvailableFields(cs, modelJson=modelJson)

            ## get result filter
            resultFilter = CustomSearchBuilder.getResultFilter(cs, availableFields=availableFields)
            if len(resultFilter)>0:
                searchString += template[4] % (resultFilter)

            ## get notable map            
            ## per SOLNESS-5244: we need to extend the list of available fields
            ## to include additional splunk reserved fields when no aggregates are present
            if len(aggregates)<1:
                availableFields.extend(['date_mday',
                                        'linecount',
                                        'eventtype',
                                        'punct',
                                        'splunk_server',
                                        'tag',
                                        'timestartpos',
                                        'timeendpos'
                                       ])
                                            
            if mapNotables:
                notableMap = CustomSearchBuilder.mapNotableFields(availableFields)
                if len(notableMap)>0:
                    searchString += template[5] % (notableMap)

        else:
            logger.error('Raw search requires valid datamodel and object')
        
        return searchString.strip()

    @staticmethod
    def makeTstats(cs, modelJson, mapNotables=True, strictMode=True, addTimeConstraints=True):
        searchString = ''
        
        ## here is the tstats search template
        template = ['| tstats allow_old_summaries=true %s from datamodel=%s where %s %s nodename=%s %s %s ',  #0 - tstats (Aggregates/Datamodel/Nodename/Event Filter/Splitby)
                    '%s ',                                                                                    #1 - Splitby rename
                    '| where %s ',                                                                            #2 - where (Result Filter 
                    '%s '                                                                                     #3 - Map Notable Events
                   ]
        
        ## per SOLNESS-4987: we need not return tstats if RT is requested
        if CustomSearchBuilder.isSearchRT(cs):
            e = 'RT search requested.  Cannot produce a valid tstats search.'
        
            if strictMode:
                logger.error(e)
                raise InvalidSearchPart(e)
            
            else:
                logger.warn(e)
                return '' 
        
        ## per SOLNESS-4979: we need not return tstats if _raw aggregates/splitbys are present
        if cs.get('aggregates', False):
            ## iterate aggregates
            for aggregate in cs['aggregates']:
                ## aggregate should have an attribute
                if aggregate.get('attribute', False) and aggregate['attribute'] == '_raw':
                    e = '_raw aggregates detected.  Cannot produce a valid tstats search.'
                    
                    if strictMode:
                        logger.error(e)
                        raise InvalidSearchPart(e)
                    
                    else:
                        logger.warn(e)
                        return ''
        
        if cs.get('splitby', False):
            ## iterate splitby
            for splitby in cs['splitby']:
                ## splitby should have an attribute
                if splitby.get('attribute', False) and splitby['attribute'] == '_raw':
                    e = '_raw splitby detected.  Cannot produce a valid tstats search.'
                    
                    if strictMode:
                        logger.error(e)
                        raise InvalidSearchPart(e)
                    
                    else:
                        logger.warn(e)
                        return ''
        
        aggregates = CustomSearchBuilder.getAggregates(cs)
        nodename   = CustomSearchBuilder.getObjectLineage(cs, modelJson=modelJson, includeBaseObject=True)
        
        ## per SOLNESS-4995: Only allow BaseEvent objects
        if nodename.startswith('BaseEvent'):
            nodename = nodename.lstrip('BaseEvent.')
            
        else:
            e = 'Non BaseEvent object detected.  Cannot produce a valid tstats search.'
        
            if strictMode:
                logger.error(e)
                raise InvalidSearchPart(e)
            
            else:
                logger.warn(e)
                return ''
        
        if cs.get('datamodel', False) and len(nodename)>0 and len(aggregates)>0:
            earliest    = ''
            latest      = ''
            eventFilter = CustomSearchBuilder.getEventFilter(cs, tstats=True)
            splitby     = CustomSearchBuilder.getSplitBy(cs)
            
            if addTimeConstraints:
                earliest = CustomSearchBuilder.getEarliest(cs)
                latest   = CustomSearchBuilder.getLatest(cs)              
            
            searchString += template[0] % (aggregates, cs['datamodel'], earliest, latest, nodename, eventFilter, splitby)
            
            ## get splitby rename
            splitbyRename = CustomSearchBuilder.getSplitByRename(cs)
            if len(splitbyRename)>0:
                searchString += template[1] % (splitbyRename)
                
            ## get available fields
            availableFields = CustomSearchBuilder.getAvailableFields(cs, modelJson=modelJson)

            ## get result filter
            resultFilter = CustomSearchBuilder.getResultFilter(cs, availableFields=availableFields)
            if len(resultFilter)>0:
                searchString += template[2] % (resultFilter)

            ## get notable map
            if mapNotables:
                notableMap = CustomSearchBuilder.mapNotableFields(availableFields)
                if len(notableMap)>0:
                    searchString += template[3] % (notableMap)
            
        else:
            e = 'Tstats searches must have a datamodel, object, and aggregate'
            
            if strictMode:
                logger.error(e)
                raise InvalidSearchPart(e)
            
            else:
                logger.warn(e)

        return searchString.strip() 

    @staticmethod
    def makeInputlookup(cs, sessionKey, mapNotables=True, use_default=False):
        searchString = ''
        
        ## here is the inputlookup search template
        template = ['| inputlookup append=T %s %s ',  #0 - inputlookup (Table)
                    '| where %s ',                    #1 - where (Event Filter)
                    '| stats %s %s ',                 #2 - stats (Aggregate/Splitby)
                    '%s ',                            #3 - Splitby rename
                    '| where %s ',                    #4 - where (Result Filter)
                    '%s '                             #5 - Map Notable Events
                   ]

        ## check for inputlookup
        if cs.get('inputlookup', False) and cs['inputlookup'].get('lookupName', False):
             
            ## per SOLNESS-4987: we should except if RT is requested
            if cs['inputlookup'].get('timeField', False) and CustomSearchBuilder.isSearchRT(cs):
                e = 'RT search requested.  Cannot produce a valid inputlookup search.'
                logger.error(e)
                raise InvalidSearchPart(e)
        
            ## get time based filters
            timeFilter = CustomSearchBuilder.getSearchBasedTimeFilters(cs)

            ## start building string
            searchString += template[0] % (cs['inputlookup']['lookupName'], timeFilter)

            ## get event filters
            eventFilter = CustomSearchBuilder.getEventFilter(cs)
            if len(eventFilter) > 0:
                   searchString += template[1] % (eventFilter)

            ## get aggregates and splitby
            aggregates = CustomSearchBuilder.getAggregates(cs)
            splitby = CustomSearchBuilder.getSplitBy(cs)

            ## if we have both
            if len(aggregates)>0 and len(splitby)>0:
                searchString += template[2] % (aggregates,splitby)
                
                ## get splitby rename
                splitbyRename = CustomSearchBuilder.getSplitByRename(cs)
                if len(splitbyRename)>0:
                    searchString += template[3] % (splitbyRename)
            
            ## aggregates only
            elif len(aggregates)>0:
                searchString += '| stats %s ' % (aggregates)

            ## splitby only
            elif len(splitby)>0:
                e = 'Splitby specified with no aggregates'
                logger.error(e)
                raise InvalidSearchPart(e)

            ## get available fields
            availableFields = CustomSearchBuilder.getAvailableFields(cs, sessionKey=sessionKey, use_default=use_default)

            ## get result filter
            resultFilter = CustomSearchBuilder.getResultFilter(cs, availableFields=availableFields)
            if len(resultFilter)>0:
                searchString += template[4] % (resultFilter)

            ## get notable map
            if mapNotables:
                notableMap = CustomSearchBuilder.mapNotableFields(availableFields)
                if len(notableMap)>0:
                    searchString += template[5] % (notableMap)
                
        else:
            e = 'inputlookup search requires lookup name'
            logger.error(e)
            raise InvalidInputlookup(e)
 
        return searchString.strip()
            
    @staticmethod
    def makeCorrelationSearch(correlationSearchJson, modelJson=None, sessionKey=None, outputMode="single", use_default=False):
        ## sessionKey used in every output mode
        if not sessionKey:
            raise splunk.AuthenticationFailed
       
        searchString = ''
        
        ## get correlation search parts           
        correlationSearchParts = correlationSearchJson.get('searches', [])
        correlationSearchPartCount = len(correlationSearchParts)
        
        ## single part search
        if correlationSearchPartCount==1:
            cs = correlationSearchParts[0]
            
            ## if single mode is requested
            if outputMode=='single':
                datamodel = cs.get('datamodel', False)
                
                ## if search part contains a datamodel
                if datamodel and cs.get('object', False):
                    
                    if modelJson is None:
                        ## get the model
                        model_id = DataModels.build_id(datamodel, None, None)
                        model = DataModels.get(id=model_id, sessionKey=sessionKey)
        
                        ## load the json
                        modelJson = json.loads(model.data)
                        
                    raw        = CustomSearchBuilder.makeRaw(cs, modelJson=modelJson)
                    raw_length = len(raw)
                    
                    tstats        = CustomSearchBuilder.makeTstats(cs, modelJson=modelJson, strictMode=False, addTimeConstraints=False)
                    tstats_length = len(tstats)
                    
                    parses = False
                    
                    ## if a non zero length tstats search is available, take it                    
                    if tstats_length>0:
                        ## validate search with splunk's parser
                        ## we do parsing here, in case a complex where clause is passed to tstats
                        status, contents = simpleRequest("search/parser", sessionKey=sessionKey, method='GET', getargs={'q': tstats, 'output_mode': "json"})
                    
                        if status.status == 200:
                            parses = True
                            searchString += tstats
                        else:
                            logger.warn("tstats search does not parse, tstats search cannot be used:" + str(contents))
                                        
                    ## if tstats was zero length or does not parse, take raw search
                    if (tstats_length==0 or (tstats_length>0 and not parses)) and raw_length>0:
                        searchString += raw
                    
                    ## if tstats was zero length or does not parse, and no raw search    
                    elif (tstats_length==0 or (tstats_length>0 and not parses)) and raw_length==0:
                        e = 'Single output mode with specified datamodel %s did not return a valid tstats %s or raw %s search' % (datamodel, tstats, raw)
                        logger.error(e)
                        raise InvalidSearchPart(e)
                
                ## if search part contains an inputlookup
                elif cs.get('inputlookup', False):
                    searchString += CustomSearchBuilder.makeInputlookup(cs, sessionKey=sessionKey, use_default=use_default)
                
                else:
                    e = 'A search part must specify either a datamodel and object, or an inputlookup'
                    logger.error(e)
                    raise InvalidSearchPart(e)

           ## output multi search
            elif outputMode=='multi':
                e = 'Output mode "multi" not available for single-part searches.  Use output mode "single".'
                logger.error(e)
                raise InvalidOutputMode(e)
        
            else:
                e = 'Output mode %s not recognized' % (outputMode)
                logger.error(e)
                raise InvalidOutputMode(e)
                
        ## multi-part search
        elif correlationSearchPartCount>1:
        
            ## output raw event search
            if (outputMode=='raw' or outputMode=='tstats' or outputMode=='inputlookup'):
                e = 'Output mode "%s" not available for multi-part searches.  Use output mode "multi".' % (outputMode)
                logger.error(e)
                raise InvalidOutputMode(e)
                
            ## output multi search
            elif outputMode=='multi':
                part = 0
                allAvailableFields = []
                
                joinTemplate = ' | join type=inner cs_key [%s]'

                ## iterate over each search part
                for cs in correlationSearchParts:
                    searchStringPart = ''
                    
                    ## this is necessary as we iterate
                    ## also, modelJson can not be passed for a multi-part search
                    modelJson = None
                    
                    if modelJson is None and cs.get('datamodel', False):
                        ## get the model
                        model_id = DataModels.build_id(cs['datamodel'], None, None)
                        model = DataModels.get(id=model_id, sessionKey=sessionKey)
        
                        ## load the json
                        modelJson = json.loads(model.data)
                    
                    ## if search part is a datmodel/object
                    if cs.get('datamodel', False) and cs.get('object', False):
                        searchStringPart = CustomSearchBuilder.makeTstats(cs, modelJson, mapNotables=False)
                    
                    ## if search part is a inputlookup
                    elif cs.get('inputlookup', False):
                        searchStringPart = CustomSearchBuilder.makeInputlookup(cs, sessionKey, mapNotables=False, use_default=use_default)
                    
                    else:
                        e = 'A search part must specify either a datamodel and object, or an inputlookup'
                        logger.error(e)
                        raise InvalidSearchPart(e)
                    
                    ## if we got back a positive search string part
                    if len(searchStringPart) > 0:
                        '''
                        !important - here is where we test for field overlaps between search parts
                                     however, we need to allow overlap for the key field
                                     this also means we need to test key validity earlier
                        '''
                        
                        ## we pass both a modelJson and sessionKey here because we can't assume datamodel vs. inputlookup
                        availableFields = CustomSearchBuilder.getAvailableFields(cs, modelJson=modelJson, sessionKey=sessionKey, use_default=use_default)
                        
                        ## verify that a key is specified
                        if cs.get('key', False):
                            for availableField in availableFields:
                                if availableField in allAvailableFields and availableField!=cs['key']:
                                    e = 'Overlap in fields detected.  Each search part in a multi-part search must output a unique set of fields.'
                                    logger.error(e)
                                    raise InvalidSearchPart(e)
                        
                        else:
                            e = 'Each search part in a mult-part search must specify a valid key'
                            logger.error(e)
                            raise InvalidSearchPart(e)
                        
                        ## collect additional available fields        
                        allAvailableFields.extend(availableFields)
                        
                        ## verify that a key is in availableFields
                        if cs['key'] in availableFields:
                            searchStringPart += ' %s' % (CustomSearchBuilder.getKeyEval(cs))
                            
                        else:
                            e = 'Each search part in a mult-part search must specify a valid key'
                            logger.error(e)
                            raise InvalidSearchPart(e)
                        
                        ## if not first part add as join
                        if part > 0:
                            searchString += joinTemplate % (searchStringPart)
                        
                        else:
                            searchString += searchStringPart
                    
                    else:
                        e = 'The search part specification %s was parsed into a zero length search.  This likely represents an unhandled error.' % (cs)
                        logger.error(e)
                        raise InvalidSearchPart(e)
                    
                    part += 1
                
                if len(searchString)>0:
                    ## get notable map
                    notableMap = CustomSearchBuilder.mapNotableFields(allAvailableFields)

                    if len(notableMap)>0:
                        searchString += ' %s' % (notableMap)
                        
            else:
                e = 'Output mode %s not recognized' % (outputMode)
                logger.error(e)
                raise InvalidOutputMode(e)
                        
        else:
            logger.warn('No search parts were found. Please verify your correlationSearchJson and try again.')                    
        
        ## clean up search string 
        searchString = searchString.strip()
        
        ## initialize parses boolean
        parses = False
       
        ## if we have a positive length search string
        if len(searchString)>0:
            ## get constDedupId
            constDedupId = CustomSearchBuilder.getConstDedupId(correlationSearchJson)
            if len(constDedupId)>0:
                searchString += ' %s' % (constDedupId)
            
            ## validate search with splunk's parser
            status, contents = simpleRequest("search/parser", sessionKey=sessionKey, method='GET', getargs={'q': searchString, 'output_mode': "json"})
        
            if status.status == 200:
                parses = True
                    
        return searchString, parses

    @staticmethod
    def __print__(cs, sessionKey, title=None):
        ## sessionKey required to do anything (at this time)
        if not sessionKey:
            raise splunk.AuthenticationFailed

        inputlookup = False

        print ''
        
        if title is not None and len(title)>0:
            print '====== %s ======' % (title)

        if cs.get('datamodel', False):
            print 'datamodel:       ' + cs['datamodel']

        else:
            print 'datamodel:       '

        if 1==1:
            print 'object:          ' + CustomSearchBuilder.getObjectLineage(cs, sessionKey=sessionKey)

        if cs.get('inputlookup', False) and cs['inputlookup'].get('lookupName', False):
            inputlookup = True
            print 'inputlookup:     ' + cs['inputlookup']['lookupName']
            print 'timeFilter:      ' + CustomSearchBuilder.getSearchBasedTimeFilters(cs)

        else:
            print 'inputlookup:     '
            print 'timeFilter:      '

        if 1==1:
            print 'eventFilter:     ' + CustomSearchBuilder.getEventFilter(cs)
            print 'aggregates:      ' + CustomSearchBuilder.getAggregates(cs)
            print 'splitby:         ' + CustomSearchBuilder.getSplitBy(cs)
            availableFields = CustomSearchBuilder.getAvailableFields(cs)
            print 'availableFields: ' + str(availableFields)
            print 'notableMap:      ' + CustomSearchBuilder.mapNotableFields(availableFields)

        if not inputlookup:
            print 'raw:             ' + CustomSearchBuilder.makeCorrelationSearch(cs, sessionKey=sessionKey)
            print 'tstats:          ' + CustomSearchBuilder.makeCorrelationSearch(cs, sessionKey=sessionKey)
            print 'inputlookup:     '

        else:
            print 'raw:             '
            print 'tstats:          '
            print 'inputlookup:     ' + CustomSearchBuilder.makeCorrelationSearch(cs, sessionKey=sessionKey)
