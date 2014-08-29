from django.core.urlresolvers import resolve
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from debug_toolbar.panels import DebugPanel
from debug_toolbar.utils import get_name_from_obj

from urlparse import urlparse, parse_qs

class SplunkRestDebugPanel(DebugPanel):
    """
    A panel to display Splunk Requests.
    """
    name = 'SplunkRest'
    template = 'splunkdj:debug/splunk_rest.html'
    has_content = True

    def nav_title(self):
        return "Splunk REST"

    def title(self):
        return "Splunk REST"

    def url(self):
        return ''

    def process_request(self, request):
        self.request = request
        self.tracker = []
        
        if hasattr(request, 'service') and request.service:
            self.service = request.service
            self.service.enable_debug(self.tracker)
        else:
            self.service = None

    def process_response(self, request, response):
        if self.service:
            self.service.disable_debug()
        
        calls = []
        for tracked in self.tracker:
            request = tracked["request"]
            response = tracked["response"]
            
            parsed_url = urlparse(request['url'])
            
            headers = request["headers"]
            method = request["method"]
            path = parsed_url.path
            query = parse_qs(parsed_url.query)
            post = None
            body = None
            
            dict_headers = {}
            for key, value in headers:
                dict_headers[key] = value
                
            headers = dict_headers
            if headers.get("content-type", "") == "application/x-www-form-urlencoded":
                post = parse_qs(request["body"])
            else:
                body = request["body"]
            
            request = dict(
                path=path,
                method=method,
                headers=headers,   
                query=query,
                post=post,
                body=body
            )
            
            headers = {}
            for key, value in response["headers"]:
                headers[key] = value
            response["headers"] = headers
            
            time = tracked["time"]
            milliseconds = float(time.seconds * 10**6 + time.microseconds) / 1000.0
            
            calls.append(dict(request=request, response=response, time=milliseconds))
            
        self.record_stats({"rest": calls})
