import sys
import pprint
import json
import datetime
import uuid
import urllib
import types
import traceback
from django.core.urlresolvers import reverse, resolve
from django.http import HttpResponseRedirect, Http404, HttpResponseServerError, HttpResponseNotFound
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.debug import ExceptionReporter, get_safe_settings
from django.template import TemplateDoesNotExist, Context
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.shortcuts import render
from splunkdj.decorators.render import render_to
from splunkdj.utility import make_splunkweb_url
from urlparse import urlparse

import logging
logger = logging.getLogger('spl.django.service')
error_logger = logging.getLogger('spl.django.request_error')
 
def format(value):
    """
    Format values appropriately for json.dumps:
        - Basic types will remain the same
        - Unicode will be converted to str
        - Everything else will be formatted using pprint
    """
    if value is None:
        return value
    if isinstance(value, (int, long, str, float, list, dict, tuple, bool, unicode)):
        return value
    return str(pprint.pformat(value))
    
def get_exception_info(request):   
    # We use Django's debug reporter, even though we are doing our own template.
    # This is because it has a great way of collecting all the useful info we 
    # need, so no reason not to leverage it 
    exc_info = sys.exc_info()
    reporter = ExceptionReporter(request, *exc_info)
    ctx = reporter.get_traceback_data()
    
    # This is a refactor of what the technical_500_template contains, just
    # doing the logic in Python rather than in a template. We collect all this
    # information so that we can log it.
    exception_type = ctx['exception_type'] if 'exception_type' in ctx else "No exception supplied"
    exception_value = ctx['exception_value'] if 'exception_value' in ctx else "No exception supplied"
    django_version = ctx["django_version_info"]
    python_executable = ctx['sys_executable']
    python_version = ctx['sys_version_info']
    python_path = ctx['sys_path']
    server_time = str(ctx['server_time'])
    unicode_hint = None
    if 'unicode_hint' in ctx:
        unicdoe_hint = ctx['unicode_hint']
    last_frame = None
    if 'lastframe' in ctx:
        frame_info = ctx['lastframe']
        last_frame = "%s in %s, line %s" % (frame_info['filename'], frame_info['function'], frame_info['lineno'])
    loaders = []
    if 'template_does_not_exist' in ctx and 'loader_debug_info' in ctx and ctx['loader_debug_info']:
        for loader in ctx['loader_debug_info']:
            loader_info = {"name": loader['loader'], "templates": []}
            for tmpl in loader['templates']:
                loader_info['templates'].append({"file": tmpl['name'], "exists": tmpl['exists']})
            loaders.append(loader_info)
    template_errors = None
    if 'template_info' in ctx and ctx['template_info']:
        template_info = ctx['template_info']
        template_errors = {
            "name": template_info['name'],
            "line": template_info['line'],
            "message": template_info['message']
        }
    exception_info = []
    if 'frames' in ctx:
        frames = ctx['frames']
        for frame in frames:
            frame_info = {
                "filename": frame['filename'],
                "function": frame['function'],
                "line": frame['lineno'],
                "context_line": frame['context_line'],
                "vars": []
            }
            if 'vars' in frame:
                for var in frame['vars']:
                    frame_info['vars'].append({
                        "variable": str(var[0]),
                        "value": format(var[1])
                    })
            exception_info.append(frame_info)
    request_info = {
        "path_info": request.path_info,
        "method": request.META['REQUEST_METHOD'],
        "url": request.build_absolute_uri(),
        "GET": {},
        "POST": {},
        "FILES": {},
        "COOKIES": {},
        "META": {}
    }
    if hasattr(request, "GET"):
        for key, value in request.GET.iteritems():
            request_info['GET'][key] = format(value)
    if "filtered_POST" in ctx:
        for key, value in ctx['filtered_POST'].iteritems():
            request_info['POST'][key] = format(value)
    if hasattr(request, "FILES"):
        for key, value in request.FILES.iteritems():
            request_info['FILES'][key] = format(value)
    if hasattr(request, "COOKIES"):
        for key, value in request.COOKIES.iteritems():
            request_info['COOKIES'][key] = format(value)
    if hasattr(request, "META"):
        for key, value in request.META.iteritems():
            request_info['META'][key] = format(value)
    settings_info = {}
    for key, value in ctx['settings'].iteritems():
        settings_info[key] = format(value)
        
    ctx['errorid'] = errorid = uuid.uuid4().hex
    
    full_info = dict(
        __time=datetime.datetime.now().isoformat(),
        __uuid=errorid,
        settings=settings_info,
        request=request_info,
        traceback=exception_info,
        stack=traceback.format_exc(exc_info[2]),
        last_frame=last_frame,
        template_loaders=loaders,
        template_errors=template_errors,
        unicode_hint=unicdoe_hint,
        exception_type=exception_type,
        exception_value=exception_value,
        django_version=django_version,
        python_version=python_version,
        python_executable=python_executable,
        python_path=python_path,
        server_time=server_time
    )
    
    return (errorid, ctx, full_info)
 
