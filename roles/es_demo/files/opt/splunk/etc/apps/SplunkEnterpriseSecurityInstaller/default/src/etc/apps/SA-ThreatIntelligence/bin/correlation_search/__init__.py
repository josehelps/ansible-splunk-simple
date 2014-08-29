import csv
import os
import re
import sys
import json
import hashlib
import logging
import json

import splunk
import splunk.admin as admin
import splunk.bundle as bundle
import splunk.entity as en
import splunk.util as util
from splunk.util import normalizeBoolean as normBool

from splunk.rest import simpleRequest

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# Ensure that shortcuts can be imported.
sys.path.append(os.path.join("..", "bin"))

from shortcuts import Duration
from shortcuts import Severity
from shortcuts import NoSessionKeyException

logger = logging.getLogger('SA-ThreatIntelligence.correlation_search')

# Import the custom search builder
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "appserver", "controllers"]) )

from customsearchbuilder import *

def error(key):
    '''
    Returns an error message for a given field.
    '''

    # Dictionary of error messages
    error_descriptions = {
          'alert.suppress.fields': "One or more fields must be selected to group by.",
          'alert.suppress.period': "Aggregation window duration must be a positive integer."
          }

    if key in error_descriptions:
        return 'Invalid value for %s: %s' % (key, error_descriptions[key])
    else:
        return 'Invalid value for %s' % key


def get_users(include_realnames=False):
    """
    Get a list of the users
    """
        
    # Find the owner table
    owners_csv_file = make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "notable_owners.csv"])
    
    # The list of owners    
    owners = []
    
    # Header element to skip
    headerElement = 'owner'
    
    # Read CSV file into the list, skipping the header line.
    with open(owners_csv_file, 'rU') as f:        
        for row in csv.reader(f):
            if len(row) > 0 and row[0] != headerElement:
                if len(row) == 1:
                    owners.append((row[0], row[0]))
                elif len(row) > 1 and row[1] == '':
                    owners.append((row[0], row[0]))
                else:
                    owners.append((row[0], row[1]))

    # Sort the owners by the real-name
    def getkey(row):
        if row[0] == 'unassigned':
            return 'zzzzz'
        elif row[1] == '':
            return row[0]
        else:
            return row[1]
    
    owners = sorted(owners, key=lambda x: getkey(x))
        
    # Remove the real-names if only the users are to be included
    if include_realnames == False:
        owners_simple = []
        
        for owner in owners:
            owners_simple.append(owner[0])
        
        return owners_simple
    else:
        return owners


