import argparse
import getpass
import itertools
import json
import numbers
import os
import re
import sys
import textwrap
import time


APPNAME = 'Splunk_TA_norse'
import splunk
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', APPNAME, 'lib']))
from credentials import CredentialManager
from log import setup_logger
from protocols import HttpProtocolHandler

logger = setup_logger(os.path.basename(__file__))


def get_session_key(options=None):
    '''Return a session key from either the CLI arguments provided
    in options, or from the value provided on STDIN by passAuth.

    @param options: A parsed ArgumentParser namespace.

    This is useful for obtaining a session key value in scripts that can be run
    both from the CLI and as Splunk search commands or scripted inputs.

    Note that for some scripts is is important to retrieve the
    sessionKey value in the __main__ function.
    '''

    sessionKey = ''

    if not options:
        # Set options if none provided.
        options = argparse.Namespace(**{'splunkuser': None, 'splunkpass': None})

    if not sys.stdin.isatty():
        # This is either a scripted input or a custom search command. If the 
        # former the session key will be usable as-is. If not, passAuth provides
        # the session key in this format (on a single line, formatted here for
        # readability)
        #
        # 'authString:
        #  <auth>
        #    <userId>admin</userId>
        #    <username>admin</username>
        #    <authToken>0865ce5c1ee84b417ed378d53048c4fe</authToken>
        #  </auth>'
        #
        sessionKey = sys.stdin.readline().strip()
        if sessionKey.startswith('authString'):
            try:
                sessionKey = re.search('authToken>([^>]+)<\/authToken', sessionKey).groups()[0]
            except Exception:
                logger.exception('Authentication failed: session key could not be retrieved via passauth.\n')
                raise
        else:
            # Assume session key is usable.
            pass

    if len(sessionKey) == 0:
        # No session key was provided. Try command-line parameters.
        if options.splunkuser and options.splunkpass:
            try:
                sessionKey = splunk.auth.getSessionKey(options.splunkuser, options.splunkpass)
            except splunk.AuthenticationFailed:
                logger.exception('Authentication failed.\n')
                raise
        elif options.user:
            # If options.pwd was not provided, prompt for password.
            try:
                splunkpass = getpass.getpass("Splunk password: ")
                sessionKey = splunk.auth.getSessionKey(options.splunkuser, splunkpass)
            except splunk.AuthenticationFailed:
                logger.exception('Authentication failed.\n')
                raise
        else:
            # If neither options.user nor options.pwd was not provided, prompt
            # for both.
            try:
                splunkuser = raw_input("Splunk user: ")
                splunkpass = getpass.getpass("Splunk password: ")
                sessionKey = splunk.auth.getSessionKey(splunkuser, splunkpass)
            except splunk.AuthenticationFailed:
                # All authentication methods failed. This usually
                # indicates that passAuth was not specified, otherwise
                # failure would have occurred in one of the previous two
                # cases.
                logger.exception('Authentication failed.\n')
                raise
    else:
        # Already retrieved session key from passAuth/passauth.
        pass

    return sessionKey


