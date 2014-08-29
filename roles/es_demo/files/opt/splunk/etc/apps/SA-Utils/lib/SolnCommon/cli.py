'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import argparse
import getpass
import sys

import splunk

from .error import CliErrors


def get_default_args(**kwargs):
    '''Return an ArgumentParser object suitable for use as a parent parser.
    This is useful for rapid specification of common command-line arguments.
    
    For instance:
    
        parent_parser = cli.get_default_args(**{
            'namespace': 'SA-ThreatIntelligence',
            'owner': 'nobody',
            'user': None,
            'password': None,
            'interactive': False,
            'query': None,
            'sourcetype': 'whois',
            'index': 'main'
        })
        
    
    Currently arguments will take two forms:
    
    - the first letter of the extended name
    - the extended name.
    
    In the case of conflict, only the long name will be used. If two
    arguments with identical long names are specified, this is regarded
    as an error.
    '''

    parser = argparse.ArgumentParser(add_help=False)
    
    validargs = {
        'index': {'dest': 'index',
                  'type': str,
                  'action': 'store',
                  'help': 'A Splunk index.'},
        'interactive': {'dest': 'interactive',
                  'action': 'store_true',
                  'help': 'Run interactively (do not use passAuth value from splunkd).'},
        'namespace': {'dest': 'namespace',
                  'type': str,
                  'action': 'store',
                  'help': 'A Splunk namespace.'},
        'owner': {'dest': 'owner',
                  'type': str,
                  'action': 'store',
                  'help': 'A Splunk user.'},
        'password': {'dest': 'password',
                  'type': str,
                  'action': 'store',
                  'help': 'A valid Splunk user password (for command-line authentication only).'},
        'query': {'dest': 'query',
                  'type': str,
                  'action': 'store',
                  'help': 'A query string.'},
        'sourcetype': {'dest': 'sourcetype',
                  'type': str,
                  'action': 'store',
                  'help': 'A Splunk sourcetype to be assigned to any events generated.'},
        'user': {'dest': 'user',
                  'type': str,
                  'action': 'store',
                  'help': 'A valid Splunk user name (for command-line authentication only).'},
        }
    
    for k, v in kwargs.items():
        if k in validargs:
            parser_args = ['-' + k[0], '--' + k]
            parser_kwargs = validargs.get(k)
            parser_kwargs.update({'default': v})
            try:
                parser.add_argument(*parser_args, **parser_kwargs)
            except argparse.ArgumentError:
                parser_args = ['--' + k]
                parser.add_argument(*parser_args, **parser_kwargs)

    return parser


def get_output_prefixes():
    '''Return a set of prefixes useful for sending nicely-formatter output to the CLI
    or to the Splunk messaging system.
    
    @return: A tuple of (output_filehandle, info_prefix, err_prefix)
    '''
    
    if not sys.stdin.isatty():
        # Running as Splunk search command.
        # 1. Log messages go to STDERR where they will become search banner messages.
        # 2. Messages must usually be prefixed with WARN level or higher
        #    to be displayed.
        return sys.stderr, 'WARN', 'ERROR'
    else:
        # Running interactively.
        # 1. Correct for misleading output prefixes.
        return sys.stdout, '', ''


def get_session_key(options=None):
    '''Return a session key from either the CLI arguments provided
    in options, or from the value provided on STDIN by passAuth.
    
    @param options: A parsed ArgumentParser namespace.
    
    This is useful for obtaining a session key value in scripts
    that can be run both from the CLI and as Splunk search commands.
    
    Note that for some functions is is important to retrieve the 
    sessionKey value in the __main__ function.
    '''

    sessionKey = ''
    
    if not options:
        # Set options if none provided.
        options = argparse.Namespace(**{'interactive': False, 'user': None, 'password': None})

    if not sys.stdin.isatty() or options.interactive:
        # Try to retrieve sessionKey from splunkd
        sessionKey = sys.stdin.readline().strip()

    if len(sessionKey) == 0:
        # No session key was provided. Try command-line parameters.
        if options.user and options.password:
            try:
                sessionKey = splunk.auth.getSessionKey(options.user, options.password)
            except splunk.AuthenticationFailed:
                sys.stderr.write(CliErrors.ERR_NO_CLI_AUTH_INFO + '\n')
                sys.exit(1)
        elif options.user:
            # If options.pwd was not provided, prompt for password.
            try:
                password = getpass.getpass("Splunk password: ")
                sessionKey = splunk.auth.getSessionKey(options.user, password)
            except splunk.AuthenticationFailed:
                sys.stderr.write(CliErrors.ERR_NO_CLI_AUTH_INFO + '\n')
                sys.exit(1)
        else:
            # If neither options.user nor options.pwd was not provided, prompt
            # for both.
            try:
                user = raw_input("Splunk user: ")
                password = getpass.getpass("Splunk password: ")
                sessionKey = splunk.auth.getSessionKey(user, password)
            except splunk.AuthenticationFailed:
                # All authentication methods failed. This usually
                # indicates that passAuth was not specified, otherwise
                # failure would have occurred in one of the previous two
                # cases.
                sys.stderr.write(CliErrors.ERR_NO_PASSAUTH_INFO + '\n')
                sys.exit(1)
    else:
        # passAuth provided the session key.
        pass
        
    return sessionKey