class CorrelationSearchMeta:
    """
    This class represents a correlation search for purposes of displaying it in a web-page.
    """
    
    REAL_TIME = 'Real time'
    SCHEDULED = 'Scheduled'
    
    TYPES = [REAL_TIME, SCHEDULED]
    
    # Base list of fields in correlationsearches.conf.
    SPEC_FIELDS = {'default_owner', 'default_status', 'description', 
        'drilldown_name', 'drilldown_search', 'rule_description', 'rule_name',
        'rule_title', 'search', 'security_domain', 'severity'}
    
    def __init__(self, name, rule_name, typ, enabled, next_scheduled_time=None, domain=None, supports_realtime=None, search=None):
        self.name                = name
        self.rule_name           = rule_name
        self.type                = typ
        self.enabled             = enabled
        self.next_scheduled_time = next_scheduled_time
        self.domain              = domain
        self.supports_realtime   = supports_realtime
        self.search              = search

    @staticmethod
    def get_search_type(settings):
        """
        Determine the type of the search by evaluating the dispatch times to see if a real-time specifier was used.
        """
        
        # We'll assume the search is not real-time unless proven otherwise
        is_rt = False
        
        # Determine if the earliest or latest time parameters are real-time
        if 'dispatch.earliest_time' in settings and settings['dispatch.earliest_time'] is not None:
            
            if settings['dispatch.earliest_time'].find("rt") >= 0:
                
                is_rt = True
                
        if 'dispatch.latest_time' in settings and settings['dispatch.latest_time'] is not None:
            
            if settings['dispatch.latest_time'].find("rt") >= 0:
                is_rt = True
        
        # Return the corresponding type
        if is_rt == True:
            return CorrelationSearchMeta.REAL_TIME
        
        else:
            return CorrelationSearchMeta.SCHEDULED
    
    @staticmethod
    def get_next_scheduled_time(settings):
        """
        Determine when the search is going to run next.
        """
        if 'next_scheduled_time' in settings:
            # Return the next scheduled time
            return settings['next_scheduled_time']
        
        else:
            return ''

    @staticmethod
    def get_security_domain(alert):
        """
        Get security domain of search
        """
        return (alert.properties.get('security_domain') or '').capitalize()
 
    @staticmethod
    def get_rule_name(alert):
        """
        Get user-friendly name of search
        """
        return alert.properties.get('rule_name', None) or alert.name
    
    @staticmethod
    def removeFromCorrelationSearchCache(name, correlation_search_cache=None):
        
        # Load the cache
        if correlation_search_cache is None:
            correlation_search_cache = CorrelationSearchMeta.loadCorrelationSearchCache()
            
        # Remove the item
        try:
            del correlation_search_cache[name]
            
            CorrelationSearchMeta.updateCorrelationSearchCache([], correlation_search_cache, force_save=True)
            
            return True
        except KeyError:
            return False

    @staticmethod
    def loadCorrelationSearchCache():
        
        f = None
        
        try:
            f = open(make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "correlationsearchmeta.csv"]), "r")
            
            reader = csv.DictReader(f, lineterminator='\n')
            
            correlation_searches = {}
                     
            # Don't use a cache that doesn't have the search_sha1 field. See SOLNESS-5076.
            if 'search_sha1' not in reader.fieldnames:
                logger.info("Cache does not have the search_sha1")
                return {}
            
            for row in reader:
                correlation_searches[row['name']] = row
            
            return correlation_searches
        
        except Exception:
            return {}
        
        finally:
            if f is not None:
                f.close()
    
    @staticmethod
    def updateCorrelationSearchCache(correlation_searches, correlation_search_cache=None, clear=False, force_save=False):
        """
        Update the cache of correlation search meta-data.
        
        Arguments:
        correlation_searches -- An array of CorrelationSearchMeta instances
        correlation_search_cache -- A dictionary (with the key being the name) of 
        """
        
        # Load the cache
        if correlation_search_cache is None and clear != True:
            correlation_search_cache = CorrelationSearchMeta.loadCorrelationSearchCache()
        elif clear == True:
            correlation_search_cache = {}
            
        # Track whether a save is necessary
        updated = force_save
            
        # Update the cache
        for correlation_search in correlation_searches:
            m = hashlib.sha1()
            m.update(correlation_search.search)
            search_digest = m.hexdigest()
            
            if not(correlation_search.name in correlation_search_cache) or correlation_search_cache[correlation_search.name].get('search_sha1', None) != search_digest:
                correlation_search_cache[correlation_search.name] = {'name': correlation_search.name, 'search_sha1': search_digest, 'supports_realtime': correlation_search.supports_realtime}
                updated = True
            
            #print "name=%s, cache_miss=%r, updating=%r, updated=%r" % (correlation_search.name, not(correlation_search.name in correlation_search_cache), not(correlation_search.name in correlation_search_cache) or correlation_search_cache[correlation_search.name]['search_sha1'] != search_digest, updated)
        
        if not updated and not clear:
            return False
            
        # Write out the file
        with open( make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "correlationsearchmeta.csv"]), "w") as f:
            
            writer = csv.DictWriter(f, ["name", "search_sha1", "supports_realtime"], lineterminator='\n')
            writer.writeheader()
            
            # Save each entry
            for data in correlation_search_cache.values():
                writer.writerow(data)
        
        return True

    @staticmethod
    def get_correlation_searches(offset=-1, count=-1, sort_by=None, session_key=None, show_rt_only=False, return_total_count=False, ignore_cache=False):
        """
        Returns a list of correlation searches wrapped in a CorrelationSearchMeta object.
        Security domain and rule name are not stored in the saved search object,
        so we have to issue a second REST call to get them from the correlation search 
        endpoint.
        """
        
        searchesDict = en.getEntities(CorrelationSearch.SAVED_SEARCHES_REST_URL,
                                      namespace  = CorrelationSearch.DEFAULT_NAMESPACE,
                                      owner      = CorrelationSearch.DEFAULT_OWNER,
                                      sessionKey = session_key,
                                      count      = -1)

        alertsDict   = en.getEntities(CorrelationSearch.CORRELATION_SEARCHES_REST_URL,
                                      namespace  = CorrelationSearch.DEFAULT_NAMESPACE,
                                      owner      = CorrelationSearch.DEFAULT_OWNER,
                                      sessionKey = session_key,
                                      count      = -1) 

        correlation_searches = []
        
        if ignore_cache:
            cached_correlation_search_info = {}
        else:
            cached_correlation_search_info = CorrelationSearchMeta.loadCorrelationSearchCache()
        
        # Process each search
        for stanza, settings in searchesDict.items():
            
            ## get the search_name
            search_name = stanza
            alert       = alertsDict.get(stanza, None)
            
            if count > 0 and len(correlation_searches) >= count:
                break
            
            if alert is not None:
                
                ## If we are not supposed to return all of the entries, then keep looping until we start at the offset
                if offset > 0:
                    offset = offset - 1
                    continue
                
                ## get the search_type
                search_type = CorrelationSearchMeta.get_search_type(settings)
                
                ## Skip this one if we are only looking for RT searches
                if show_rt_only and search_type != CorrelationSearchMeta.REAL_TIME:
                    continue
                
                ## get the search status (enabled/disabled)
                enabled = CorrelationSearch.is_search_enabled(settings)
                
                ## get the next_scheduled_time
                next_scheduled_time = CorrelationSearchMeta.get_next_scheduled_time(settings)

                ## get the user-friendly name
                rule_name = CorrelationSearchMeta.get_rule_name(alert)

                ## get the security domain
                security_domain = CorrelationSearchMeta.get_security_domain(alert)

                ## If the search has a search spec then parse it
                search_spec_json = None
                if alert['search'] is not None:
                    
                    ## Parse the search JSON and see if RT is possible
                    try:
                        search_spec_json = json.loads(alert['search'])
                    except ValueError:
                        pass

                ## Determine if the search is streaming (can be executed in real-time)
                try:
                    supports_realtime = CorrelationSearch.supports_realtime(settings, search_spec_json, session_key, cached_correlation_search_info, name=stanza)
                except Exception as e:
                    # Log that this search could not be parsed
                    logger.warn(str(e))
                    supports_realtime = None

                ## populate the search
                correlation_search = CorrelationSearchMeta(search_name, rule_name, search_type, enabled, next_scheduled_time, security_domain, supports_realtime, settings['search'])
                
                ## append to the list
                correlation_searches.append(correlation_search)
        
        # Update the correlation search cache
        if not ignore_cache:
            CorrelationSearchMeta.updateCorrelationSearchCache(correlation_searches, cached_correlation_search_info)
                
        # Return the list of searches
        if return_total_count:
            return correlation_searches, len(alertsDict.keys())
        else:
            return correlation_searches


