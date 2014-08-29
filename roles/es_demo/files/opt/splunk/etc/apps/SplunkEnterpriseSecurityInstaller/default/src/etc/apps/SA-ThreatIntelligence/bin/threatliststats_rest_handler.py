import logging
import logging.handlers
import os
import re
import sys
import json

import splunk.admin as admin
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import splunk.rest
import splunk.clilib.cli_common

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.models import InputStatus

## Setup the logger
def setup_logger():
    """
    Sets up a logger for the REST handler.
    """

    logger = logging.getLogger('threatliststats_rest_handler')
    # Prevent the log messages from being duplicated in the python.log 
    #     AuthorizationFailed
    logger.propagate = False 
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(
                    make_splunkhome_path(['var', 'log', 'splunk', 
                                          'threatliststats_rest_handler.log']), 
                                        maxBytes=25000000, backupCount=5)
    
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

class ThreatlistStatsRH(admin.MConfigHandler):
    '''
    ThreatlistStats REST handler.

    The ThreatlistStats REST handler aggregates data from the following 
    locations into a single REST endpoint for use with the Threat List Audit 
    dashboard:
        * "/services/data/inputs/threatlist" REST Endpoint
        * "/admin/inputstatus/ModularInputs:modular input commands" REST Endpoint
        * The python_modular_input.log log file by leveraging the following 
        search:
            - "search source=*python_modular_input.log index=_internal 
            download_task daysago=1 | search url=* | dedup stanza | 
            fields _raw"
        * File system information for downloaded threatlists and local 
        threatlists added as lookup tables. Acquired FS information 
        is as follows:
            - File Size (Bytes)
            - mtime
    '''
    ## admin.py constants
    REQUESTED_ACTIONS = {
        '1':     'ACTION_CREATE',
        '2':     'ACTION_LIST',
        '4':     'ACTION_EDIT',
        '8':     'ACTION_REMOVE',
        '16':    'ACTION_MEMBERS',
        '32':    'ACTION_RELOAD'
    }

    ## Permissions
    READ_CAPABILITY = 'list_threatliststats'

    def setup(self):
        logger.info('Setting up threatliststats_rest_handler')

        ## set read capability
        # self.setReadCapability(ThreatlistStatsRH.READ_CAPABILITY)

    def _retrieveThreatListData(self, confInfo):
        """
        This method queries the 'data/inputs/threatlist' endpoint and adds the 
        appropriate data to <tt>confInfo</tt>

        @param confInfo: The data structure containing the configuration 
        information for the REST endpoint.
        """

        unwanted_attributes = ['delim_regex', 'eai:acl', 'extract_regex', 
                               'fields', 'host', 'ignore_regex', 'index', 
                               'initial_delay', 'master_host', 'proxy_port', 
                               'proxy_server', 'proxy_user', 'site_user', 
                               'skip_header_lines', 'source', 'sourcetype', 
                               'target', 'timeout', 'retries', 'retry_interval'
                               ]

        response, content = splunk.rest.simpleRequest('data/inputs/threatlist',
                                getargs={'output_mode': 'json', 'count': '0'}, 
                                raiseAllErrors=True, 
                                sessionKey=self.getSessionKey())

        if response.status == 200:
            try:
                content = json.loads(content)
                for entry in content['entry']:
                    for item in entry['content']:
                        if item not in unwanted_attributes:
                            confInfo[entry['name']][item] = entry['content'][item]
            except Exception as e:
                logger.exception("Unable to parse the response from " +  
                                 "endpoint data/inputs/threatlist!")
        else:
            logger.warning('Received a ' + str(response.status) + 
                        ' response from the data/inputs/threatlist endpoint.')

    def _addModularInputsEndpointData(self, confInfo):
        """
        This method queries the 'admin/inputstatus/ModularInputs:modular input 
        commands' REST Endpoint and adds the appropriate data to 
        <tt>confInfo</tt>

        @param confInfo: The data structure containing the configuration 
        information for the REST endpoint.
        """

        # String constants
        STATUS_KEY = 'exit status description'
        THREATLIST_STANZA = 'threatlist://'

        modular_input_idval = InputStatus.build_id(
                                'ModularInputs:modular input commands', 
                                None, None)
        modular_input_query = InputStatus.get(id=modular_input_idval, 
                                              sessionKey=self.getSessionKey())
        modular_inputs = modular_input_query.inputs

        stanza_rx = r'(?<=\()threatlist\:\/\/\w+(?=\))'

        for name, state in modular_inputs.iteritems():
            # parse stanza name via regex
            stanza_match = re.search(stanza_rx, name)
            if stanza_match:
                stanza = stanza_match.group()
                input_name = str(stanza)[len(THREATLIST_STANZA):]

                confInfo[input_name]['stanza'] = stanza

                if state:
                    # Get the open and close times for the input
                    confInfo[input_name]['threatlist_script_status'] = \
                        state.get(STATUS_KEY, '')

    def _addFSInfo(self, confInfo):
        """
        This method adds FileSystem information from each downloaded threatlist 
        or local threatlist lookup table, and adds it to <tt>confInfo</tt>. 
        The information acquired is as follows:
            * File Size
            * mtime
        
        @param confInfo: The data structure containing the configuration 
        information for the REST endpoint.
        """
        lookup_regex = r'(?<=lookup\:\/\/)\w*\b'
        
        splunk_db = splunk.clilib.cli_common.splunk_db
        mod_inputs_path = os.path.join(splunk_db, 'modinputs', 'threatlist')
        
        threatlists = {}
        for threatlist in confInfo:
            if 'disabled' in confInfo[threatlist] and \
            not confInfo[threatlist]['disabled']:
                threatlists[threatlist] = {}
               
                ## If this is a local lookup file
                if 'url' in confInfo[threatlist] and 'lookup://' in \
                confInfo[threatlist]['url']: 
                    threatlists[threatlist]['is_lookup_table'] = True
                    lookup_name = re.search(lookup_regex, 
                                            confInfo[threatlist]['url']).group()
                                           
                    ## Retrieve lookup filename from data/transforms/lookups
                    response, content = splunk.rest.simpleRequest(('data/' + 
                        'transforms/lookups/' + lookup_name), 
                                                getargs={'output_mode': 'json', 
                                                         'count': '0'},
                        raiseAllErrors=True,
                        sessionKey=self.getSessionKey())
                   
                    threatlist_lookup_file = None
                    threatlist_file_path = None
                    if response.status == 200:
                        try:
                            content = json.loads(content)
                            if len(content['entry']) > 0:
                                threatlist_lookup_file = \
                                    content['entry'][0]['content']['filename']
                                app_context = content['entry'][0]['acl']['app']
                                threatlist_file_path = make_splunkhome_path(
                                        ['etc', 'apps', app_context,'lookups', 
                                         threatlist_lookup_file])
                                
                            if threatlist_file_path is None:
                                logger.warning("There is no file for " + 
                                               "lookup: " + 
                                               threatlist_file_path)
                        except Exception as e:
                            logger.exception("Unable to parse the response " + 
                                             "from endpoint data/transforms/" + 
                                             "lookups with search: " + search)

                    threatlists[threatlist]['threatlist_file_path'] = \
                        threatlist_file_path
                   
                    try:
                        threatlists[threatlist]['stats'] = \
                        os.stat(threatlists[threatlist]['threatlist_file_path'])
                    except Exception:
                        logger.warning('Unable to gather stats for: ' + 
                                       threatlist_file_path)
                ## Else if it isn't a local lookup file
                else: 
                    threatlists[threatlist]['threatlist_file_path'] = \
                        os.path.join(mod_inputs_path, threatlist)
                    threatlists[threatlist]['is_lookup_table'] = False
                    try:
                        threatlists[threatlist]['stats'] = os.stat(os.path.join(
                                                mod_inputs_path, threatlist))
                    except Exception:
                        logger.warning('Unable to gather stats for: ' + 
                                       os.path.join(mod_inputs_path, 
                                                    threatlist))

        for threatlist in threatlists:
            confInfo[threatlist]['is_lookup_table'] = \
            threatlists[threatlist]['is_lookup_table']
            if 'stats' in threatlists[threatlist]:
                confInfo[threatlist]['threatlist_file_path'] = \
                threatlists[threatlist]['threatlist_file_path']
               
                confInfo[threatlist]['threatlist_actual_file_size'] = \
                threatlists[threatlist]['stats'].st_size
               
                confInfo[threatlist]['threatlist_file_st_mtime'] = \
                threatlists[threatlist]['stats'].st_mtime

    def _addModInputsLogData(self, confInfo):
        """
        This method leverages the 'search/jobs/export' endpoint to run a search 
        that acquires the <tt>download_task</tt> log entries from the 
        <tt>*python_modular_input.log</tt> logs.
        It then adds this data to <tt>confInfo</tt>.

        @param confInfo: The data structure containing the configuration 
        information for the REST endpoint.
        """
        fieldRegex = {
            'stanza': r'(?<=stanza\=)\w*(?=\s)',
            'status': r'(?<=status\=)\".*\"(?=\s)',
        }

        search = ("search source=*python_modular_input.log index=_internal " + 
                  "download_task daysago=1 | search url=* | dedup stanza | " + 
                  "fields _raw")
    
        response, content = splunk.rest.simpleRequest('search/jobs/export', 
                                postargs={'search': search,
                                          'output_mode': 'raw',
                                          'count': '0'}, 
                                raiseAllErrors=True, 
                                sessionKey=self.getSessionKey())

        if response.status == 200:
            try:
                for row in content.split('\n')[:-1]:
                    meta_data, log_data = row.split(' | ')
                    stanza = re.search(fieldRegex['stanza'], log_data).group()
              
                    confInfo[stanza]['download_status'] = \
                        re.search(fieldRegex['status'], log_data).group()
                
            except Exception as e:
                if row:
                    logger.error('Row being processed at the time of the error: ' + 
                                 str(row))
                logger.exception('Unable to parse the content returned from ' + 
                                 'the search: "search source=*python_modular' + 
                                 '_input.log index=_internal download_task | ' +
                                 'search url=* | dedup stanza | fields _raw"')
        else:
            logger.warning('Received a ' + str(response.status) + 
                           ' response from the search/jobs/export endpoint.')
            logger.warning('Search Parameters: search="search source=' + 
                           '*python_modular_input.log index=_internal ' + 
                           'download_task | search url=* | dedup stanza | ' + 
                           'fields _raw", output_mode="raw"')

    def handleList(self, confInfo):
        """
        Handles listing of Threat List data.
        """
        ## Get requested action
        actionStr = str(self.requestedAction)
        if ThreatlistStatsRH.REQUESTED_ACTIONS.has_key(actionStr):
            actionStr = ThreatlistStatsRH.REQUESTED_ACTIONS[actionStr]

        logger.info('Entering %s' % (actionStr))

        ## Retrieve Threatlist Intel from the 
        ##     /services/data/inputs/threatlist endpoint--
        self._retrieveThreatListData(confInfo)

        ## Add data from "/admin/inputstatus/ModularInputs: modular 
        ##     input commands" endpoint
        self._addModularInputsEndpointData(confInfo)

        ## Add data from the *python_modular_inputs.log logs ....
        self._addModInputsLogData(confInfo)

        ## Obtain FS Information for each threat list with a file attribute -- 
        self._addFSInfo(confInfo)
       
    def handleReload(self, confInfo=None):
        """
        Handles refresh/reload of the configuration options.
        """
        pass

    def handleRemove(self, confInfo):
        """
        Handles removal of configuration options.
        """
        pass

# initialize the handler
admin.init(ThreatlistStatsRH, admin.CONTEXT_APP_AND_USER)