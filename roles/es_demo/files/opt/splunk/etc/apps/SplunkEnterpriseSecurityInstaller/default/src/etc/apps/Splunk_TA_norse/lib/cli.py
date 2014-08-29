'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import argparse
import getpass
import sys

import splunk


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

    if not sys.stdin.isatty():
        # Try to retrieve sessionKey from splunkd
        sessionKey = sys.stdin.readline().strip()

    if len(sessionKey) == 0:
        # No session key was provided. Try command-line parameters.
        if options.user and options.password:
            try:
                sessionKey = splunk.auth.getSessionKey(options.user, options.password)
            except splunk.AuthenticationFailed:
                sys.stderr.write('No authentication information provided.\n')
                sys.exit(1)
        elif options.user:
            # If options.pwd was not provided, prompt for password.
            try:
                password = getpass.getpass("Splunk password: ")
                sessionKey = splunk.auth.getSessionKey(options.user, password)
            except splunk.AuthenticationFailed:
                sys.stderr.write('No authentication info provided.\n')
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
                sys.stderr.write('No authentication info provided.\n')
                sys.exit(1)
    else:
        # passAuth provided the session key.
        pass

    return sessionKey