def get_options(argv=None):
    desc = '''Script for executing Norse IPViking query.'''

    parser = argparse.ArgumentParser(description=textwrap.dedent(desc),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('ip',
        type=str,
        action='store',
        help='The IP for the IPViking query.')

    parser.add_argument('-f', '--format',
        dest='format',
        type=str,
        action='store',
        help='The output format. Should be one of "full", "short", or "json".',
        default="full")

    parser.add_argument('-l', '--location',
        dest='location',
        type=str,
        action='store',
        help='The URL to download.',
        default='http://us.api.ipviking.com/api/')

    parser.add_argument('-p', '--proxy_user',
        dest='proxy_user',
        type=str,
        action='store',
        help='The name of the Splunk stored credential that contains the proxy user, if required.')

    parser.add_argument('-c', '--cred', '-credential',
        dest='user',
        type=str,
        action='store',
        help='The name of the Splunk stored credential that contains the Norse API key.',
        default='norse_ipviking')
    
    parser.add_argument('--splunkpass',
        dest='splunkpass',
        type=str,
        action='store',
        help='The password of the Splunk user executing the script as. For interactive command-line use only.')

    parser.add_argument('--splunkuser',
        dest='splunkuser',
        type=str,
        action='store',
        help='The name of the Splunk user to execute the script as. For interactive command-line use only.')

    return parser.parse_args(argv)


def get_credentials(options, session_key):
    '''Get credentials for remote API access and proxy authentication,
    if requested. Exits if credentials cannot be retrieved.
    '''

    credmgr = CredentialManager(session_key)

    if options.user:
        try:
            password = credmgr.get_clear_password(options.user, '', APPNAME, 'nobody')
            if password:
                setattr(options, 'password', password)
            else:
                raise ValueError('API credential was empty.')
        except splunk.ResourceNotFound:
            logger.exception('Could not retrieve user credentials.')
            raise
            
    if options.proxy_user:
        try:
            password = credmgr.get_clear_password(options.proxy_user, '', APPNAME, 'nobody')
            if password:
                setattr(options, 'proxy_password', password)
            else:
                raise ValueError('Proxy credential was empty.')
        except splunk.ResourceNotFound:
            logger.exception('Could not retrieve proxy credentials.')
            raise

    return options


def print_options(options):
    print(options)    


def get_handler(name):
    '''Return a protocol handler by name.'''
    PROTOCOL_HANDLERS = {'http': HttpProtocolHandler,
                         'https': HttpProtocolHandler}
    return PROTOCOL_HANDLERS.get(name, None)


def perform_download(options, session_key):

    content = None
    
    # Set timeout
    setattr(options, 'timeout', 30)
    
    try:
        handler_name = options.location.split('://')[0]
        handler_cls = get_handler(handler_name)
        handler = handler_cls(session_key, **vars(options))
        
        if handler:
            post_data = {'apikey': options.password,
                         'method': 'ipview',
                         'ip': options.ip}
            headers = [('Accept', 'application/json')]
            content = handler.run(options.location, data=post_data, headers=headers, return_errors=[302])
        else:
            raise ValueError('Could not retrieve protocol handler.')
    except Exception:
        raise

    return content


def flatten(value, accum):
    '''Function for flattening IPViking JSON to Splunk fields. Does not convert 
    NoneType values.'''
    output = {}
    if isinstance(value, (basestring, numbers.Number)):
        output[accum] = value
    elif isinstance(value, dict):
        for subk, subv in value.iteritems():
            values = flatten(subv, '')
            for k, v in values.iteritems():
                output['.'.join(itertools.ifilter(lambda x: x, [accum, subk, k]))] = v
    elif isinstance(value, list):
        for num, subv in enumerate(value):
            values = flatten(subv, '')
            for k, v in values.iteritems():
                output['.'.join(itertools.ifilter(lambda x: x, [accum, str(num), k]))] = v
    return output


def flatten_to_mv(value, accum):
    '''Function for flattening IPViking JSON to Splunk fields. Does not convert 
    NoneType values.'''
    output = {}
    if isinstance(value, (basestring, numbers.Number)):
        output[accum] = value
    elif isinstance(value, dict):
        for subk, subv in value.iteritems():
            values = flatten_to_mv(subv, '')
            for k, v in values.iteritems():
                output['.'.join(itertools.ifilter(lambda x: x, [accum, subk, k]))] = v
    elif isinstance(value, list):
        for subv in value:
            values = flatten_to_mv(subv, '')
            for k, v in values.iteritems():
                curr = output.setdefault(k, [])
                curr.append(v)
    return output


def output_to_mv(data):

    rv = {}
    for k, v in data.iteritems():
        if isinstance(v, list):
            rv[k] = map(str, v)
        else:
            rv[k] = str(v)

    return rv


if __name__ == "__main__":

    # Retrieve script options and session key.
    try:
        options = get_options(sys.argv[1:])
        session_key = get_session_key(options)

        # Retrieve credentials from secure storage.
        options = get_credentials(options, session_key)

        # Perform the download and retrieve results as JSON.
        results = perform_download(options, session_key)

        # Format and output as Splunk results.
        output = json.loads(results)

        if not options.format or options.format == 'full':
            output = flatten(output['response'], '')
            splunk.Intersplunk.outputResults([output])
        elif options.format == 'short':
            output = flatten_to_mv(output['response'], '')
            splunk.Intersplunk.outputResults([output_to_mv(output)])
        elif options.format == 'json':
            splunk.Intersplunk.outputResults([{'_time': time.time(), 'response': results}])

    except Exception as exc:
        logger.exception('Error when processing IPViking results.')
        errorResults = splunk.Intersplunk.generateErrorResults(exc)
        splunk.Intersplunk.outputResults(errorResults)