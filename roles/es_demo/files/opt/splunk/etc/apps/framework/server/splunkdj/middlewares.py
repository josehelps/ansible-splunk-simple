
from django.middleware.csrf import get_token
from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.core.urlresolvers import is_valid_path, resolve, reverse
from django.http import HttpResponseRedirect
from django.utils.cache import patch_vary_headers
from django.utils import translation
from django.http import Http404

from splunkdj.auth.backends import get_user
from splunkdj.utility import format_local_tzoffset, create_derived_service

import datetime
import time
import logging, logging.handlers
import rfc822
import sys
import os

logger = logging.getLogger('spl.django.service')
        
class SplunkCsrfMiddleware(object):
    def process_view(self, request, *args, **kwargs):
        get_token(request)
        return None
        
class SplunkResolvedUrlMiddleware(object):
    def process_request(self, request):
        # Set a default so we don't have to ensure it has the attribute
        request.app_name = None
        request.url_name = None
        
        resolved = None
        try:
            resolved = resolve(request.path_info)
        except:
            # If we had an error in resolution, then we can continue, we don't
            # need to do anything
            pass
            
        # If we don't have a resolved match, there is nothing for us to do. 
        # We can just go ahead and return.
        if resolved:
            request.app_name = resolved.app_name
            request.url_name = resolved.url_name
                
        return
        
class SplunkAppEnabledMiddleware(object):
    """
    Ensure that when a URL pattern is accessed in a particular app-scope,
    that the app in question is enabled.
    """
    
    def _verify_app_is_enabled(self, service, app_name):
        if app_name and app_name == 'homefx':
            return
        
        # We need to use the most general service as the app may be disabled.
        service = create_derived_service(service, app=None, owner=None)
        try:
            app = service.apps[app_name]
            if app['disabled'] == '1' or app['visible'] == '0':
                raise Http404("Application '%s' is disabled." % app_name)
        except:
            raise Http404("Application '%s' is disabled." % app_name)
    
    def process_request(self, request):
        if request.app_name and request.user.is_authenticated():
            # Now that we have a name for the app, we can go ahead and
            # try and see if that app is enabled.
            return self._verify_app_is_enabled(request.service, request.app_name)
                
        return
        
class SplunkLocaleMiddleware(LocaleMiddleware):
    # The base LocaleMiddleware class in Django core does not seem to properly
    # handle redirects when Django is not mounted on the root. This simply
    # reimplements the logic for handling the response, most of this code is
    # taken verbatim, and we only changed the path that we redirect to.
    def process_response(self, request, response):
        language = translation.get_language()
        if (response.status_code == 404 and
                not translation.get_language_from_path(request.path_info)
                    and self.is_language_prefix_patterns_used()):
            urlconf = getattr(request, 'urlconf', None)
            language_path = '/%s%s' % (language, request.path_info)
            path_valid = is_valid_path(language_path, urlconf)
            if (not path_valid and settings.APPEND_SLASH
                    and not language_path.endswith('/')):
                path_valid = is_valid_path("%s/" % language_path, urlconf)

            if path_valid:
                path = request.get_full_path()
                script_mount = request.META.get("SCRIPT_NAME", "")
                
                if path.startswith(script_mount):
                    path = path.replace(script_mount, ("%s/%s" % (script_mount, language)), 1)
                
                language_url = "%s://%s%s" % (
                    request.is_secure() and 'https' or 'http',
                    request.get_host(), path)
                return HttpResponseRedirect(language_url)
        translation.deactivate()

        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = language
        return response
        
