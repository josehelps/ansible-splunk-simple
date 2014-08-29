import ConfigParser
import os
import socket
from splunk.clilib import bundle_paths
from splunk.clilib import cli_common


def is_pool_member():
    '''Returns True if this server is a member of a search head pool.'''
    return cli_common.getConfKeyValue('server', 'pooling', 'state') == 'enabled'


def get_pool_members():
    '''Return the members of a search head pool.'''
    ss = bundle_paths.get_shared_storage()
    try:
        cfg = ConfigParser.ConfigParser()
        cfg.read(os.path.join(ss, 'etc', 'pooling', 'pooling.ini'))
        members = dict(cfg.items('members'))
        return members
    except ConfigParser.Error:
        return {}


def is_pool_master(master_name=None):
    '''Detect whether this server's name matches the master_name.
    We check both the serverName AND the hostname for a match.
    Modular inputs will pass in the hostname, which may differ from the
    server name.
    
    Note: if serverName and the list of peers are mismatched, this will cause the
    modular input not to execute. 
    '''

    server_name = cli_common.getConfKeyValue('server', 'general', 'serverName')
    hostname = socket.gethostname()
    if master_name:
        return master_name == server_name or master_name == hostname
    else:
        # See if this server is alphabetically lowest among all the peers. If 
        # so, execute on this system. Peers are listed in pooling.ini on the
        server_names = get_pool_members()
        first_server_name = sorted(server_names.keys())[0]
        try:

            return server_name == first_server_name or hostname == first_server_name
        except Exception:
            return False


def should_execute(master_host=None):
    '''Determine if a modular input should execute on this host. Execute in
    two conditions:

        1. We are in SHP configuration and master_host matches our hostname
        or server name. If master_host is undefined or empty, do not execute, but warn.
        2. We are not in SHP configuration. The master_host setting is ignored.

    Returns a tuple (boolean_status, string_msg) indicating whether this host
    should execute the modular input or not, and the reason.
    '''

    # If/else logic is slightly complex to permit return of specific error
    # messages to the caller.  Assume SHP not enabled until proven otherwise.    
    rv = (True, 'Search head pooling not enabled. Modular input execution will proceed on this host.')
    if is_pool_member():
        if master_host:
            # Master host was defined in the inputs.conf stanza.
            if is_pool_master(master_host):
                rv = (True, 'Master host matches ({0}). Modular input execution will proceed on this host.'.format(master_host))
            else:
                rv = (False, 'Master host does not match ({0}). Modular input will not be executed.'.format(master_host))
        else:
            # Try to select master host alphabetically.
            if is_pool_master():
                rv = (True, 'Selecting this search head pool member as master host based on alphabetical ordering ({0}). Modular input execution will proceed on this host.')
            else:
                rv = (False, 'Not selecting this search head pool member as master host based on alphabetical ordering ({0}). To override, define master_host in inputs.conf.')
    else:
        pass

    return rv
