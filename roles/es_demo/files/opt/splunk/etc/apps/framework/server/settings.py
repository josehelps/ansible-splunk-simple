# Django settings for testsite project.

import os
import sys
import json

current_dir = os.path.dirname(__file__)

# Add the contrib packages to our pythonpath
contrib_dir = os.path.join(current_dir, '..', 'contrib')
for contrib_package_path in os.listdir(contrib_dir):
    contrib_package_path = os.path.join(contrib_dir, contrib_package_path)
    contrib_package_path = os.path.abspath(contrib_package_path)
    sys.path.insert(0, contrib_package_path)

# Get the config file
SPLUNKDJ_CONFIG = {}
if 'SPLUNKDJ_CONFIG' in os.environ and os.environ['SPLUNKDJ_CONFIG'].strip():
    SPLUNKDJ_CONFIG = json.load(open(os.environ['SPLUNKDJ_CONFIG'], 'r'))

# Provide a way to access elements in the config that fails nicely
def get_config(option):
    if option not in SPLUNKDJ_CONFIG:
        raise ValueError('Could not find expected "%s" setting in %s' % (
            option, os.environ['SPLUNKDJ_CONFIG']))
    return SPLUNKDJ_CONFIG[option]

# Pickup the debug flag from the config file
DEBUG = get_config("debug")
TEMPLATE_DEBUG = DEBUG

# Find out whether we are in test mode (best way to do this according
# to internet)
TEST_MODE = "test" in sys.argv or os.environ.has_key("TEST_MODE")

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {}
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

gettext = lambda s: s
LANGUAGES = (
    ('en-us', gettext('English')),
    ('en-gb', gettext('British English')),
    ('de-de', gettext('German')),
    ('it-it', gettext('Italian')),
    ('ko-kr', gettext('Korean')),
    ('ja-jp', gettext('Japanese')),
    ('zh-cn', gettext('Simplified Chinese')),
    ('zh-tw', gettext('Traditional Chinese')),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# We will error out if there is no 'mount' set.
MOUNT = get_config('mount')
RAW_MOUNT = get_config('raw_mount')

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(current_dir, 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/%s/static/' % MOUNT

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies'
SESSION_SERIALIZER='django.contrib.sessions.serializers.JSONSerializer'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'splunkdj.loaders.statics.StaticRootFinder',
    'splunkdj.loaders.statics.SplunkWebStaticFinder',
    'splunkdj.loaders.statics.SplunkWebAppStaticFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = get_config('secret_key')

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'splunkdj.loaders.template_loader.SpecificAppLoader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'splunkdj.middlewares.SplunkDjangoRequestLoggingMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'splunkdj.middlewares.SplunkLocaleMiddleware',
    # NOTE: Middleware which calls resolve/reverse must come after this comment!
    'splunkdj.middlewares.SplunkResolvedUrlMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'splunkdj.middlewares.SplunkWebSessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'splunkdj.auth.middleware.SplunkAuthenticationMiddleware',
    'splunkdj.middlewares.SplunkAppEnabledMiddleware',
    'splunkdj.middlewares.SplunkCsrfMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

if 'x_frame_options_sameorigin' in SPLUNKDJ_CONFIG and get_config('x_frame_options_sameorigin'):
    MIDDLEWARE_CLASSES += ('django.middleware.clickjacking.XFrameOptionsMiddleware',)

INTERNAL_IPS = ('127.0.0.1', 'localhost')

ALLOWED_HOSTS = ['*']

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "splunkdj.context_processors.splunkdj")

ROOT_URLCONF = 'urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

AUTHENTICATION_BACKENDS = (
    'splunkdj.auth.backends.SplunkAuthenticationBackend',
)

# Only if we are in test mode should we use the model backend
if TEST_MODE:
    AUTHENTICATION_BACKENDS += ('django.contrib.auth.backends.ModelBackend',)
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3', 
        'NAME': 'testdb',
    }

USER_APP_FINDERS = (
    'splunkdj.loaders.apps_finder.BasicAppsFinder',
    'splunkdj.loaders.apps_finder.SplunkWebAppsFinder',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'splunkdj',
)

BUILTIN_APPS = (
    'examplesfx',
    'homefx',
    'quickstartfx',
    'testfx',
    'setupfx'
)

USER_APPS = (
    # user defined apps go here - they need to be in the PYTHONPATH
)

# Use the loaders to find all the other user apps
from splunkdj.loaders.apps_finder import find_user_apps
USER_APPS += find_user_apps()

DISCOVERED_APPS = set(USER_APPS) - set(BUILTIN_APPS)

# Combine the USER_APPS into INSTALLED_APPS
INSTALLED_APPS += USER_APPS

