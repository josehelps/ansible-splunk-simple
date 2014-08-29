from django.contrib.auth.decorators import login_required
import settings
from splunkdj.decorators.render import render_to
from splunkdj.utility import create_derived_service
from splunklib.binding import namespace

_NO_DESCRIPTION = "No description has been provided for this app."

# Returns the specified configuration file key or None if it does not exist
def _get_conf_key(conf, stanza_name, key):
    if conf is None:
        # No app.conf available
        return None
    try:
        return conf[stanza_name][key]
    except KeyError:
        return None

@render_to('homefx:home.html')
@login_required
def home(request):
    apps = []
    for app in settings.USER_APPS:
        if app == "homefx":
            continue
        
        # Workaround Configurations.__getitem__ not supporting namespace
        # override correctly for individual lookups. (DVPL-2155)
        app_service = create_derived_service(request.service, owner='nobody', app=app)
        try:
            app_conf = app_service.confs['app']
        except KeyError:
            # App does not have an app.conf
            app_conf = None
        
        info = {
            'author': _get_conf_key(app_conf, 'launcher', 'author') or "",
            'description': _get_conf_key(app_conf, 'launcher', 'description') or _NO_DESCRIPTION,
            'name': app,
            'label': _get_conf_key(app_conf, 'ui', 'label') or app,
            'version': _get_conf_key(app_conf, 'launcher', 'version') or "0.0"
        }
        apps.append(info)

    return { 'apps': apps }
