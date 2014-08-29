import sys
import re
import json

from os import path, makedirs
from copy import deepcopy

from django.core.urlresolvers import RegexURLPattern, RegexURLResolver
from django.core.management.base import BaseCommand
from django.utils import simplejson
from django.utils.datastructures import SortedDict
from django.conf import settings
from django.template import loader, Context

RE_KWARG = re.compile(r"(\(\?P\<(.*?)\>.*?\))") #Pattern for recongnizing named parameters in urls
RE_ARG = re.compile(r"(\(.*?\))") #Pattern for recognizing unnamed url parameters

def handle_url_module(js_patterns, module_name, prefix="", app=None, app_kwargs=None):
    """
    Load the module and output all of the patterns
    Recurse on the included modules
    """
    if isinstance(module_name, basestring):
        __import__(module_name)
        root_urls = sys.modules[module_name]
        patterns = root_urls.urlpatterns
    else:
        root_urls = module_name
        patterns = root_urls
        
    for pattern in patterns:
        if issubclass(pattern.__class__, RegexURLPattern):
            if pattern.name:
                # Add the kwargs for the view
                kwargs = deepcopy(app_kwargs) or {}
                kwargs.update(pattern.default_args or {})
                
                full_url = prefix + pattern.regex.pattern
                for chr in ["^","$"]:
                    full_url = full_url.replace(chr, "")
                #handle kwargs, args
                kwarg_matches = RE_KWARG.findall(full_url)
                if kwarg_matches:
                    for el in kwarg_matches:
                        #prepare the output for JS resolver
                        full_url = full_url.replace(el[0], "<%s>" % el[1])
                #after processing all kwargs try args
                args_matches = RE_ARG.findall(full_url)
                if args_matches:
                    for el in args_matches:
                        full_url = full_url.replace(el, "<>")#replace by a empty parameter name
                
                if pattern.name not in js_patterns:
                    js_patterns[pattern.name] = []
                        
                js_patterns[pattern.name].append({
                    "pattern": "/" + full_url,
                    "app": app or "",
                    "kwargs": kwargs
                })
        elif issubclass(pattern.__class__, RegexURLResolver):
            if pattern.urlconf_name:
                handle_url_module(
                    js_patterns, 
                    pattern.urlconf_name, 
                    prefix=pattern.regex.pattern, 
                    app=pattern.app_name, 
                    app_kwargs=pattern.default_kwargs
                )
                
def create_javascript_urlpatterns():
    js_patterns = SortedDict()
    handle_url_module(js_patterns, settings.ROOT_URLCONF)
    
    dirpath = path.join(settings.STATIC_ROOT, settings.JS_CACHE_DIR)
    filepath = path.join(settings.STATIC_ROOT, settings.JS_CACHE_DIR, "urlresolver.js")
    
    tmpl = loader.get_template('splunkdj:jsurls.html')
    ctx = Context({ 'patterns': json.dumps(js_patterns), 'mount': settings.MOUNT })
    rendered = tmpl.render(ctx)
    
    if not path.exists(dirpath):
        makedirs(dirpath)
    
    output_file = open(filepath, 'w')
    output_file.write(rendered)
    output_file.flush()
    
    output_file.close()