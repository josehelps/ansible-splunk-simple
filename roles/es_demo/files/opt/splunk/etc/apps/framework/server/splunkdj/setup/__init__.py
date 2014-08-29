from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from splunkdj.utility import get_current_app_name

def config_required(function):
    """
    A view function decorator that redirects the user to the
    setup screen if the current app is not configured.
    """
    # @config_required requires that the user be already logged in.
    # Thus make sure that login has happened in case the user forgot
    # the @login_required decorator or (more likely) put it in the wrong order.
    @login_required
    def wrapper(request, *args, **kwargs):
        # Redirect to setup screen if not configured
        service = request.service
        if not get_configured(service):
            app_name = get_current_app_name(request)
            return HttpResponseRedirect(reverse(app_name + ':setup'))
        
        # Otherwise proceed normally
        return function(request, *args, **kwargs)
    
    return wrapper

def get_configured(service):
    """
    Returns whether the current app is configured.
    """
    try:
        return (service.confs['app']['install']['is_configured'] == '1')
    except KeyError:
        # No config file, stanza, or key? Default to unconfigured.
        return False

def set_configured(service, configured):
    """
    Sets whether the current app is configured.
    """
    try:
        app_install = service.confs['app']['install']
    except KeyError:
        # No config file or stanza? Create them.
        app_install = service.confs['app'].create('install')
    
    app_install.submit({
        'is_configured': 1 if configured else 0
    })

def create_setup_view_context(request, form_cls, next_url):
    """
    Prepares the specified form class to be rendered by a setup view template.
    Returns the context dictionary to be rendered with the template.
    """
    if not hasattr(form_cls, 'load') or not hasattr(form_cls, 'save'):
        raise ValueError(
            ('Expected form class %s to have "load" and "save" methods. ' +
             'Are you passing a django.forms.Form instead of ' +
             'a splunkdj.setup.forms.Form?') % form_cls.__name__)
    
    service = request.service

    if request.method == 'POST':
        form = form_cls(request.POST)
        if form.is_valid():
            # Save submitted settings and redirect to home view
            form.save(request)
            set_configured(service, True)
            return HttpResponseRedirect(next_url)
        else:
            # Render form with validation errors
            pass
    else:
        if get_configured(service):
            # Render form bound to existing settings
            form = form_cls.load(request)
        else:
            # Render unbound form
            form = form_cls()

    return {
        'form': form,
        'configured': get_configured(service),
    }