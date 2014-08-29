'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import abc
import gzip
import StringIO
import struct
import sys
import urllib
import urllib2


class GzipHandler(object):
    '''Class for handling gzip-formatted string content.'''

    # Error messages
    ERR_INVALID_FORMAT = 'File is not gzip format.'
    ERR_SIZE_MISMATCH = 'Gzip file size does not match actual.'

    def __init__(self):
        pass

    @classmethod
    def checkFormat(self, data):
        '''Take a string and validate whether it is in gzip
           format. 
        '''
        # Check for gzip header.
        # Bytes 0 and 1 should be (per RFC 1952):
        # ID1 = 31 (0x1f, \037), ID2 = 139 (0x8b, \213)
        return data[0:2] == '\037\213'

    @classmethod
    def decompress(self, data):
        '''Decompress a string containing gzip-compressed data,
           performing basic validation. Returns the decompressed
           data or raises ValueError with an error string.
        '''

        # 1 - Check format.
        if not self.checkFormat(data):
            raise ValueError(self.ERR_INVALID_FORMAT)

        # 2 -- Read length of file from last four bytes of data.
        # This should be the size of the uncompressed data mod 2^32
        # Note that unpack() always returns a tuple even for one item
        sizeInt, = struct.unpack('i', data[-4:])

        # 3 -- Decompress the string
        decompressor = gzip.GzipFile(fileobj=StringIO.StringIO(data), mode='rb')
        text = decompressor.read()

        # 4 -- Check decompressed size.
        if len(text) != sizeInt:
            raise ValueError(self.ERR_SIZE_MISMATCH)

        return text


class ProtocolHandler(object):
    '''Abstract base class for protocol handlers.'''
    __metaclass__ = abc.ABCMeta

    def __init__(self, sessionKey, **kwargs):
        # Save references to logger and session key.
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
    '''Class for holding options commonly used by an HTTP(S)-based API.'''

    def __init__(self, *args, **kwargs):
        super(HttpProtocolHandlerOptions, self).__init__(*args, **kwargs)

    def set_options(self, *args, **kwargs):

        valid_keys = ['app', 'owner', 'proxy_port', 'proxy_server', 'proxy_user', 'proxy_password', 'proxy_realm', 'location', 'timeout']
        for k in valid_keys:
            setattr(self, '_' + k, kwargs.get(k, None))


class HttpProtocolHandler(ProtocolHandler, HttpProtocolHandlerOptions):

    def __init__(self, sessionKey, **options):
        # Save reference to session key.
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

        # Debugging
        #handlers.extend([urllib2.HTTPHandler(debuglevel=1)])

        return urllib2.build_opener(*handlers)

    def format_output(self, output):
        # Decompress the output if the file is gzip/zlib format
        if GzipHandler.checkFormat(output):
            try:
                return GzipHandler.decompress(output)
            except ValueError:
                # Exception while decompressing gzip content
                raise
        else:
            return output

    def format_query(self, query):
        assert isinstance(query, basestring), "Query was not a string."
        return ProtocolHandler.format_query(self, query)

    def run(self, query, data=None, headers=None, return_errors=[]):
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
                # Probably caught TypeError when processing POST arguments for query.
                data = None
        else:
            data = None

        opener = self.buildOpener()
        urllib2.install_opener(opener)

        # Perform the query
        request = urllib2.Request(query, data)
        # Add headers if requested.
        if headers:
            for (k, v) in headers:
                request.add_header(k, v)

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
        except (urllib2.HTTPError, urllib2.URLError) as e:
            if e.code in return_errors:
                content = e.read()
            else:
                raise
        except Exception as e:
            raise

        if content:
            return self.format_output(content)
        else:
            # No content returned.
            pass
        
        return None
