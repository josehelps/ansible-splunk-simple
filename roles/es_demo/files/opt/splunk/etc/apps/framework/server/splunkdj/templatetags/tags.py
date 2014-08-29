from django import template
from django.conf import settings
from django.utils import importlib
from django.core.urlresolvers import reverse
from django.template import RequestContext
from splunkdj.utility import get_current_app_name

import logging
logger = logging.getLogger('spl.django.service')

register = template.Library()

def _getattr(obj, attr):
    return getattr(obj, attr) if hasattr(obj, attr) else None

@register.assignment_tag
def get_user_apps():
    user_apps = list(settings.USER_APPS)
    user_apps.remove('homefx')
    
    def get_name_and_url(app):
        app_module = importlib.import_module(app)
        
        if hasattr(app_module, '__label__'):
            app_name = app_module.__label__
        else:
            app_name = app
        
        app_url = reverse("%s:home" % app)
    
        return {
            'name': app_name,
            'url': app_url
        }
        
    apps = map(get_name_and_url, user_apps)
    apps = sorted(apps, key=lambda app: app['name'].lower())
    
    return apps
    
@register.assignment_tag(takes_context=True)
def get_splunk_apps(context):
    service = context['request'].service
    apps = service.apps.list()
    
    def filter_visible_and_enabled(app):
        visible = app['visible'] == '1'
        enabled = app['disabled'] != '1'
        
        return visible and enabled
    
    def get_name_and_url(app):
        app_name = app['label']
        app_url = "/en-US/app/%s" % app.name
    
        return {
            'name': app_name,
            'url': app_url
        }
    
    apps = filter(lambda app: not app.name in settings.USER_APPS, apps)
    apps = filter(filter_visible_and_enabled, apps)
    apps = map(get_name_and_url, apps)
    apps = sorted(apps, key=lambda app: app['name'].lower())
    
    return apps
    
@register.assignment_tag(takes_context=True)    
def get_apps(context):
    user_apps = get_user_apps()
    splunk_apps = get_splunk_apps(context)
    
    return sorted(user_apps + splunk_apps, key=lambda app: app['name'].lower())

@register.simple_tag()
def get_app_name(app_path):
    app = importlib.import_module(app_path)
    return _getattr(app, "__label__") or app_path

@register.simple_tag(takes_context=True)
def ensure_request_context(context):
    if not isinstance(context, RequestContext):
        raise Exception("Must use RequestContext")
    
    return ''
    
@register.assignment_tag(takes_context=True)
def get_current_app(context):
    request = context['request']
    app_name = get_current_app_name(request)
    return importlib.import_module(app_name)
    
@register.assignment_tag(takes_context=True)
def get_app_nav(context, app):
    if hasattr(app, 'NAV'):
        return app.NAV or []
    else:
        try:
            importlib.import_module(".nav", app.__name__)
            return app.nav.NAV
        except Exception, e:
            logger.exception(e)
            pass
    return []