SPLUNKD_SCHEME        = str(get_config('splunkd_scheme'))
SPLUNKD_HOST          = str(get_config('splunkd_host'))
SPLUNKD_PORT          = int(get_config('splunkd_port'))
SPLUNK_WEB_SCHEME     = str(get_config('splunkweb_scheme'))
SPLUNK_WEB_HOST       = str(get_config('splunkweb_host'))
SPLUNK_WEB_PORT       = int(get_config('splunkweb_port'))
SPLUNK_WEB_MOUNT      = str(get_config('splunkweb_mount'))
SPLUNK_WEB_INTEGRATED = bool(get_config('splunkweb_integrated'))

DJANGO_PORT = int(get_config('splunkdj_port'))

CSRF_COOKIE_NAME = "django_csrftoken_%s" % DJANGO_PORT
SESSION_COOKIE_NAME = "django_sessionid_%s" % DJANGO_PORT
SESSION_COOKIE_PATH="/%s" % MOUNT.strip("/")

DEFAULT_APP = 'homefx'

LOGIN_URL = None
LOGIN_TEMPLATE = None
LOGIN_REDIRECT_URL = None
LOGOUT_URL = None

if not SPLUNK_WEB_INTEGRATED:
    LOGIN_URL = "/%s/accounts/login/" % MOUNT
    LOGIN_REDIRECT_URL = "/%s" % MOUNT
    LOGOUT_URL = '/%s/accounts/logout/' % MOUNT
    if get_config('quickstart'):
        LOGIN_TEMPLATE = 'quickstartfx:login.html'
    else:
        LOGIN_TEMPLATE = 'splunkdj:auth/registration/login.html'
else:    
    # If we are integrated into Splunkweb, then we are going to use it
    # logging in/out.
    splunkweb_mount = "%s/" % SPLUNK_WEB_MOUNT if SPLUNK_WEB_MOUNT else ""
    
    LOGIN_URL = "/%saccount/login/" % splunkweb_mount
    LOGIN_REDIRECT_URL = "/%s" % MOUNT
    LOGOUT_URL = '/%saccount/logout/' % splunkweb_mount
    
    import django.contrib.auth
    
    # Splunkweb uses "return_to", so we will as well.
    django.contrib.auth.REDIRECT_FIELD_NAME = "return_to"

PROXY_PATH = str(get_config('proxy_path'))

# Whether or not to use built and minified files
USE_BUILT_FILES = bool(get_config('use_built_files'))
USE_MINIFIED_FILES = bool(get_config('use_minified_files'))

# Whether or not we are running on Splunk 5
try:
    SPLUNK_5 = get_config('splunk_5')
except ValueError:
    SPLUNK_5 = False

# JS
JS_CACHE_DIR = os.path.join('splunkjs', 'generated')

# To allow multi-line templatetags, we have to modify the regex in
# django
import django.template.base
import re
tag_re_pattern = django.template.base.tag_re.pattern
tag_re_flags = django.template.base.tag_re.flags
django.template.base.tag_re = re.compile(tag_re_pattern, tag_re_flags | re.S)

# To allow _ in the domain name, we have to modify the host validation
# regex
import django.http.request
django.http.request.host_validation_re = re.compile(r"^([a-z0-9._\-]+|\[[a-f0-9]*:[a-f0-9:]+\])(:\d+)?$")

# Add our default tags
from django.template import add_to_builtins
add_to_builtins('splunkdj.templatetags.defaulttags')

# For every app, we're going to try and load its models file. If none exists,
# or we get an error, we just exit. We do this because some Django apps put
# initialization code in models.py.
import importlib
for app in INSTALLED_APPS:
    try:
        app_urls_module = "%s.models" % app
        app_urls = importlib.import_module(app_urls_module)
    except:
        pass

# Logs

import logging, logging.handlers

BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters':{
        'verbose': {
            'format':'%(asctime)s %(levelname)-s %(module)s:%(lineno)d - %(message)s',
        },
        'simple': {
            'format': '%(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'INFO',
        },
        'file_access': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(os.environ['SPLUNK_HOME'], BASE_LOG_PATH, 'django_access.log'),
            'formatter': 'simple',
            'level': 'INFO',
        },
        'file_service': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(os.environ['SPLUNK_HOME'], BASE_LOG_PATH, 'django_service.log'),
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'file_error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(os.environ['SPLUNK_HOME'], BASE_LOG_PATH, 'django_error.log'),
            'formatter': 'simple',
            'level': 'INFO',
        },
    },
    'loggers': {
        'spl.django.access': {
            'handlers': ['console', 'file_access'],
            'level': 'INFO',
        },
        'spl.django.service': {
            'handlers': ['console', 'file_service'],
            'level': 'INFO',
        },
        'spl.django.error': {
            'handlers': ['console', 'file_service'],
            'level': 'ERROR',
        },
        'spl.django.request_error': {
            'handlers': ['console', 'file_error'],
            'level': 'ERROR',
        },
    }
}

# Clear out the SPLUNKDJ_CONFIG settings
SPLUNKDJ_CONFIG = None