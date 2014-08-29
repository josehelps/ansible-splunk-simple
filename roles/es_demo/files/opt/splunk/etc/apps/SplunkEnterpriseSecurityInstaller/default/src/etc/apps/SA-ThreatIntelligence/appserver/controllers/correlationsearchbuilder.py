import cherrypy
import csv
import sys
import logging
import os
import splunk
import splunk.entity as en
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.clilib.bundle_paths as bp

# Import the correlation search helper class
sys.path.append( os.path.join("..", "..", "bin") )
from correlation_search import CorrelationSearch

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.controllers.CorrelationSearchBuilder')

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
        
        # Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        # Get the meta-data
        domain = kwargs.get('security_domain', 'threat')
        severity = kwargs.get('severity', 'high')
        description = kwargs.get('description', '')
        name = kwargs.get('name', '')
        
        # Get the information for making the search
        """
        data_model = kwargs.get('data_model', '')
        object = kwargs.get('object', '')
        function = kwargs.get('function', '')
        attribute = kwargs.get('attribute', '')
        """
        
        search = kwargs.get('search', '')
        start_time = kwargs.get('earliest', '-24h')
        end_time = kwargs.get('latest', 'now')
        severity = kwargs.get('severity', 'unknown')
        
        if (start_time is not None and start_time.find("rt") >= 0) or (end_time is not None and end_time.find("rt") >= 0):
            cron_schedule = "*/5 * * * *"
        else:
            cron_schedule = "*/30 * * * *"

        # Make the search
        correlation_search = CorrelationSearch( name = name, domain=domain, start_time=start_time, end_time=end_time,
                                                search=search, description=description, cron_schedule=cron_schedule, severity=severity,
                                                default_status="1", default_owner=None,
                                                namespace="SA-ThreatIntelligence", rule_title="", rule_description="")
        
        correlation_search.save()
        
        """
        correlation_search = CorrelationSearch( name = name, domain=domain, start_time=start_time, end_time=end_time,
                                                        search=search, description=description, cron_schedule=cron_schedule, severity=severity,
                                                        default_status=default_status, default_owner=default_owner, drilldown_search=drilldown_search,
                                                        drilldown_name=drilldown_name, aggregate_duration=duration, group_by=group_by,
                                                        email_to=email_to, email_subject=email_subject, email_format=email_format,
                                                        email_sendresults=email_sendresults, email_isenabled=email_isenabled,
                                                        rss_isenabled=rss_isenabled, script_isenabled=script_isenabled, script_filename=script_filename,
                                                        namespace=namespace, rule_title=rule_title, rule_description=rule_description)
        """
        
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
        