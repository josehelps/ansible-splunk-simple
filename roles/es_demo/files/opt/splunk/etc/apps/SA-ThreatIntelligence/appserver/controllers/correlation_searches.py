import cherrypy
import csv
import sys
import logging, logging.handlers
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

import os
import splunk
import traceback
import urllib
import json
import splunk.entity as en
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.clilib.bundle_paths as bp

# Import the correlation search helper class
sys.path.append( os.path.join("..", "..", "bin") )
from correlation_search import CorrelationSearchMeta, CorrelationSearch
from shortcuts import Severity

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

# Setup the logger
def setup_logger():
    """
    Setup a logger for the REST handler.
    """
    
    logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.controllers.CorrelationSearchBuilder')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'correlation_search_controller.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
   
    logger.addHandler(file_handler)
   
    return logger

logger = setup_logger()


class CorrelationSearchBuilder(controllers.BaseController):
    '''Correlation search builder Controller'''

    @route('/:ping=ping')
    @expose_page(must_login=True, methods=['GET', 'POST']) 
    def ping(self, **kwargs):
        return self.render_json( {
                                  'is_available'    : '1'
                                  }, set_mime='text/plain')

    @route('/:save=save')
    @expose_page(must_login=True, methods=['POST']) 
    def save(self, **kwargs):
        """
        This handler is currently invoked by the "Save correlation search" button that is included in predictive analytics. You should be using the 'update_or_create_search' for new functionality.
        """
        
        # Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        # Get the meta-data
        domain = kwargs.get('security_domain', 'threat')
        severity = kwargs.get('severity', 'high')
        description = kwargs.get('description', '')
        name = kwargs.get('name', '')
        
        # Get the information for making the search
        search = kwargs.get('search', '')
        start_time = kwargs.get('earliest', '-24h')
        end_time = kwargs.get('latest', 'now')
        severity = kwargs.get('severity', 'unknown')
        
        if (start_time is not None and start_time.find("rt") >= 0) or (end_time is not None and end_time.find("rt") >= 0):
            cron_schedule = "*/5 * * * *"
        else:
            cron_schedule = "*/30 * * * *"

        # Make the search
        #
        # ADD SEARCH CREATION HERE...
        #
        correlation_search = CorrelationSearch( name = name, domain=domain, start_time=start_time, end_time=end_time,
                                                search=search, description=description, cron_schedule=cron_schedule, severity=severity,
                                                default_status="1", default_owner=None,
                                                namespace="SA-ThreatIntelligence", rule_title="", rule_description="")
        
        correlation_search.save()
        
        # I'm returning the info just for debugging
        return self.render_json( {
                                  'sid'             : correlation_search.sid,
                                  'earliest'        : start_time,
                                  'latest'          : end_time,
                                  'search'          : search,
                                  'security_domain' : domain,
                                  'description'     : description,
                                  'name'            : name
                                  }, set_mime='text/plain')
       
    @route('/:update_or_create_search=update_or_create_search')
    @expose_page(must_login=True, methods=['GET', 'POST']) 
    def update_or_create_search(self, sid=None, name=None, domain=None, start_time=None, end_time=None, search=None, enabled=True,
                        description=None, owner=None, cron_schedule=None, severity="unknown", default_status="new",
                        default_owner=None, drilldown_search=None, drilldown_name=None, duration=None, group_by=None,
                        email_to=None, email_subject=None, email_format=None, email_sendresults=None, email_isenabled=None,
                        rss_isenabled=None, script_isenabled=None, script_filename=None,
                        namespace=None, rule_title=None, rule_description=None, search_spec=None, summary_index_action_enabled=None,
                        risk_action_enabled=False, risk_score=None, risk_object=None, risk_object_type=None, **kwargs):
        
        # Prepare a response
        response = {}
        
        # Set the cron schedule to the run the search every 5 minutes if the search is real-time
        if (start_time is not None and start_time.find("rt") >= 0) or (end_time is not None and end_time.find("rt") >= 0):
            cron_schedule = "*/5 * * * *"
        
        # Make sure the group by is an array and convert it if it is not already
        if group_by != "" and isinstance(group_by, basestring):
            group_by = group_by.split(",")
        
        # Save the correlation search
        try:
            
            if sid is None:
                is_new = True
                correlation_search = CorrelationSearch( name=name, domain=domain, start_time=start_time, end_time=end_time,
                                                        search=search, description=description, cron_schedule=cron_schedule, severity=severity,
                                                        default_status=default_status, default_owner=default_owner, drilldown_search=drilldown_search,
                                                        drilldown_name=drilldown_name, aggregate_duration=duration, group_by=group_by,
                                                        email_to=email_to, email_subject=email_subject, email_format=email_format,
                                                        email_sendresults=email_sendresults, email_isenabled=email_isenabled,
                                                        rss_isenabled=rss_isenabled, script_isenabled=script_isenabled, script_filename=script_filename,
                                                        namespace=namespace, rule_title=rule_title, rule_description=rule_description, search_spec=search_spec,
                                                        summary_index_action_enabled=summary_index_action_enabled, risk_action_enabled=risk_action_enabled, risk_score=risk_score,
                                                        risk_object=risk_object, risk_object_type=risk_object_type)
            else:
                is_new = False
                correlation_search = CorrelationSearch( sid = sid, name=name, domain=domain, start_time=start_time, end_time=end_time,
                                                        search=search, description=description, cron_schedule=cron_schedule, severity=severity,
                                                        default_status=default_status, default_owner=default_owner, drilldown_search=drilldown_search,
                                                        drilldown_name=drilldown_name, aggregate_duration=duration, group_by=group_by,
                                                        email_to=email_to, email_subject=email_subject, email_format=email_format,
                                                        email_sendresults=email_sendresults, email_isenabled=email_isenabled,
                                                        rss_isenabled=rss_isenabled, script_isenabled=script_isenabled, script_filename=script_filename,
                                                        namespace=namespace, rule_title=rule_title, rule_description=rule_description, search_spec=search_spec,
                                                        summary_index_action_enabled=summary_index_action_enabled, risk_action_enabled=risk_action_enabled, risk_score=risk_score,
                                                        risk_object=risk_object, risk_object_type=risk_object_type)


            correlation_search.save()
            
            # Return the search ID so that the caller can know where to find this search
            response["sid"] = correlation_search.sid
            
            # Return a success message
            if is_new:
                response["message"] = "Correlation search successfully created"
            else:
                response["message"] = "Correlation search successfully saved"
            
            # Note that the item was successfully saved
            response["success"] = True

        except splunk.AuthorizationFailed:
            
            response["message"] = "You do not have permission to edit correlation searches"
            response["success"] = False            
        
        except Exception, e :
            
            tb = traceback.format_exc()
            
            response["message"] = str(e)
            response["trace"] = tb
            response["success"] = False
        
        # Return a message indicating success
        return self.render_json(response)
    
    
    @route('/:security_domains=security_domains')
    @expose_page(must_login=True, methods=['GET']) 
    def get_security_domains(self, **kwargs):
        return self.render_json(CorrelationSearch.VALID_DOMAINS)
        
    @route('/:severities=severities')
    @expose_page(must_login=True, methods=['GET']) 
    def get_severities(self, **kwargs):
        severities = Severity.getSeverities()
        return self.render_json(list(severities))

    @route('/:namespaces=namespaces')
    @expose_page(must_login=True, methods=['GET']) 
    def get_namespaces(self, **kwargs):
        namespaces = CorrelationSearch.get_valid_namespaces(cherrypy.session.get('sessionKey'))
        return self.render_json(namespaces)
    
    @route('/:email_formats=email_formats')
    @expose_page(must_login=True, methods=['GET']) 
    def get_email_formats(self, **kwargs):
        email_formats = CorrelationSearch.VALID_EMAIL_FORMATS
        return self.render_json(email_formats)
    
    @route('/:all_info=all_info')
    @expose_page(must_login=True, methods=['GET']) 
    def get_all_info(self, **kwargs):
        
        r = {}
        
        r['domains'] = CorrelationSearch.VALID_DOMAINS
        r['severities'] = list(Severity.getSeverities())
        r['namespaces'] = CorrelationSearch.get_valid_namespaces(cherrypy.session.get('sessionKey'))
        r['email_formats'] = CorrelationSearch.VALID_EMAIL_FORMATS
        
        return self.render_json(r)
    
    def smash_together_search_contents(self, corr_search_content, saved_search_content):
        return dict(saved_search_content['entry'][0]['content'].items() + corr_search_content['entry'][0]['content'].items())
    
    @route('/:get_searches=get_searches')
    @expose_page(must_login=True, methods=['GET'])
    def get_searches(self, **kwargs):
        
        # Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        # Default to JSON since that is what Javascript usually wants
        args = {}
        
        if 'output_mode' in kwargs:
            args['output_mode'] = kwargs['output_mode']
        else:
            args['output_mode'] = 'json'
            
        args['count'] = '-1'
        
        correlation_searches = CorrelationSearchMeta.get_correlation_searches(count=10000, return_total_count=False)
        
        entries = []
        
        for c in correlation_searches:
            entry = {}
            entry['name']                = c.name
            entry['rule_name']           = c.rule_name
            entry['type']                = c.type
            entry['enabled']             = c.enabled
            entry['next_scheduled_time'] = c.next_scheduled_time
            entry['supports_realtime']   = c.supports_realtime
            entry['search']              = c.search
            entry['domain']              = c.domain
            
            entries.append(entry)
        
        return self.render_json(entries)
    
    @route('/:get_search=get_search')
    @expose_page(must_login=True, methods=['GET'])
    def get_search(self, search, **kwargs):
        
        # Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        # Default to JSON since that is what Javascript usually wants
        args = {}
        
        if 'output_mode' in kwargs:
            args['output_mode'] = kwargs['output_mode']
        else:
            args['output_mode'] = 'json'
        
        try:
            serverResponse, serverContent = splunk.rest.simpleRequest('/services/alerts/correlationsearches/' + urllib.quote(search), sessionKey=session_key, getargs=args)
        except splunk.AuthenticationFailed:
            return None
        
        # Parse the JSON because we are going to add some info to it
        corr_search_content = json.loads(serverContent)
        
        # Now get the search
        try:
            serverResponse, serverContent = splunk.rest.simpleRequest('/services/saved/searches/' + urllib.quote(search), sessionKey=session_key, getargs=args)
        except splunk.AuthenticationFailed:
            return None
        
        search_content = json.loads(serverContent)
        
        combined_content = dict(search_content['entry'][0]['content'].items() + corr_search_content['entry'][0]['content'].items())
        
        corr_search_content['entry'][0]['content'] = combined_content
        
        # Make sure to change the name of the search field since both have this field
        corr_search_content['entry'][0]['content']['savedsearch'] = search_content['entry'][0]['content']['search']
        
        return self.render_json(corr_search_content)
    
    def is_sequence(self, arg):
        """
        Determine if the providing argument is a list of some sort (but not a string which can look like a list).
    
        Argument:
        arg -- The item to be tested for whether it is a list
        """
    
        return (not hasattr(arg, "strip") and
                hasattr(arg, "__getitem__") or
                hasattr(arg, "__iter__"))
    
    @route('/:disable_searches=disable_searches')
    @expose_page(must_login=True, methods=['POST'])
    def disable_searches(self, searches, **kwargs):
        
        # Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        messages = []
        
        # Handle the case where the searches list is just a string
        if not self.is_sequence( searches ):
            searches = [ searches ]
        
        # Do the work
        try:
            i = 0
            
            for s in searches:
                CorrelationSearch.disable(s)
                i = i + 1
                
            if i == 0:
                messages.append( {'severity' : 'info', 'message' : 'No correlation searches provided to disable'} )
            elif i == 1:
                messages.append( {'severity' : 'info', 'message' : 'Correlation search successfully disabled'} )
            else:
                messages.append( {'severity' : 'info', 'message' : 'Correlation searches successfully disabled'} )
            
        except Exception as e:
            messages.append( {'severity' : 'error', 'message' : 'Error occurred while modifying the Correlation search: ' + str(e)} )
        
        return self.render_json({'messages' : messages})
    
    @route('/:enable_searches=enable_searches')
    @expose_page(must_login=True, methods=['POST'])
    def enable_searches(self, searches, **kwargs):
        
        # Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        messages = []
        
        # Handle the case where the searches list is just a string
        if not self.is_sequence( searches ):
            searches = [ searches ]
        
        # Do the work
        try:
            i = 0
            
            for s in searches:
                CorrelationSearch.enable(s)
                i = i + 1
                
            if i == 0:
                messages.append( {'severity' : 'info', 'message' : 'No correlation searches provided to enable'} )
            elif i == 1:
                messages.append( {'severity' : 'info', 'message' : 'Correlation search successfully enabled'} )
            else:
                messages.append( {'severity' : 'info', 'message' : 'Correlation searches successfully enabled'} )
            
        except Exception as e:
            messages.append( {'severity' : 'error', 'message' : 'Error occurred while modifying the Correlation search: ' + str(e)} )
    
        return self.render_json({'messages' : messages})
    
    @route('/:change_searches_to_non_rt=change_searches_to_non_rt')
    @expose_page(must_login=True, methods=['POST'])
    def change_searches_to_non_rt(self, searches, **kwargs):
        
        # Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        messages = []
        
        # Handle the case where the searches list is just a string
        if not self.is_sequence( searches ):
            searches = [ searches ]
        
        # Do the work
        try:
            i = 0
            
            for s in searches:
                c_search = CorrelationSearch.load(s)
                
                if c_search.isRealtime():
                    c_search.make_non_realtime()
                    
                    if c_search.save_savedsearches_conf( session_key=session_key, namespace=c_search.namespace, owner=c_search.owner):
                        i = i + 1
                    
            if i == 0:
                messages.append( {'severity' : 'info', 'message' : 'No correlation searches provided to convert to scheduled'} )
            elif i == 1:
                messages.append( {'severity' : 'info', 'message' : 'Correlation search successfully converted to scheduled'} )
            else:
                messages.append( {'severity' : 'info', 'message' : 'Correlation searches successfully converted to scheduled'} )
            
        except Exception as e:
            messages.append( {'severity' : 'error', 'message' : 'Error occurred while modifying the Correlation search: ' + str(e)} )
        
        return self.render_json({'messages' : messages})
    
    @route('/:change_searches_to_rt=change_searches_to_rt')
    @expose_page(must_login=True, methods=['POST'])
    def change_searches_to_rt(self, searches, **kwargs):
        
        # Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        messages = []
        
        # Handle the case where the searches list is just a string
        if not self.is_sequence( searches ):
            searches = [ searches ]
        
        # Do the work
        try:
            i = 0
            
            for s in searches:
                c_search = CorrelationSearch.load(s)
                
                if not c_search.isRealtime():
                    c_search.make_realtime()
                    
                    if c_search.save_savedsearches_conf( session_key=session_key, namespace=c_search.namespace, owner=c_search.owner):
                        i = i + 1
            
            if i == 0:
                messages.append( {'severity' : 'info', 'message' : 'No correlation searches provided to convert to real-time'} )
            elif i == 1:
                messages.append( {'severity' : 'info', 'message' : 'Correlation search successfully converted to real-time'} )
            else:
                messages.append( {'severity' : 'info', 'message' : 'Correlation searches successfully converted to real-time'} )
                
        except Exception as e:
            messages.append( {'severity' : 'error', 'message' : 'Error occurred while modifying the Correlation search: ' + str(e)} )
            
        return self.render_json({'messages' : messages})