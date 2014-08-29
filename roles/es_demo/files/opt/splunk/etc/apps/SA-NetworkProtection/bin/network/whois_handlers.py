'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import abc
import datetime
import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
import urllib2

import splunk
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon import filesystem
from SolnCommon.credentials import CredentialManager


class WhoisBase(object):
    '''Abstract base class for WHOIS operations.'''
    __metaclass__ = abc.ABCMeta
    
    def __init__(self, logger, sessionKey, **kwargs):
        # Save reference to logger object
        self._logger = logger
        self._sessionKey = sessionKey
    
    @abc.abstractmethod
    def run(self, query):
        '''Run the WHOIS query.'''
        return

    @abc.abstractmethod
    def format(self, query, data):
        '''Format the data for use as a Splunk event.'''
        return


class WhoisOptions(object):
    '''Abstract base class for WHOIS options.'''
    __metaclass__ = abc.ABCMeta
        
    @abc.abstractmethod
    def set_options(self, *args, **kwargs):
        '''Set options for the WHOIS query.'''
        return
    

class WhoisCliOptions(WhoisOptions):
    '''Class for setting cross-platform command-line arguments to
    system WHOIS commands as a list, for later use by subprocess module.
    '''
    _options = []
    
    def __init__(self, *args, **kwargs):
        super(WhoisCliOptions, self).__init__(*args, **kwargs)

    def set_proxy_host_option(self, proxy_host):
        if sys.platform == 'nt':
            raise NotImplementedError
        else:
            self._options.extend(['-h', proxy_host])

    def set_port_option(self, proxy_port):
        if sys.platform == 'nt':
            raise NotImplementedError
        else:
            self._options.extend(['-p', proxy_port])
            
    def set_options(self, *args, **kwargs):
        '''Set options for the whois command, if provided.'''
        if kwargs.get('proxy_host', False):
            self.set_host_option(kwargs.get('proxy_host'))
        if kwargs.get('proxy_port', False):
            self.set_port_option(kwargs.get('proxy_port'))
            
            
class WhoisHttpOptions(WhoisOptions):
    '''Class for setting WHOIS options for arguments commonly used by an 
    HTTP(S)-based API.'''
    
    _api_password = None
    _api_user = None
    _format = None
    _proxy_password = None
    _proxy_server = None
    _proxy_port = None
    _proxy_user = None
    _url = None
    _errors = []
    
    TIMEOUT=30

    def __init__(self, *args, **kwargs):
        super(WhoisHttpOptions, self).__init__(*args, **kwargs)

    def load_credentials(self):
        
        mgr = CredentialManager(self._sessionKey)

        if self._api_user:
            try:
                self._api_password = mgr.get_clear_password(self._api_user, self._realm, self._app, self._owner)
            except splunk.ResourceNotFound:
                try:
                    # Fall back to not using a realm.
                    self._api_password = mgr.get_clear_password(self._api_user, None, self._app, self._owner)
                except splunk.ResourceNotFound:
                    self._errors.append('API user credential %s could not be found.' % self._api_user)
        else:
            self._errors.append('An API user credential must be provided for API queries.')

        if self._proxy_user:
            # Try "proxy" realm user first
            try:
                self._proxy_password = mgr.get_clear_password(self._proxy_user, self._realm, self._app, self._owner)
            except splunk.ResourceNotFound:
                # Ignore the realm.
                try:
                    self._proxy_password = mgr.get_clear_password(self._proxy_user, '', self._app, self._owner)
                except splunk.ResourceNotFound:
                    self._errors.append('Proxy user credential %s could not be found.' % self._proxy_user)
        else:
            # Proxy user is optional.
            pass
        
    def set_options(self, *args, **kwargs):

        valid_keys = ['api_user', 'app', 'debug', 'format', 'owner', 'proxy_port', 'proxy_server', 'proxy_user']
        for k in valid_keys:
            setattr(self, '_' + k, kwargs.get(k, None))
            
        if self._api_user or self._proxy_user:
            self.load_credentials()


class WhoisSystem(WhoisBase, WhoisCliOptions):
    '''Run a WHOIS query using the system "whois" command.'''
    
    _sourcetype = 'whois:system'
    
    def __init__(self, *args, **kwargs):
        super(WhoisSystem, self).__init__(*args, **kwargs)
        self.set_options(*args, **kwargs)
        self._locate_executable()
    
    def _locate_executable(self):
        '''Locate the proper WHOIS command for the given system.
        
        UNIX:
        
            Use command provided by the system.
        
        Windows:
        
            Sysinternals WHOIS client can be downloaded from here:
            
                http://technet.microsoft.com/en-us/sysinternals/bb897435.aspx
        '''

        self._exc = None
        if sys.platform == 'nt':
            self._exc = filesystem.which('whois.exe')
        else:
            self._exc = filesystem.which('whois')
    
    def prepare_query(self, query):
        '''Prepare the query.'''
        return [self._exc] + self._options + [query]
            
    def run(self, query):
        '''Run a whois query via the system command. Return the data as a string.'''

        q = self.prepare_query(query)

        try:
            import pprint
            self._logger.info('QUERYING:%s' % pprint.pformat(q))
            return subprocess.check_output(q)
        except subprocess.CalledProcessError as e:
            #(exc_type, exc_value, exc_traceback) = sys.exc_info()
            self._logger.info('ERROR:%s|%s' % (pprint.pformat(q), e))
            pass

    def format(self, query, resolved_query, data):
        '''Format the query and data produced by this handler for use as a Splunk event.'''
        return 'domain={0} {1}'.format(query, data)


