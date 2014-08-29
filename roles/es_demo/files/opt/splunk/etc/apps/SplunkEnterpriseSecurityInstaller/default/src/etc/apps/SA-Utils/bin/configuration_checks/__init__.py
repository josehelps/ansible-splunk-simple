import itertools
import logging
import os
import re
import sys

import splunk
import splunk.entity

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.limits import get_limits
from SolnCommon.models import InputStatus
from SolnCommon.models import SplunkLookupTableFile
from SolnCommon.models import SplunkLookupTransform
from SolnCommon.models import SplunkRole

MSG_OK = "No configuration errors found."

## confcheck_default_search_indexes messages
MSG_FMT_DEFAULT_SEARCH_INCLUDES_SUMMARY_INDEXES = "The list of indexes to be searched by default for the admin role includes the following summary indexes which may cause performance problems: {}"

## confcheck_default_search_all_non_internal messages
MSG_DEFAULT_SEARCH_INCLUDES_INTERNAL_INDEXES = "The list of indexes to be searched by default for the admin role includes 'All non-internal indexes' which may cause performance problems"

## confcheck_lookup_table_size messages
MSG_FMT_LOOKUP_TABLE_SIZE = 'msg="{0}" file="{1}" size="{2}" limit="{3}"'
MSG_LOOKUP_TABLE_SIZE_EXCEEDED = "A lookup table used in a CIDR or WILDCARD definition exceeds the maximum allowable value"
MSG_LOOKUP_TABLE_SIZE_OK = "Lookup table size within bounds"

## confcheck_script_errors messages
MSG_FMT_INPUT_MSG = 'msg="{0}" input="{1}" stanza="{2}" status="{3}"'
MSG_INPUT_STATUS_ACTIVE = 'A script is still running'
MSG_INPUT_STATUS_FAIL = 'A script exited abnormally'
MSG_INPUT_STATUS_SUCCESS = 'A script exited normally'
MSG_INPUT_STATUS_UNKNOWN = 'A script is in an unknown state'
MSG_INPUT_STATUS_WAIT = "A script has not yet executed"


def confcheck_default_search_indexes(*args, **kwargs):
    """
    This function checks to make sure that no summary indexes are in the list 
    of default search indexes for the admin role.
    """
    
    messages = []

    # Indexes that should not be included in the default list for the "admin" role.
    problem_rx = re.compile("^(.*summary[0-9]?|notable)$")
    
    # Get the default search indexes list for the admin role
    role_id = SplunkRole.build_id('admin', None, None)
    admin_role = SplunkRole.get(role_id, kwargs.get('sessionKey'))

    # Check the indexes
    problems = {idx for idx in itertools.chain.from_iterable([problem_rx.findall(i) for i in admin_role.srchIndexesDefault])}

    if problems:
        messages.append((logging.ERROR, MSG_FMT_DEFAULT_SEARCH_INCLUDES_SUMMARY_INDEXES.format(','.join(problems))))
    else:
        messages.append((logging.DEBUG, MSG_OK))
    return messages


def confcheck_default_search_all_non_internal(*args, **kwargs):
    """
    Checks to make sure that the list of default search indexes for the admin 
    role does not include all non-internal indexes.
    """

    messages = []
    # Get the default search indexes list for the admin role
    role_id = SplunkRole.build_id('admin', None, None)
    admin_role = SplunkRole.get(role_id, kwargs.get('sessionKey'))

    if "*" in admin_role.srchIndexesDefault:
        messages.append((logging.ERROR, MSG_DEFAULT_SEARCH_INCLUDES_INTERNAL_INDEXES))
    else:
        messages.append((logging.DEBUG, MSG_OK))
    return messages


def confcheck_lookup_table_size(*args, **kwargs):
    '''Validate that lookup tables with CIDR or WILDCARD fields defined don't
    exceed max_memtable_bytes in size.
    '''
    key = kwargs.get('sessionKey')
    messages = []
    
    # Retrieve all WILDCARD or CIDR transforms
    transforms_srch = 'match_type="*CIDR*" OR match_type="*WILDCARD*"'
    transforms = SplunkLookupTransform.search(transforms_srch, sessionKey=key)
    
    # Retrieve the file names associated with each transform.
    lookup_table_files_srch = ' OR '.join(['name={}'.format(i.filename) for i in transforms])
    lookup_table_files = SplunkLookupTableFile.search(lookup_table_files_srch, sessionKey=key)
    
    # Get limits.conf stanza for lookups.
    limits = get_limits('lookup', key)

    for lookup_table_file in lookup_table_files:
        if os.path.isfile(lookup_table_file.path):
            size = os.stat(lookup_table_file.path).st_size
            if limits.max_memtable_bytes < size:
                messages.append((logging.ERROR, MSG_FMT_LOOKUP_TABLE_SIZE.format(
                    MSG_LOOKUP_TABLE_SIZE_EXCEEDED,
                    lookup_table_file.name, 
                    size, 
                    limits.max_memtable_bytes)))
            else:
                # size OK.
                messages.append((logging.DEBUG, MSG_FMT_LOOKUP_TABLE_SIZE.format(
                    MSG_LOOKUP_TABLE_SIZE_OK,
                    lookup_table_file.name, 
                    size, 
                    limits.max_memtable_bytes)))
        else:
            # No such lookup table file - this is not a warning we handle
            # as the user is typically warned about this at search time.
            pass

    return messages