def redirector(request, app, view):
    params = {}
    
    for (key, val) in request.GET.iteritems():
        params[key] = val

    full_name = "%s:%s" % (app, view)
    
    if not view or not app:
        logger.error("Redirector requires both 'app' and 'view' to be set, received: app='%s' view='%s'" % (app, view))
        raise Error("Redirector requires both 'app' and 'view' to be set, received: app='%s' view='%s'" % (app, view))
        
    return HttpResponseRedirect(reverse(full_name, kwargs=params))
    
def default_search(request):
    app = request.app_name
    lang_code = request.LANGUAGE_CODE
    query_suffix = request.META['QUERY_STRING']
    if query_suffix != '':
        query_suffix = '?' + query_suffix
    return HttpResponseRedirect(make_splunkweb_url("/%s/app/%s/search%s" % 
        (lang_code, app, query_suffix)))
    
@render_to()
@login_required
def default_template_render(request, template_name):
    app = request.app_name
    template_path = "%s:%s.html" % (app, template_name)
    return {
        "TEMPLATE": template_path
    }

@never_cache
def handle404(request):    
    # This code is modified from views/debug.py in Django, as we want to display
    # a debug style view, just modified slightly.
    exc_info = sys.exc_info()
    exception = exc_info[1]
    
    try:
        tried = exception.args[0]['tried']
    except (IndexError, TypeError, KeyError):
        tried = []

    urlconf = getattr(request, 'urlconf', settings.ROOT_URLCONF)
    if isinstance(urlconf, types.ModuleType):
        urlconf = urlconf.__name__

    c = Context({
        'urlconf': urlconf,
        'root_urlconf': settings.ROOT_URLCONF,
        'request_path': request.path_info[1:], # Trim leading slash
        'urlpatterns': tried,
        'reason': force_bytes(exception, errors='replace'),
        'request': request,
        'settings': get_safe_settings(),
    })
    
    return HttpResponseNotFound(render_to_string('splunkdj:404.html', context_instance=c))

@never_cache
def handle404_bad_urlconf(request):
    c = Context({
        'request_path': request.path_info[1:], # Trim leading slash
        'request': request,
    })
    
    return HttpResponseNotFound(
        render_to_string('splunkdj:404_bad_urlconf.html', context_instance=c))
    
@never_cache
def handle500(request):    
    # Let's attempt to render a more useful error message
    errorid, ctx, exception = get_exception_info(request)
    
    # We log the raw error to the log file, so that splunk can pick it up as
    # JSON.
    error_logger.error(json.dumps(exception, sort_keys=True))
    
    # Build up the URL for making the query
    lang_code = request.LANGUAGE_CODE if hasattr(request, 'LANGUAGE_CODE') else 'en-us'
    query_args = {
        "q": 'search index=_internal sourcetype=django_error "%s" | head 1 | spath' % errorid,
        "display.events.maxlines": 0,
        "display.general.type": "events",
        "earliest": 0,
        "latest": ""
    }
    query_string = urllib.urlencode(query_args)
    ctx['search_url'] = make_splunkweb_url("/%s/app/search/search?%s" % (lang_code, query_string))
    
    return HttpResponseServerError(render_to_string('splunkdj:500.html', context_instance=Context(ctx)))

@never_cache
@render_to('splunkdj:page_config.html', mimetype="application/javascript")
@login_required
def get_page_config(request):
    referer = request.META.get("HTTP_REFERER", "")
    app = ""
    app_label = ""
    if referer:
        try:
            parsed = urlparse(referer)
            parsed_path = parsed.path.replace("/%s/" % settings.MOUNT, "/")
            resolved = resolve(parsed_path)
            app = resolved.app_name
            
            if app:
                app_label = request.service.apps[app]["label"]
        except Exception, e:
            # If there was an error here, don't kill the entire page
            # just return some default info
            app = app or ""
            app_label = app_label or app
    
    zone_info = request.service.get('/services/search/timeparser/tz').body.read()
    
    return {
        "autoload": "1" == request.GET.get("autoload", "0"),
        "config": json.dumps({
            "SPLUNKD_FREE_LICENSE": request.user.is_free,
            "MRSPARKLE_ROOT_PATH": "/%s" % str(settings.SPLUNK_WEB_MOUNT).strip("/"),
            "DJANGO_ROOT_PATH": "/%s" % str(settings.RAW_MOUNT),
            "MRSPARKLE_PORT_NUMBER": str(settings.SPLUNK_WEB_PORT),
            "DJANGO_PORT_NUMBER": str(settings.DJANGO_PORT),
            "LOCALE": str(request.LANGUAGE_CODE),
            "JS_LOGGER_MODE": "None",
            "USERNAME": str(request.user.username),
            "USER_DISPLAYNAME": str(request.user.realname),
            "APP": str(app),
            "APP_DISPLAYNAME": str(app_label),
            "SERVER_ZONEINFO": str(zone_info),
            "SPLUNKD_PATH": str(settings.PROXY_PATH),
            "DJANGO_ENABLE_PROTECTIONS": True,
        })
    }
