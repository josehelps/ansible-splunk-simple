'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import re
import socket


def is_valid_ip(value):
    '''Validate an IP address.'''
    rx = re.compile('^(([0-1]\d{0,2}|2[0-4]\d|25[0-5]|\d{0,2})\.){3}([0-1]\d{0,2}|2[0-4]\d|25[0-5]|\d{0,2})$')
    try:
        return rx.match(value.strip())
    except AttributeError:
        # Value was not a string
        return False


def resolve(addr):
    '''Try to resolve an IP to a name, returning False on common failures.
    Respects the socket.timeout value of the calling application.
    
    @param addr: An IP address.
    '''
    if is_valid_ip(addr):
        try:
            name, addresslist, aliaslist = socket.gethostbyaddr(addr)
            return name
        except socket.gaierror:
            # [Errno 8] nodename nor servname provided, or not known
            pass
        except socket.herror:
            # [Errno 1] Unknown host
            pass
        except socket.timeout:
            # Timeout.
            pass
        except TypeError:
            # Should never get here; invalid data type such as int passed to
            # gethostbyaddr.
            pass
        
        return False