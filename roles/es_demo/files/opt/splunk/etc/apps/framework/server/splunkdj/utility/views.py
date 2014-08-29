from django.contrib.auth.decorators import login_required as require_login
from django.shortcuts import render_to_response
from django.template import RequestContext
from splunkdj.setup import config_required as require_config

def render_template(template, mimetype=None, login_required=True, config_required=False):
    def renderer(request, *args, **kwargs):
        return render_to_response(
            template,
            kwargs,
            context_instance=RequestContext(request))
    
    action = renderer
    if login_required or config_required:
        action = require_login(action)
    if config_required:
        action = require_config(action)
    return action