def confcheck_script_errors(*args, **kwargs):
    """
    This function checks scripted and modular inputs for error codes that might
    indicate a crash.
    """
    
    messages = []

    modular_input_idval = InputStatus.build_id('ModularInputs:modular input commands', None, None)
    scripted_input_idval = InputStatus.build_id('ExecProcessor:exec commands', None, None)
    modular_input_query = InputStatus.get(id=modular_input_idval, sessionKey=kwargs.get('sessionKey'))
    scripted_input_query = InputStatus.get(id=scripted_input_idval, sessionKey=kwargs.get('sessionKey'))
    modular_inputs = modular_input_query.inputs
    scripted_inputs = scripted_input_query.inputs

    # Sample of normal script exit status (use_single_instance==True):
    # {'/opt/splunk/etc/apps/SA-NetworkProtection/bin/whois.py': {'exit status description': 'exited with code 0',
    #  'time closed': '2013-05-10T12:25:21-0700',
    #  'time opened': '2013-05-10T12:25:21-0700'},
    # Sample of normal script exit status (use_single_instance==False - note the stanza name):
    # '/opt/splunk/etc/apps/SA-Utils/bin/app_imports_update.py (app_imports_update://update_es)': {'exit status description': 'exited with code 0',
    #  'time closed': '2013-05-10T12:25:24-0700',
    #  'time opened': '2013-05-10T12:25:21-0700'}}

    # String constants
    STATUS_KEY = 'exit status description'
    STARTED_KEY = 'time opened'
    STOPPED_KEY = 'time closed' 
    
    # Regular expressions
    stanza_rx = re.compile('^(\S+)(?:(?:\s+\()([^\(]+)(?:\))){0,1}$')
    status_rx = re.compile('^exited\swith\scode\s(\d+)$')

    for name, state in itertools.chain(modular_inputs.iteritems(), scripted_inputs.iteritems()):

        # These must be set inside the loop for correctness.
        input_name = None
        stanza = None
        status = None

        # parse stanza name via regex
        stanza_match = stanza_rx.match(name)
        if stanza_match:
            input_name, stanza = stanza_match.groups()                
        else:
            # fall back to just the name
            input_name = name
        if not stanza:
            stanza = 'default'
        
        if state:
            
            # Get the open and close times for the input.
            status = state.get(STATUS_KEY, '')
            started = state.get(STARTED_KEY, None)
            stopped = state.get(STOPPED_KEY, None)

            # Get the status code.
            status_match = status_rx.match(status)
            if status_match:
                # The script has exited with a code.
                status_code = status_match.groups()[0]
            
                # Scripts are assumed to have exited "normally" if the exit code is
                # 0. If the exit code cannot be determined, an error is raised.
                if status_code != '0':
                    # Format the message
                    messages.append((logging.ERROR, MSG_FMT_INPUT_MSG.format(
                        MSG_INPUT_STATUS_FAIL,
                        input_name, 
                        stanza, 
                        status)))
                else:
                    # The input has executed normally.
                    messages.append((logging.DEBUG, MSG_FMT_INPUT_MSG.format(
                        MSG_INPUT_STATUS_SUCCESS,
                        input_name, 
                        stanza, 
                        status)))
            elif status:
                # The script has exited with a status, but we could not determine
                # an exit code. Assume this is an error and return the status.
                messages.append((logging.ERROR, MSG_FMT_INPUT_MSG.format(
                    MSG_INPUT_STATUS_FAIL,
                    input_name, 
                    stanza, 
                    status)))
            elif started and not stopped:
                # If the script has not exited (no "exited with code" key), but
                # has started, assume that the script is running.
                messages.append((logging.DEBUG, MSG_FMT_INPUT_MSG.format(
                    MSG_INPUT_STATUS_ACTIVE,
                    input_name, 
                    stanza, 
                    'running')))
            else:
                # Script is in an unknown state (no exit code, not started, maybe stopped)
                messages.append((logging.ERROR, MSG_FMT_INPUT_MSG.format(
                    MSG_INPUT_STATUS_UNKNOWN,
                    input_name, 
                    stanza, 
                    'unknown')))
        else:
            # Script has not been executed yet (no state).
            messages.append((logging.DEBUG, MSG_FMT_INPUT_MSG.format(
                MSG_INPUT_STATUS_WAIT,
                input_name, 
                stanza, 
                'not yet executed')))

    return messages
