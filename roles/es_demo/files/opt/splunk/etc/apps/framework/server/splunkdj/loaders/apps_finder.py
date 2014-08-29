import os
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module

class BaseFinder(object):
    """
    Base class for all app finder classes.
    """
    def find(self):
        raise NotImplementedError()

class BasicAppsFinder(BaseFinder):
    """
    A basic app finder that will find all framework apps in $FRAMEWORK_HOME/server/apps.
    """
    def __init__(self, *args, **kwargs):
        super(BasicAppsFinder, self).__init__(*args, **kwargs)
        
        self._path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    def find(self):
        # Add the server/apps directory to the PYTHONPATH
        apps_path = os.path.join(self._path, "apps")
        sys.path.insert(0, apps_path)
        
        # Find all the apps in server/apps
        apps = ()
        for app_path in os.listdir(apps_path):
            full_app_path = os.path.join(self._path, "apps", app_path)
            is_dir = os.path.isdir(full_app_path)
            
            if not is_dir:
                continue
            
            apps += (app_path,)
            
        return apps
        
class SplunkWebAppsFinder(BaseFinder):
    """
    A basic app finder that will find all framework apps in $SPLUNK_HOME/etc/apps.
    """
    def __init__(self, *args, **kwargs):
        super(SplunkWebAppsFinder, self).__init__(*args, **kwargs)
        
        # In case there is an error, we initialize it with the SPLUNK_HOME versions
        apps_root = os.path.normpath(os.path.join(os.environ['SPLUNK_HOME'], "etc", "apps"))
        slave_apps_root = os.path.normpath(os.path.join(os.environ['SPLUNK_HOME'], "etc", "slave_apps"))
        
        try:
            # Find the true locations (respecting SHP, etc) for apps
            import splunk.clilib.bundle_paths as bundle_paths
            apps_root = bundle_paths.get_base_path()
            slave_apps_root = bundle_paths.get_slaveapps_base_path()
        except Exception, e:
            pass
        
        self.roots = [
            apps_root,
            slave_apps_root,
        ]
    
    def _find(self, root):
        # Find all the apps in etc/apps and etc/server-apps
        apps = ()
        for splunkweb_app_name in os.listdir(root):
            full_splunkweb_app_path = os.path.join(root, splunkweb_app_name)
            is_dir = os.path.isdir(full_splunkweb_app_path)
            
            if not is_dir:
                continue
            
            # We look for a etc/apps/<app>/django/<app> folder, as it needs to 
            # a Python package with the name of the app
            full_django_app_path = os.path.join(full_splunkweb_app_path, 'django', splunkweb_app_name)
            if not os.path.exists(full_django_app_path):
                continue
            
            # We add the django container folder to the PYTHONPATH os that we can
            # properly import it.
            sys.path.insert(0, os.path.join(full_splunkweb_app_path, 'django'))
            
            # Add it to the apps to return
            apps += (splunkweb_app_name,)
            
        return apps
    
    def find(self):
        apps = ()
        for root in self.roots:
            if root and os.path.isdir(root):
                apps += self._find(root)
            
        return apps

def find_user_apps():
    
    # This is a rewrite of the logic inside debug_toolbar to load
    # all the user app finders
    finder_paths = getattr(settings, 'USER_APP_FINDERS')
    finder_classes = []
    for finder_path in finder_paths:
        try:
            dot = finder_path.rindex('.')
        except ValueError:
            raise ImproperlyConfigured(
                "%s isn't a user app finder module" % finder_path)
        finder_module, finder_classname = finder_path[:dot], finder_path[dot + 1:]
        try:
            mod = import_module(finder_module)
        except ImportError, e:
            raise ImproperlyConfigured(
                'Error importing user app finder %s: "%s"' %
                (finder_module, e))
        try:
            finder_class = getattr(mod, finder_classname)
        except AttributeError:
            raise ImproperlyConfigured(
                'User app finder module "%s" does not define a "%s" class' %
                (finder_module, finder_classname))
        finder_classes.append(finder_class)
    
    # Now that we have our classes, we will
    # run them all and find all the apps
    apps = ()
    for finder_class in finder_classes:
        finder = finder_class()
        found_apps = finder.find()
        
        apps += found_apps
        
    return apps