class WhoisHttpHandler():

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
        if self._api_user is not None:
            # We have already checked to ensure password is valid.
            site_password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            site_password_mgr.add_password(realm=None,
                                           uri=self._url,
                                           user=self._api_user,
                                           passwd=self._api_password)
            site_basicauth_handler = urllib2.HTTPBasicAuthHandler(site_password_mgr)
            site_digestauth_handler = urllib2.HTTPDigestAuthHandler(site_password_mgr)
            handlers.extend([site_basicauth_handler, site_digestauth_handler])
    
        # Debugging
        #handlers.extend(urllib2.HTTPHandler(debuglevel=1))
        
        return urllib2.build_opener(*handlers)
    

class WhoisDomaintools(WhoisBase, WhoisHttpOptions, WhoisHttpHandler):
    '''Run a WHOIS query against domaintools.com API.'''
        
    # Formats require an argument in the query string.
    # HTML is not supported as it complicates parsing of the output.
    _formats = {'json': None,
               'xml': 'xml'}
    
    def __init__(self, *args, **kwargs):
        super(WhoisDomaintools, self).__init__(*args, **kwargs)
        
        # Hardcoded attributes (may be required for CLI options processing).
        self._realm = 'proxy'  # Used to retrieve API credentials.

        # Process CLI options
        self.set_options(*args, **kwargs)

        # Dynamic attributes (can only be set after CLI options are processed).
        if not getattr(self, '_host', False):
            # Fall back to using freedomaintools.com if host not provided.
            setattr(self, '_host', 'freeapi.domaintools.com')
    
    def prepare_query(self, query):
        '''Prepare the query. Credentials must have been retrieved
        before this function is called.
        
        Arguments:
        - query: A string representing the domain name.
        '''

        self._query = None
        self._url = 'http://{0}'.format(self._host)
        self._uri = '/'.join(['/v1', query, 'whois'])
        
        # TODO: Move all this validation to modular input validation routine.
        if self._api_password is None:
            raise Exception('API key could not be retrieved.')
        elif self._proxy_user and not (self._proxy_server and self._proxy_port):
            raise Exception('Proxy user specified without valid proxy server and/or port.')
        elif self._proxy_user and not self._proxy_password:
            raise Exception('Proxy user credential could not be retrieved.')
        else:            
            timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            signature = hmac.new(self._api_password,
                                 ''.join([self._api_user, timestamp, self._uri]),
                                 digestmod=hashlib.sha1).hexdigest()
            
            self._query = '{0}{1}?api_username={2}&signature={3}&timestamp={4}'.format(
                self._url,
                self._uri,
                self._api_user,
                signature,
                timestamp)
                
            format_arg = self._formats.get(self._format)

            if format_arg:
                self._query += '&format=' + format_arg 

    def run(self, query):
        
        self.prepare_query(query)

        if self._debug:
            import pprint
            print 'ERRORS'
            pprint.pprint(self._errors)
            print 'OPTIONS'
            pprint.pprint(self.__dict__)

        opener = self.buildOpener()
        urllib2.install_opener(opener)
        
        # Perform the query
        request = urllib2.Request(self._query)
        content = None

        # Since we want all of the queried domains to show up in the "whois"
        # index as "newly seen domains" regardless of the success/failure of the
        # query, we catch ALL exceptions here. If JSON content is returned by the API,
        # it will be formatted in the format() routine below. Some HTTP error codes
        # will actually return content that includes an error message and those
        # are handled by treating the error code as the response.
        
        try:
            response = urllib2.urlopen(request, timeout=self.TIMEOUT)
            content = response.read()
        except urllib2.HTTPError as e:
            self._logger.exception('Caught HTTPError when querying %s: code=%s exc=%s', query, e.code, e)
            if hasattr(e, 'read'):
                content = e.read()
        except urllib2.URLError as e:
            self._logger.exception('Caught URLError when querying %s: reason=%s exc=%s', query, e.reason, e)
            if hasattr(e, 'read'):
                content = e.read()
        except Exception as e:
            # None will be returned as content for handling by format() 
            self._logger.exception('Caught unknown exception when querying %s: exc=%s', query, e)
        
        if content is None:
            # None will be returned as content for handling by format().
            self._logger.error('No content returned when querying %s', query)

        return content
    
    def format(self, query, resolved_query, data):
        '''Format the data produced by this handler for use as a Splunk event.'''
        
        # Note the double braces used to include literal brackets {} in the JSON
        # output - this is required to use the format() method later on.
        default_output = '{{ "error" : {{ "message":"{0}" }} }}'
        
        try:
            obj = json.loads(data)
        except TypeError:
            msg = "JSON parsing failed for query {0}".format(query)
            obj = json.loads(default_output.format(msg))
            self._logger.error(msg)
        except Exception:
            msg = "Unexpected exception when parsing query {0}".format(query)
            obj = json.loads(default_output.format(msg))
            self._logger.error(msg)

        obj['domain'] = query
        if resolved_query:
            obj['resolved_domain'] = resolved_query                
        return json.dumps(obj, sort_keys=True)
