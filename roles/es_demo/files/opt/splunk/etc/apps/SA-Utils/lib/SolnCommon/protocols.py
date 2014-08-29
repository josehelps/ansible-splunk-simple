'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import abc
import sys
import urllib
import urllib2

import splunk
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.codecs import GzipHandler
from SolnCommon.codecs import ZipHandler
from SolnCommon.credentials import CredentialManager


class ProtocolHandler(object):
    '''Abstract base class for protocol handlers.'''
    __metaclass__ = abc.ABCMeta

    def __init__(self, logger, sessionKey, **kwargs):
        # Save references to logger and session key.
        self._logger = logger
        self._sessionKey = sessionKey

    @abc.abstractmethod
    def format_query(self, query):
        '''Perform any necessary formatting on the query.'''
        return query

    @abc.abstractmethod
    def run(self, query):
        '''Run a protocol operation.'''
        raise NotImplementedError

    @abc.abstractmethod
    def format_output(self, output):
        '''Format the output data'''
        return output


class ProtocolHandlerOptions(object):
    '''Abstract base class for protocol handler options.'''
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def set_options(self, *args, **kwargs):
        '''Set options for the protocol handler.'''
        raise NotImplementedError


class HttpProtocolHandlerOptions(ProtocolHandlerOptions):
    '''Class for setting options commonly used by an HTTP(S)-based API.'''

    _site_password = None   # A password for remote authentication if required
    _site_user = None       # A user for remote authentication if required
    _format = None          # ?
    _proxy_password = None  # A proxy password
    _proxy_server = None    # A proxy server
    _proxy_port = None      # A proxy port
    _proxy_user = None      # A proxy user
    _url = None             # The URL for the query
    _errors = []            # Accumulated errors
    _timeout = 30           # The timeout for queries conducted by this handler.

    def __init__(self, *args, **kwargs):
        super(HttpProtocolHandlerOptions, self).__init__(*args, **kwargs)

    def load_credentials(self):

        mgr = CredentialManager(self._sessionKey)

        if self._site_user:
            try:
                self._site_password = mgr.get_clear_password(self._site_user, self._realm, self._app, self._owner)
            except splunk.ResourceNotFound:
                try:
                    # Fall back to not using a realm.
                    self._site_password = mgr.get_clear_password(self._site_user, None, self._app, self._owner)
                except (AttributeError, splunk.ResourceNotFound):
                    self._errors.append('API user credential %s could not be found.' % self._site_user)
        else:
            self._errors.append('An API user credential must be provided for API queries.')

        if self._proxy_user:
            try:
                self._proxy_password = mgr.get_clear_password(self._proxy_user, self._realm, self._app, self._owner)
            except (AttributeError, splunk.ResourceNotFound):
                self._errors.append('Proxy user credential %s could not be found.' % self._proxy_user)
        else:
            # Proxy user is optional.
            pass

    def set_options(self, *args, **kwargs):

        valid_keys = ['app', 'debug', 'owner', 'proxy_port', 'proxy_server', 'proxy_user', 'realm', 'site_user']
        for k in valid_keys:
            setattr(self, '_' + k, kwargs.get(k, None))

        if self._site_user or self._proxy_user:
            self.load_credentials()