class CorrelationSearch:
    """
    Represents a correlation search
    """

    SAVED_SEARCHES_REST_URL         = '/saved/searches/'
    CORRELATION_SEARCHES_REST_URL   = '/alerts/correlationsearches/'
    
    NOTABLE_EVENT_INDEX             = 'notable'
    
    SEGMENT_SEPARATOR               = " - "

    DEFAULT_OWNER            = 'nobody'
    DEFAULT_SECURITY_DOMAIN  = 'Threat'
    DEFAULT_NAMESPACE        = 'SA-ThreatIntelligence'
    VALID_DOMAINS            = ['Access', 'Audit', 'Endpoint', 'Identity', 'Network', 'Threat']
    VALID_NAMESPACES         = []  # cache for valid namespaces
    INVALID_NAMESPACES       = ['SA-CommonInformationModel', 'SA-Eventgen', 'SA-Utils']
    VALID_OWNERS             = []  # cache for valid owners

    # Alerting parameters for use in UI
    VALID_EMAIL_FORMATS = {'html': 'inline', 'csv': 'as CSV', 'pdf': 'as PDF'}
    # End alerting parameters
    
    def __init__(self, *args, **kwargs):
        
        self.cron_schedule          = kwargs.get('cron_schedule', None)
        self.default_owner          = kwargs.get('default_owner', None)
        self.default_status         = kwargs.get('default_status', None)
        self.description            = kwargs.get('description', None)
        self.domain                 = kwargs.get('domain', CorrelationSearch.DEFAULT_SECURITY_DOMAIN)
        self.drilldown_name         = kwargs.get('drilldown_name', None)
        self.drilldown_search       = kwargs.get('drilldown_search', None)
        self.end_time               = kwargs.get('end_time', None)
        self.enabled                = kwargs.get('enabled', True)
        self.name                   = kwargs.get('name', None)
        self.namespace              = kwargs.get('namespace', CorrelationSearch.DEFAULT_NAMESPACE)
        self.owner                  = kwargs.get('owner', CorrelationSearch.DEFAULT_OWNER)
        self.rule_description       = kwargs.get('rule_description', None)
        self.rule_title             = kwargs.get('rule_title', None)
        self.search                 = kwargs.get('search', None)
        self.search_spec            = kwargs.get('search_spec', None)
        self.severity               = Severity.from_readable_severity(kwargs.get('severity', "unknown"))
        self.sid                    = kwargs.get('sid', None)
        self.start_time             = kwargs.get('start_time', None)

        if self.sid is not None:
            # This may be an existing search. Namespace and owner get loaded in get_rest_info
            # instead of here, since we need to have the data for static methods as well.
            self.namespace = None
            self.owner     = None

        # Throttling parameters apply to ALL alert actions.
        # Note: aggregate_duration is a Splunk time specifier, so we force the conversion.
        self.aggregate_duration     = str(kwargs.get('aggregate_duration', ''))
        self.group_by               = kwargs.get('group_by', None)

        # Summary index alert action parameters.
        # Default action is to create notable event.
        self.summary_index_action_enabled = util.normalizeBoolean(kwargs.get('summary_index_action_enabled', True))

        # Email alert action parameters
        self.email_action_enabled   = util.normalizeBoolean(kwargs.get('email_isenabled', None))
        self.email_format           = kwargs.get('email_format', None)
        self.email_sendresults      = util.normalizeBoolean(kwargs.get('email_sendresults', None))
        self.email_subject          = kwargs.get('email_subject', None)
        self.email_to               = kwargs.get('email_to', None)

        # RSS alert action parameters
        self.rss_action_enabled     = util.normalizeBoolean(kwargs.get('rss_isenabled', None))
        
        # Script alert action parameters
        self.script_action_enabled  = util.normalizeBoolean(kwargs.get('script_isenabled', None))
        self.script_filename        = kwargs.get('script_filename', None)

        # Risk alert action parameters
        self.risk_action_enabled    = util.normalizeBoolean(kwargs.get('risk_action_enabled', None))
        self.risk_score             = kwargs.get('risk_score', None)
        self.risk_object            = kwargs.get('risk_object', None)
        self.risk_object_type       = kwargs.get('risk_object_type', None)

    @staticmethod
    def is_search_enabled(settings):
        """
        Determine if the given search is enabled
        """
        
        # Get the disabled flag
        if 'disabled' in settings:
            return not util.normalizeBoolean(settings['disabled'], False)
        
        else:
            return False
        
    @staticmethod
    def supports_realtime(settings, search_spec_json, session_key, cached_correlation_search_info=None, name=None):
        """
        Determine if the given search supports streaming.
        """
        
        # If a search_spec is included then use the custom search builder to see if it can be converted
        if search_spec_json is not None and "searches" in search_spec_json:
            return CustomSearchBuilder.isRTPossible(search_spec_json)
        
        if cached_correlation_search_info and name in cached_correlation_search_info:
            return normBool(cached_correlation_search_info[name]['supports_realtime'])
        
        # Prepend "search" unless the search starts with a pipe
        search_prepend = ""
        
        if settings['search'].strip()[0] != "|":
            search_prepend = "search "
        
        status, contents = simpleRequest("search/parser", sessionKey=session_key, method='GET', getargs={'q': search_prepend + settings['search'], 'output_mode': "json"})
        
        if status.status != 200:
            raise Exception('Failed to parse the search=' + search_prepend + settings['search'])
        
        else:
            search_meta = json.loads(contents)
            
            commands = search_meta.get('commands', [])
            
            # If the first command is a search, then verify nothing else is generating
            anyGeneratingInStreamingPipeline = any([c['isGenerating'] and c['pipeline'] == 'streaming' and c['command'] != 'search' for c in commands])
            anyGeneratingInReportingPipeline = any([c['isGenerating'] and c['pipeline'] == 'report' for c in commands])
            
            if commands[0]['command'] == 'search':
                return not anyGeneratingInStreamingPipeline
            else:
                return not anyGeneratingInReportingPipeline
            
    @staticmethod
    def enable(search_name, session_key=None):
        """
        Enable the given search.
        """
        
        return CorrelationSearch.set_status(search_name, True, session_key)
    
    @staticmethod
    def disable(search_name, session_key=None):
        """
        Disable the given search.
        """
        
        return CorrelationSearch.set_status(search_name, False, session_key)
    
    @staticmethod
    def set_status(search_name, enable, session_key=None):
        """
        Enables/disable the given search. returns true if the search was correctly disabled.
        """
        # Create the basic search
        search = CorrelationSearch(sid=search_name)
        
        # Get session key and other information necessary to access the REST endpoint
        session_key, namespace, owner = search.get_rest_info(session_key, None, None)

        # Get the appropriate entity
        entity = en.getEntity(CorrelationSearch.SAVED_SEARCHES_REST_URL, search_name, namespace=namespace, owner=owner, sessionKey=session_key)
        
        # Disable/enable the search
        entity['disabled'] = not enable
        en.setEntity(entity, sessionKey=session_key)
        
        return True

    @staticmethod
    def getGroupByAsList(fields):
        """
        Set the list to group by. If a string is provided, then it will be converted to a list.
        """
        
        if fields is not None:

            if isinstance(fields, list) and len(fields) > 0:
                return fields
            elif isinstance(fields, basestring) and len(fields) > 0:
                return [str.strip(i) for i in str(fields).split(",")]
            
        return []
    
    def isRealtime(self):
        """
        Determines if the given correlation search is real-time.
        """
        if (self.start_time is not None and self.start_time.find("rt") >= 0) or (self.end_time is not None and self.end_time.find("rt") >= 0):
            return True
        else:
            return False

    @staticmethod
    def __refresh_savedsearches__(session_key=None):
        en.refreshEntities('properties/savedsearches', sessionKey=session_key)

    @staticmethod
    def __get_session_key__(session_key=None, thrown_exception=True):
        
        # Try to get the session key if not provided
        if session_key is None:
            import splunk
            session_key, sessionSource = splunk.getSessionKey(return_source=True)
        
        # Do not continue if we could not get a session key and the caller wants us to thrown an exception
        if session_key is None and thrown_exception:
            raise NoSessionKeyException("Could not obtain a session key")
        
        # Return the session key
        return session_key

    @staticmethod
    def load(sid, session_key=None, namespace=None, owner=None):
        """
        Load the search with the given name.
        """
        
        # Create the basic search
        search = CorrelationSearch(sid=sid)
        
        # Get the session key and other information necessary to access the REST endpoint
        session_key, namespace, owner = search.get_rest_info(session_key, namespace, owner)
        #session_key = search.__get_session_key__(session_key)

        # Load the information from savedsearches.conf
        search.load_savedsearches_conf(session_key, namespace, owner)
        
        # Load the information from correlationsearches.conf
        search.load_correlationsearches_conf(session_key, namespace, owner)
        
        # Return the resulting search
        return search

    @staticmethod
    def validate_duration_and_group_by(duration, group_by):
        
        # Make sure that:
        #   1) If duration is provided, then at least one group-by field is defined
        if (duration is not None and duration > 0) and group_by is not None and len(group_by) == 0:
            raise ValueError(error('alert.suppress.fields'))
        
        #   2) If a group-by was provided then the duration is not zero
        elif (duration <= 0 or duration is None) and group_by is not None and len(group_by) > 0:
            raise ValueError(error('alert.suppress.fields'))

    def load_savedsearches_conf(self, session_key=None, namespace=None, owner=None):
        """
        Configures the given saved search with the parameters loaded from the related savedsearches.conf
        """
        
        # Refresh savedsearches.conf
        CorrelationSearch.__refresh_savedsearches__(session_key)

        # Get the saved search info
        saved_search            = en.getEntity(CorrelationSearch.SAVED_SEARCHES_REST_URL, self.sid, namespace=namespace, owner=owner, sessionKey=session_key)
        
        self.enabled            = CorrelationSearch.is_search_enabled(saved_search)
        self.start_time         = saved_search.get('dispatch.earliest_time')
        self.end_time           = saved_search.get('dispatch.latest_time')
        self.search             = saved_search.get('search')
        self.cron_schedule      = saved_search.get('cron_schedule')

        # Load summary index alert action parameters.
        self.summary_index_action_enabled = util.normalizeBoolean(saved_search.get('action.summary_index', None))

        # Load email alert action parameters
        self.email_action_enabled = util.normalizeBoolean(saved_search.get('action.email', None))
        self.email_sendresults    = util.normalizeBoolean(saved_search.get('action.email.sendresults', None))
        self.email_to             = saved_search.get('action.email.to', None)
        self.email_format         = saved_search.get('action.email.format', None)
        self.email_subject        = saved_search.get('action.email.subject', None)
        
        # Load rss alert action parameters
        self.rss_action_enabled    = util.normalizeBoolean(saved_search.get('action.rss', None))
        self.script_action_enabled = util.normalizeBoolean(saved_search.get('action.script', None))
        self.script_filename       = saved_search.get('action.script.filename', None)

        # Load risk alert action parameters
        self.risk_action_enabled = util.normalizeBoolean(saved_search.get('action.risk', None))
        self.risk_score          = saved_search.get('action.risk._risk_score', None)
        self.risk_object         = saved_search.get('action.risk._risk_object', None)
        self.risk_object_type    = saved_search.get('actions.risk._risk_object_type', None)
        
        # Load app and owner context
        self.namespace           = saved_search.get('eai:acl').get('app')
        self.owner               = saved_search.get('eai:acl').get('owner')
        
        # Load aggregation parameters
        self.group_by            = CorrelationSearch.getGroupByAsList(saved_search.get('alert.suppress.fields', None))
        
        # Set the aggregation to an empty string by default which indicates that no throttling is to be done
        self.aggregate_duration = Duration.duration_from_readable(saved_search.get('alert.suppress.period', ''))

    def load_correlationsearches_conf(self, session_key=None, namespace=None, owner=None):
        """
        Configures the given correlation search with the parameters loaded from the related correlationsearches.conf
        """
        
        # Get the saved search info
        try:
            corr_search = en.getEntity(CorrelationSearch.CORRELATION_SEARCHES_REST_URL, self.sid, namespace=namespace, owner=owner, sessionKey=session_key)
            
            self.description      = corr_search['description']
            self.severity         = corr_search['severity']
            self.default_status   = corr_search['default_status']
            self.default_owner    = corr_search['default_owner']
            self.domain           = corr_search['security_domain']
            self.drilldown_search = corr_search['drilldown_search']
            self.drilldown_name   = corr_search['drilldown_name']
            self.name             = corr_search['rule_name']
            self.rule_title       = corr_search['rule_title']
            self.rule_description = corr_search['rule_description']
            self.search_spec      = corr_search['search']
            
        except splunk.ResourceNotFound:
            pass

    def validate_namespace(self, session_key, namespace=None):
        '''
        Return the namespace of the current search, or the default.
        Raises an exception if an invalid namespace is specified.
        '''

        if not self.VALID_NAMESPACES:
            # Cache value to cut down on REST calls.
            self.VALID_NAMESPACES = CorrelationSearch.get_valid_namespaces(session_key)

        if namespace is None or namespace == '' or len(namespace) == 0:
            namespace = CorrelationSearch.DEFAULT_NAMESPACE
        elif namespace in self.VALID_NAMESPACES:
            pass
        else:
            raise Exception('Unable to load or save search: Invalid application specified (%s).' % (namespace))

        return namespace

    def validate_owner(self, session_key, owner=None):
        '''
        Return the owner of the current search, or the default.
        Raises an exception if an invalid owner is specified.
        '''

        if not self.VALID_OWNERS:
            # Cache value to cut down on REST calls.
            self.VALID_OWNERS = get_users(session_key)

        if owner is None or owner == '' or len(owner) == 0:
            owner = CorrelationSearch.DEFAULT_OWNER
        elif owner in self.VALID_OWNERS or owner == 'nobody':
            pass
        else:
            raise Exception('Unable to load or save search: Invalid owner specified.')

        return owner

    def get_rest_info(self, session_key=None, namespace=None, owner=None):
        """
        Returns a session key, namespace and owner (in that order). The namespace and owner will be
        populated with default values if they do not have a value already.
        """

        # Try to get the session key if not provided
        session_key = CorrelationSearch.__get_session_key__(session_key)
        
        # If this is an existing search, get the namespace and owner
        if self.sid:
            try:
                saved_search      = en.getEntity(CorrelationSearch.SAVED_SEARCHES_REST_URL, self.sid, sessionKey=session_key)
                namespace         = saved_search.get('eai:acl').get('app')
                #owner             = saved_search.get('eai:acl').get('owner')
            except Exception:
                pass

        # Validate the owner and namespace
        namespace = self.validate_namespace(session_key, namespace)
        #owner     = self.validate_owner(session_key, owner)

        # Force user to "nobody" to permit role-based editing.
        owner = 'nobody'

        self.namespace = namespace
        self.owner     = owner
        
        return session_key, namespace, owner
    
    def setup_id(self):
        """
        Prepare the id if it is not yet been created
        """
        
        # Setup the rule id if it is not defined yet
        if self.sid is None and self.domain is not None and self.name is not None:
            self.sid = self.domain + CorrelationSearch.SEGMENT_SEPARATOR + self.name + CorrelationSearch.SEGMENT_SEPARATOR + "Rule"
        elif self.sid is None and (self.domain is not None and self.name is not None):
            raise Exception("The id of the correlation search is none and cannot be constructed since both domain and name must be defined (%s, %s) respectively" % (self.domain, self.name))

    def save(self):
        """
        Save the correlation search.
        """
        
        # Setup the id if it is not defined yet
        self.setup_id()

        # Get the session key and other information necessary to access the REST endpoint
        session_key, namespace, owner = self.get_rest_info(None, self.namespace, self.owner)

        # Perform the save against the correlation searches endpoint.
        if self.save_correlationsearches_conf(session_key, namespace, owner):
            # Perform the save against the savedsearches endpoint
            # Note: The saved searches entry needs to be saved last since this 
            # will cause Splunk to kick off the search.
            self.save_savedsearches_conf(session_key, namespace, owner)

    @staticmethod
    def none_to_default(value, default=""):
        if value is None:
            return default
        else:
            return value

    @staticmethod
    def blank_to_none(value):
        if value is None:
            return None
        elif len(str(value).strip()) == 0:
            return None

    @staticmethod
    def get_valid_namespaces(session_key):
        '''
        Return a list of the valid namespaces for this Splunk instance.
        Valid namespaces for correlation searches must begin with (DA|SA).
        Static so this can be called in Mako template to populate a dropdown list.
        '''

        rx       = re.compile('^(DA|SA)-', re.IGNORECASE)
        apps     = en.getEntities('/apps/local/', sessionKey=session_key, count=-1)
        excludes = CorrelationSearch.INVALID_NAMESPACES
        return [i for i in apps if (rx.match(i) and not i in excludes)]

    def save_correlationsearches_conf(self, session_key=None, namespace=None, owner=None):
        """
        Save the correlationsearches.conf
        """
        
        # Setup the id if it is not defined yet
        self.setup_id()

        # Is is_new is not defined, then see if it exists already
        corr_search = None
        is_new = False
        
        try:
            corr_search = en.getEntity(CorrelationSearch.CORRELATION_SEARCHES_REST_URL, self.sid, namespace=namespace, owner=owner, sessionKey=session_key)
        except splunk.ResourceNotFound:
            is_new = True
        
        # If new, then create a new entry
        if is_new:
            corr_search = en.getEntity(CorrelationSearch.CORRELATION_SEARCHES_REST_URL, "_new", namespace=namespace, owner=owner, sessionKey=session_key)
            corr_search.owner = CorrelationSearch.DEFAULT_OWNER  # Make sure to force the owner to nobody, otherwise, Splunk will make the entry private
            corr_search['name'] = self.sid
            
        # If existing, then edit the current entry
        else:
            corr_search = en.getEntity(CorrelationSearch.CORRELATION_SEARCHES_REST_URL, self.sid, namespace=namespace, owner=owner, sessionKey=session_key)
        
        # rule name is always included (this forces creation of a correlationsearches.conf stanza for all custom searches).
        corr_search['description']      = CorrelationSearch.none_to_default(self.description)
        corr_search['rule_name']        = CorrelationSearch.none_to_default(self.name)
        corr_search['search']           = CorrelationSearch.none_to_default(self.search_spec)
        if self.summary_index_action_enabled:
            # Update the correlation search with the relevant fields - notable event search
            corr_search['default_owner']    = CorrelationSearch.none_to_default(self.default_owner)
            corr_search['default_status']   = CorrelationSearch.none_to_default(self.default_status)
            corr_search['drilldown_name']   = CorrelationSearch.none_to_default(self.drilldown_name)
            corr_search['drilldown_search'] = CorrelationSearch.none_to_default(self.drilldown_search)
            corr_search['security_domain']  = CorrelationSearch.none_to_default(self.domain).lower()
            corr_search['severity']         = Severity.from_readable_severity(self.severity)
            corr_search['rule_description'] = CorrelationSearch.none_to_default(self.rule_description)
            corr_search['rule_title']       = CorrelationSearch.none_to_default(self.rule_title)
        else:
            # Update the correlation search with the relevant fields - risk search
            for field in CorrelationSearchMeta.SPEC_FIELDS - {'description', 'rule_name', 'search'}:
                del corr_search.properties[field]
        
        # Set the entity
        return en.setEntity(corr_search, sessionKey=session_key)

    def remove_rt_from_time(self, search_time):
        
        strip_rt_regex = re.compile("(rt)?(.*)")
        
        m = strip_rt_regex.search(search_time)
        
        if m is not None:
            return m.groups()[1]
        else:
            return search_time

    @staticmethod
    def change_to_realtime(search_name, session_key=None):
        """
        Change the given search to real-time.
        """
        
        # Create the basic search
        search = CorrelationSearch.load(sid=search_name, session_key=session_key)
        
        search.make_realtime()
        search.save()
        
    @staticmethod
    def change_to_non_realtime(search_name, session_key=None):
        """
        Change the given search to scheduled.
        """
        
        # Create the basic search
        search = CorrelationSearch.load(sid=search_name, session_key=session_key)
        
        search.make_non_realtime()
        search.save()

    def isUsingSearchSpec(self):
        if self.search_spec is not None and 'searches'  in self.search_spec:
            return True
        else:
            return False

    def update_search_from_spec(self, session_key=None):
        
        # Determine if a search_spec is being used
        if not self.isUsingSearchSpec():
            return
        
        # Parse the search spec
        search_spec_parsed = json.loads(self.search_spec)

        # Update the times accordingly
        if 'inputlookup' in search_spec_parsed['searches'][0]:
            # Inputlookup search.
            # Retain earliest/latest in spec if present
            # Reset dispatch.earliest_time and dispatch.latest_time.
            self.start_time = ''
            self.end_time = '+0s'
        elif len(search_spec_parsed['searches']) > 1:
            # Multimode datamodel search.
            # Retain earliest/latest in spec if present.
            # Reset dispatch.earliest_time and dispatch.latest_time.
            self.start_time = ''
            self.end_time = '+0s'
        elif len(search_spec_parsed['searches']) == 1:
            # Single-mode data model search.
            # dispatch.earliest_time and dispatch.latest_time are used.
            # earliest/latest set to value of the above.
            search_spec_parsed['searches'][0]['earliest'] = self.start_time
            search_spec_parsed['searches'][0]['latest'] = self.end_time
        
        # Update the alert suppress fields
        if self.aggregate_duration is not None and len(str(self.aggregate_duration)) > 0:
            search_spec_parsed['alert.suppress'] = 1
            search_spec_parsed['alert.suppress.fields'] = self.group_by
        else:
            search_spec_parsed['alert.suppress'] = 0
            search_spec_parsed['alert.suppress.fields'] = []
        
        # Update the raw_search
        self.search, parses = CustomSearchBuilder.makeCorrelationSearch(search_spec_parsed, sessionKey=session_key)
        logger.warn("search_spec converted, search= " + self.search)

    def make_non_realtime(self):
        """
        Changes the correlation search from a real-time search to a scheduled one.
        """
        
        self.start_time = self.remove_rt_from_time(self.start_time)
        self.end_time = self.remove_rt_from_time(self.end_time)
        
    def make_realtime(self):
        """
        Changes the correlation search from a scheduled search to a real-time one.
        """
        
        if not self.isRealtime():
        
            if self.start_time is not None and not self.start_time.startswith("rt"):
                self.start_time = "rt" + self.start_time
                
            # If blank, add a start time because Splunk requires one for rt
            elif self.start_time is None:
                self.start_time = "rt"
                
            if self.end_time is not None and not self.end_time.startswith("rt"):
                self.end_time = "rt" + self.end_time
                
            # If blank, add a end time because Splunk requires one for rt
            elif self.end_time is None:
                self.end_time = "rt"

    def save_savedsearches_conf(self, session_key=None, namespace=None, owner=None):
        """
        Save the savedsearches.conf
        """
        
        # Setup the id if it is not defined yet
        self.setup_id()
        saved_search = None
        
        try:
            # If existing, then edit the current entry
            saved_search = en.getEntity(CorrelationSearch.SAVED_SEARCHES_REST_URL, self.sid, namespace=namespace, owner=owner, sessionKey=session_key)
        except splunk.ResourceNotFound:
            # Create a new entry
            saved_search = en.getEntity(CorrelationSearch.SAVED_SEARCHES_REST_URL, "_new", namespace=namespace, owner=owner, sessionKey=session_key)
            saved_search.owner = CorrelationSearch.DEFAULT_OWNER  # Make sure to force the owner to nobody, otherwise, Splunk will make the entry private
            saved_search['name'] = self.sid

        # If a duration is provided but not a group-by, then assume we are to group-by 'const_dedup_id'
        if self.aggregate_duration is not None and len(str(self.aggregate_duration)) > 0 and len(CorrelationSearch.getGroupByAsList(self.group_by)) == 0:
            self.group_by = ['const_dedup_id']
            
        # Now re-make the search string if a search spec is being used
        self.update_search_from_spec(session_key)
        
        # Make sure that the duration and group-by fields are set right
        CorrelationSearch.validate_duration_and_group_by(Duration.duration_from_readable(self.aggregate_duration), CorrelationSearch.getGroupByAsList(self.group_by))
        
        # Determine if the search is real-time
        real_time = self.isRealtime()

        # Update the saved search with the relevant fields
        saved_search['dispatch.earliest_time'] = self.start_time
        saved_search['dispatch.latest_time'] = self.end_time
        saved_search['search'] = self.search
        saved_search['cron_schedule'] = self.cron_schedule
        saved_search['is_scheduled'] = 1

        # General alerting parameters.
        saved_search['alert.digest_mode'] = 1
        saved_search['alert.track'] = 0
                
        # Enable the alert suppression if we are using it; otherwise, clear our the related fields
        if self.group_by is None or len(self.group_by) == 0 or self.aggregate_duration == 0 or self.aggregate_duration == None:
            saved_search['alert.suppress'] = 0
            saved_search['alert.suppress.fields'] = ""
            saved_search['alert.suppress.period'] = ""
        else:
            saved_search['alert.suppress'] = 1
            # Convert the group by fields list to a string
            saved_search['alert.suppress.fields'] = ",".join(CorrelationSearch.getGroupByAsList(self.group_by))
            saved_search['alert.suppress.period'] = Duration.duration_from_readable(self.aggregate_duration)

        # Default alert action set.
        actions = []

        # Notable event alert action parameters
        if self.summary_index_action_enabled:
            actions.append('summary_index')
            saved_search['action.summary_index._name'] = CorrelationSearch.NOTABLE_EVENT_INDEX
            saved_search['action.summary_index.ttl'] = '1p'
        else:
            # Set no options. Since the action will be disabled in the local conf,
            # other default params may linger if set in default, but should be innocuous.
            pass

        # Email alert action parameters
        if self.email_action_enabled:
            actions.append('email')
            saved_search['action.email.subject']     = self.email_subject
            saved_search['action.email.to']          = self.email_to
            if self.email_sendresults:
                saved_search['action.email.sendresults']  = 1
                # SOLNESS-5050: Inline results use default format for now, because 
                # "email_format" is overloaded, so we need another parameter.
                if self.email_format == 'html':
                    saved_search['action.email.inline']  = 1
                    saved_search['action.email.sendcsv']  = 0
                    saved_search['action.email.sendpdf']  = 0
                elif self.email_format == 'csv':
                    saved_search['action.email.inline']  = 0
                    saved_search['action.email.sendcsv']  = 1
                    saved_search['action.email.sendpdf']  = 0
                elif self.email_format == 'pdf':
                    saved_search['action.email.inline']  = 0
                    saved_search['action.email.sendcsv']  = 0
                    saved_search['action.email.sendpdf']  = 1
            else:
                saved_search['action.email.sendresults'] = 0
                saved_search['action.email.inline']  = 0
                saved_search['action.email.sendcsv']  = 0
                saved_search['action.email.sendpdf']  = 0

        else:
            # Set no options. Since the action will be disabled in the local conf,
            # other default params may linger if set in default, but should be innocuous.
            pass

        # Risk alert action parameters.
        if self.risk_action_enabled:
            actions.append('risk')
            saved_search['action.risk._risk_object'] = self.risk_object
            saved_search['action.risk._risk_object_type'] = self.risk_object_type
            saved_search['action.risk._risk_score'] = self.risk_score
        else:
            # Set no options. Since the action will be disabled in the local conf,
            # other default params may linger if set in default, but should be innocuous.
            pass

        # RSS alert action parameters.
        if self.rss_action_enabled:
            actions.append('rss')
        else:
            # Set no options. Since the action will be disabled in the local conf,
            # other default params may linger if set in default, but should be innocuous.
            pass

        # Script alert action parameters.
        if self.script_action_enabled:
            actions.append('script')
            saved_search['action.script.filename'] = self.script_filename
        else:
            # Set no options. Since the action will be disabled in the local conf,
            # other default params may linger if set in default, but should be innocuous.
            pass

        saved_search['actions'] = ','.join(actions)
        if actions:
            saved_search['alert_type'] = 'number of events'
            saved_search['alert_threshold'] = 0
            saved_search['alert_comparator'] = 'greater than'
        else:
            saved_search['alert_type'] = ''
            saved_search['alert_threshold'] = 0
            saved_search['alert_comparator'] = ''

        # Set real-time backfill for the search if it is real-time
        if real_time:
            saved_search['dispatch.rt_backfill'] = 1

        # Set the entity
        return en.setEntity(saved_search, sessionKey=session_key)

    ## get capabilities method    
    @staticmethod
    def getCapabilities4User(user=None, session_key=None):
        roles = []
        capabilities = []
        
        ## Get user info              
        if user is not None:
            userDict = en.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
        
            for stanza, settings in userDict.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            roles = val
             
        ## Get capabilities
        for role in roles:
            roleDict = en.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
            
            for stanza, settings in roleDict.items():
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key == 'imported_capabilities':
                            capabilities.extend(val)
            
        return capabilities
