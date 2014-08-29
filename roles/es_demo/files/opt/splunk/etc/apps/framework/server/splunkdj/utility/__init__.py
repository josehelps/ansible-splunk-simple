from django.core.urlresolvers import resolve
from django.conf import settings
from splunklib.client import Service
import time

def get_current_app_name(request):
    return request.app_name

def create_derived_service(old_service, owner=None, app=None):
    new_service = Service(
        host=old_service.host,
        port=old_service.port,
        scheme=old_service.scheme,
        token=old_service.token,
        owner=owner,
        app=app)
    
    # Force the same underlying HTTP binding.
    # This ensures that the debug state is preserved, which keeps things like
    # the Splunk REST debug panel working as expected with the derived service.
    new_service.http = old_service.http
    
    return new_service

def get_time_offset(t=None, dual_output=False):
    """Return offset of local zone from GMT in seconds, either at present or at time t."""
    # python2.3 localtime() can't take None
    if t is None:
        t = time.time()

    if not dual_output:
        if time.localtime(t).tm_isdst and time.daylight:
            return -time.altzone
        else:
            return -time.timezone
            
    return (-time.timezone, -time.altzone)
        
def format_local_tzoffset(t=None):
    '''
    Render the current process-local timezone offset in standard -0800 type
    format for the present or at time t.
    '''
    offset_secs = get_time_offset(t)

    plus_minus = "+"
    if offset_secs < 0:
        plus_minus = '-'
    offset_secs = abs(offset_secs)

    hours, rem_secs  = divmod(offset_secs, 3600 )   # 60s * 60m -> hours
    minutes = (rem_secs / 60)
    return "%s%0.2i%0.2i" % (plus_minus, hours, minutes)

def make_splunkweb_url(path):
    """
    Given a path on Splunkweb, create the absolute URL, taking into account
    the mount.
    
    For example:
        path = "/en-US/foo" with mount/root_endpoint as /root
        returns
        "/root/en-US/foo"
    """
    splunkweb_mount = ""
    if settings.SPLUNK_WEB_MOUNT:
        splunkweb_mount = "/%s" % settings.SPLUNK_WEB_MOUNT
        
    return "%s%s" % (splunkweb_mount, path)