class HttpProtocolHandler(ProtocolHandler, HttpProtocolHandlerOptions):

    def __init__(self, logger, sessionKey, **options):
        # Save references to logger and session key.
        self._logger = logger
        self._sessionKey = sessionKey
        
        self.set_options(**options)

    def buildOpener(self):
        ''' Build a URL opener based on the information in options.'''

        handlers = []

        # Proxy server handling
        if self._proxy_user is not None and self._proxy_server is not None:

            # we have already checked to see if proxy_server, proxy_password, and proxy_port are valid
            proxy_server_http = 'http://' + self._proxy_server + ':' + str(self._proxy_port) + '/'
            proxy_server_https = 'https://' + self._proxy_server + ':' + str(self._proxy_port) + '/'

            proxy_password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            proxy_password_mgr.add_password(realm=None,
                                            uri=proxy_server_http,
                                            user=self._proxy_user,
                                            passwd=self._proxy_password)
            proxy_password_mgr.add_password(realm=None,
                                            uri=proxy_server_https,
                                            user=self._proxy_user,
                                            passwd=self._proxy_password)

            proxy_basicauth_handler = urllib2.ProxyBasicAuthHandler(proxy_password_mgr)
            proxy_digestauth_handler = urllib2.ProxyDigestAuthHandler(proxy_password_mgr)
            proxy_handler = urllib2.ProxyHandler({'http': proxy_server_http,
                                                  'https': proxy_server_https})
            handlers.extend([proxy_handler, proxy_basicauth_handler, proxy_digestauth_handler])

        elif self._proxy_server is not None:
            # we have already checked to see if proxy_server and proxy_port are valid
            proxy_server_http = 'http://' + self._proxy_server + ':' + str(self._proxy_port) + '/'
            proxy_server_https = 'https://' + self._proxy_server + ':' + str(self._proxy_port) + '/'
            proxy_handler = urllib2.ProxyHandler({'http': proxy_server_http,
                                                  'https': proxy_server_https})
            handlers.extend([proxy_handler])

        # HTTP auth handling
        if self._site_user is not None:
            # We have already checked to ensure password is valid.
            site_password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            site_password_mgr.add_password(realm=None,
                                           uri=self._url,
                                           user=self._site_user,
                                           passwd=self._site_password)
            site_basicauth_handler = urllib2.HTTPBasicAuthHandler(site_password_mgr)
            site_digestauth_handler = urllib2.HTTPDigestAuthHandler(site_password_mgr)
            handlers.extend([site_basicauth_handler, site_digestauth_handler])

        # Debugging
        #handlers.extend([urllib2.HTTPHandler(debuglevel=1)])

        return urllib2.build_opener(*handlers)

    def format_output(self, output):
        # Decompress the output if the file is gzip/zlib format
        if GzipHandler.checkFormat(output):
            try:
                return GzipHandler.decompress(output)
            except ValueError as e:
                self._logger.exception('Exception while decompressing gzip content: exc=%s', e)
        elif ZipHandler.checkFormat(output):
            try:
                return ZipHandler.decompress(output)
            except ValueError as e:
                self._logger.exception('Exception while decompressing zip content: exc=%s', e)            
        else:
            return output

    def format_query(self, query):
        assert isinstance(query, basestring), "Query was not a string."
        return ProtocolHandler.format_query(self, query)

    def run(self, query, data=None, return_errors=False):
        '''Issue an HTTP request.
        
        @param query: The URL for the request.
        @param data: A dictionary of POST arguments. If empty or None, a GET
            request will be made; any other value results in a POST with the 
            contents of "data" used as POST arguments. The dictionary will
            be URL encoded before use. 
        @param return_errors: If True, the content of the response object will
            be returned when an HTTP error occurs. If False, an HTTP error will
            result in a return value of False.
            
        @return: The content of the HTTP response, or False if an HTTP
            error occurs (see the definition of return_errors above for details
            on error handling).
        '''

        query = self.format_query(query)
        
        # Set data explicitly to None if necessary, to avoid mistakenly forcing 
        # a POST if data was passed as an empty dictionary.
        if data:
            try:
                data = urllib.urlencode(data)
            except TypeError:
                # POST arguments will be ignored, which will likely cause the download to fail. 
                self._logger.exception('Caught TypeError when processing POST arguments for query %s.', query)
                data = None
        else:
            data = None

        if self._debug:
            import pprint
            print 'ERRORS'
            pprint.pprint(self._errors)
            print 'OPTIONS'
            pprint.pprint(self.__dict__)

        opener = self.buildOpener()
        urllib2.install_opener(opener)

        # Perform the query
        request = urllib2.Request(query, data)
        content = None

        # All queries will return as all exceptions are caught.
        # The caller is responsible for checking the response for errors, if
        # necessary. Some HTTP error codes actually return content that
        # includes an error message. These are handled by treating the error
        # code as the response if return_errors is True; if return_errors is
        # False, the caller can expect a return value of None.

        try:
            response = urllib2.urlopen(request, timeout=self._timeout)
            content = response.read()
        except urllib2.HTTPError as e:
            self._logger.error('Caught HTTPError when querying %s: code=%s exc=%s', query, e.code, e)
            if return_errors:
                content = e.read()
        except urllib2.URLError as e:
            self._logger.error('Caught URLError when querying %s: reason=%s exc=%s', query, e.reason, e)
            if return_errors:
                content = e.read()
        except Exception as e:
            # None will be returned as content.
            self._logger.error('Caught unknown exception when querying %s: exc=%s', query, e)

        if content:
            return self.format_output(content)
        else:
            self._logger.error('No content returned when querying %s', query)
        return None


class NoopProtocolHandler(object):
    '''Protocol handler that does nothing. Useful for bypassing "download"
    actions in cases where a local lookup table is the entity being downloaded.'''
    def run(self):
        return