class SplunkWebSessionMiddleware(object):
    def __init__(self, port=8000, **kwargs):
        
        self._initialized = False
        self._storage_path = None
        
        if not settings.SPLUNK_WEB_INTEGRATED:
            return
        
        try:
            from lib.util import splunk_to_cherry_cfg, make_absolute
            
            cherrypy_cfg = splunk_to_cherry_cfg('web', 'settings')
            
            storage_type = cherrypy_cfg.get('tools.sessions.storage_type')
            storage_path = None
            
            if storage_type == 'file':
                storage_path = make_absolute(cherrypy_cfg['tools.sessions.storage_path'])
            else:
                return
            
            self._storage_path = storage_path
            self._initialized = True
        except Exception, e:
            self._initialized = False
            pass
            
            
    def process_request(self, request):
        if not self._initialized or not self._storage_path:
            return
            
        user = None
        session = None
            
        try:
            from lib.sessions import FileSession
            
            cookie_name = 'session_id_%s' % settings.SPLUNK_WEB_PORT
            if cookie_name not in request.COOKIES:
                return
                
            splunkweb_cookie = request.COOKIES[cookie_name]
            
            session = FileSession(
                splunkweb_cookie,
                storage_path=self._storage_path,
                timeout=60,
                clean_freq=5
            )
            
            # Acquire the lock. If this fails, we assume that the lock is no
            # longer acquired, and thus does not need to be released. Any 
            # future use is protected by the try/finally which will release
            # the lock when it is complete.
            session.acquire_lock(read_lock=True)
            
            # DO NOT PUT ANYTHING HERE. ALL CODE SHOULD BE INSIDE THE TRY/FINALLY,
            # SO THAT WE CAN ENSURE THE SESSION LOCK GETS RELEASED.
            
            try:
                if 'sessionKey' in session:
                    session_key = "Splunk %s" % session['sessionKey']
                    username = None
                    
                    if 'user' in session and 'name' in session['user']:
                        username = session['user']['name']
                        
                    user = get_user(username, session_key)
                    if user:
                        request._cached_user = user
            finally:
                # If we failed to create a user, and we have a session,
                # then we need to delete the session.
                # The main reason is that if we don't have a user, it means
                # we are not authenticated. If we aren't authenticated, we'll
                # get redirected to Splunkweb's login page, which will just 
                # redirect us back if a sessionKey value exists (whether it
                # is valid or not). We then get into an infinite redirect loop,
                # as we'll just come back here.
                if not user:
                    session.delete()
                
                # Release the lock
                session.release_lock()
                
        except Exception, e:
            logger.exception(e)
            pass

# This Django request logger is an implementation of Splunkweb's logging 
# handler. Django's objects are different, but the resulting logs are meant
# to be the same as Splunkweb

class SplunkDjangoRequestLoggingMiddleware(object):
    error_logger = None
    access_logger = None

    access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' 

    def __init__(self):
        self.access_logger = logging.getLogger('spl.django.access')
        self.error_logger = logging.getLogger('spl.django.error')

    def process_response(self, request, response):

        """
        Write to the access log (in Apache/NCSA Combined Log format).

        This is a port of the Splunk web_access logging code. It is a rough
        mapping of request objects in the splunk web cherrypy server to equivalent
        objects in the django environment 
        """
        atoms = {'h': request.META.get('REMOTE_ADDR', ''),# or REMOTE_HOST
                 'l': '-',
                 'u': getattr(request, 'user', '-'),
                 't': self.access_time(time.time()),
                 'r': "%s %s %s" % (request.method, 
                                    request.get_full_path(), 
                                    request.META.get('SERVER_PROTOCOL', '')), #or ACTUAL_SERVER_PROTOCOL
                 's': response.status_code,
                 'b': len(response.content) or '-',
                 'f': request.META.get('HTTP_REFERER', ''),
                 'a': request.META.get('HTTP_USER_AGENT', ''),
                 }

        for k, v in atoms.items():
            if isinstance(v, unicode):
                v = v.encode('utf8')
            elif not isinstance(v, str):
                v = str(v)
            # Fortunately, repr(str) escapes unprintable chars, \n, \t, etc
            # and backslash for us. All we have to do is strip the quotes.
            v = repr(v)[1:-1]
            # Escape double-quote.
            atoms[k] = v.replace('"', '\\"')

        try:
            # JIRA: DVPL-3314
            self.access_logger.info(self.access_log_format % atoms)
        except:
            error_logger.log("Error writing access log")
            self(traceback=true)

        return response

    def access_time(self, req_time):
        now = datetime.datetime.fromtimestamp(req_time)
        month = rfc822._monthnames[now.month - 1].capitalize()
        return ('[%02d/%s/%04d:%02d:%02d:%02d.%03d %s]' %
                (now.day, month, now.year, now.hour, now.minute, now.second, 
                 now.microsecond/1000, format_local_tzoffset(req_time)))
        

                
        