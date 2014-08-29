'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import os
import re
import sys
import time
import threading
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.lookups import get_temporary_checkpoint_file
from SolnCommon.modinput import logger
from SolnCommon.modinput import ModularInput
from SolnCommon.modinput.fields import Field
from SolnCommon.modinput.fields import IntegerField
from SolnCommon.modinput.fields import RangeField
from SolnCommon.pooling import should_execute
from SolnCommon.protocols import HttpProtocolHandler
from SolnCommon.protocols import NoopProtocolHandler
from SolnCommon.credentials import CredentialManager

## Uncomment for debugging.
#import logging
#logger.setLevel(logging.DEBUG)


class ThreatlistModularInput(ModularInput):

    def __init__(self):

        self.DEFAULT_INITIAL_DELAY = 300
        self.DEFAULT_RETRIES = 3
        self.DEFAULT_RETRY_INTERVAL = 60
        self.DEFAULT_TIMEOUT_INTERVAL = 30
        self.DEFAULT_SKIP_HEADER_LINES = 0
        self.DEFAULT_THREAD_POOL_SIZE = 5
        self.DEFAULT_THREAD_SLEEP_INTERVAL = 300
        self.DEFAULT_MERGE_THREAD_SLEEP_INTERVAL = 15

        # Dictionary of supported protocol handlers.
        self.PROTOCOL_HANDLERS = {'http': HttpProtocolHandler,
                               'https': HttpProtocolHandler,
                               'lookup': NoopProtocolHandler}

        # Regex for extracting key=value strings
        self.KV_REGEX = re.compile('(\w+)=([\w:$]+|"[^"]+")')
        
        # Regex for extracting interpolated arguments.
        self.ARG_REGEX = re.compile('\$([A-Za-z0-9_]+):([A-Za-z0-9_]+)\$')

        scheme_args = {'title': "Threat Lists",
                       'description': "Downloads threat lists or other threat intelligence feeds from remote hosts.",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "false"}

        args = [
            ### General options
            Field("type", "Threatlist Type", """Type of threat list, such as "malware".""", required_on_create=True, required_on_edit=True),
            Field("description", "Description", """Description of the threat list.""", required_on_create=True, required_on_edit=True),
            Field("target", "Target", """Target lookup table.""", required_on_create=False, required_on_edit=False),
            Field("url", "URL", """URL or location of the threatlist.""", required_on_create=True, required_on_edit=True),
            RangeField("weight", "Weight", """Weight for IPs that appear on this threatlist. A higher weight increases an IP's risk score.""", low=1, high=100, required_on_create=True, required_on_edit=True),
            ### Download options
            Field("post_args", "POST arguments", """POST arguments to send to the remote URL.""", required_on_create=False, required_on_edit=False),
            IntegerField("retry_interval", "Retry interval", "Interval between attempts to download this threat list, in seconds.  [Defaults to {0}]".format(self.DEFAULT_RETRY_INTERVAL), required_on_create=True, required_on_edit=True),
            Field("site_user", "Remote site user", "The user name for authentication to the remote site, if required. Must correspond to a Splunk stored credential.", required_on_create=False, required_on_edit=False),
            IntegerField("retries", "Retries", "the number of times to retry a failed download.  [Defaults to {0}]".format(self.DEFAULT_RETRIES), required_on_create=True, required_on_edit=True),
            IntegerField("timeout", "Timeout interval", "Time before regarding a download attempt as failed, in seconds.  [Defaults to {0}]".format(self.DEFAULT_TIMEOUT_INTERVAL), required_on_create=True, required_on_edit=True),
            ### Proxy options
            RangeField("proxy_port", "Proxy port", "The proxy server port, if required.", low=0, high=65535, required_on_create=False, required_on_edit=False),
            Field("proxy_server", "Proxy server", "The proxy server, if required. Only used by HTTP(S) protocol.", required_on_create=False, required_on_edit=False),
            Field("proxy_user", "Proxy user", "The proxy user name, if required. Must correspond to a Splunk stored credential. Only used by HTTP(s) protocol.", required_on_create=False, required_on_edit=False),
            ### Parser options
            # Note: extract_regex is a Field instead of DelimitedField so we can handle splitting via the CSV parser.
            # TODO: Eliminate distinction between delim_regex and extract_regex.
            Field("delim_regex", "Delimiting regex", "Regular expression used to delimit the input.", required_on_create=False, required_on_edit=False),
            Field("extract_regex", "Extracting regex", "Regular expression used to extract fields from the input.", required_on_create=False, required_on_edit=False),
            Field("fields", "Fields", "The list of fields to extract from the threat list.", required_on_create=True, required_on_edit=True),
            Field("ignore_regex", "Ignoring regex", "Regular expression for lines to be ignored in the threat list.", required_on_create=False, required_on_edit=False),
            Field("skip_header_lines", "Skip header lines", "Number of header lines to skip, if any. [Defaults to {0}]".format(self.DEFAULT_SKIP_HEADER_LINES), required_on_create=False, required_on_edit=False),
            ### General options - should only be set in default stanza.
            IntegerField("initial_delay", "Initial delay", """Initial delay in seconds before the modular input begins executing, IF not being executed on a cron schedule. Used to alleviate startup load. [Defaults to {0}]""".format(self.DEFAULT_INITIAL_DELAY), required_on_create=False, required_on_edit=False),
            Field("master_host", "Master host", "The master host for this download.", required_on_create=False, required_on_edit=False),
        ]

        self._app = 'SA-ThreatIntelligence'
        self._owner = 'nobody'
        self._name = 'Threatlist'
        
        super(ThreatlistModularInput, self).__init__(scheme_args, args)

    def get_handler(self, name):
        '''Return a protocol handler by name.'''
        return self.PROTOCOL_HANDLERS.get(name, None)

    def get_password(self, user, app, owner):
        credmgr = CredentialManager(self._input_config.session_key)
        return credmgr.get_clear_password(user, '', app, owner)
    
    def get_post_args(self, stanza):
        '''Retrieve POST arguments. Right now this is a string expected to
        contain key=value pairs, possibly quoted.
        
        @param stanza: The input stanza.
        '''

        data = {}
        post_args = stanza.get('post_args', {})
        if post_args:
            try:
                data = dict(self.KV_REGEX.findall(post_args))

                # Handle any dynamic POST arguments where we have to retrieve
                # information. Usually this is something like an API key to be
                # retrieved from the secure credential store.
                updated_data = {}

                for post_arg, post_value in data.items():
                    arg_match = self.ARG_REGEX.match(post_value)
                    if arg_match:
                        # Right now we only handle custom "user:<username>" arguments.
                        field, value = arg_match.groups()
                        if field == 'user':
                            try:
                                dynamic_value = self.get_password(value, self._app, 'nobody')
                                updated_data[post_arg] = dynamic_value
                            except Exception:
                                logger.exception('stanza=%s status="error retrieving user credentials" post_arg="%s" name="%s"', stanza.get('name'), post_arg, value)

                data.update(updated_data)

            except Exception:
                # Error processing POST arguments. Ignore them.
                logger.exception('stanza="%s" status="error processing POST arguments" post_args="%s"', stanza.get('name'), post_args)
    
        return data
    
    def download_task(self):
        '''Download a threat list.'''
        logger.info('status=download_thread_starting')
        stanza = self._stanzas[0]

        # Get the POST arguments, protocol handler and retry settings.
        retries = stanza.get('retries', self.DEFAULT_RETRIES)
        retry_interval = stanza.get('retry_interval', self.DEFAULT_RETRY_INTERVAL)
        stanza_name = stanza.get('name').split('://')[1]
        url = stanza.get('url')
        handler_name = url.split('://')[0]
        handler_cls = self.get_handler(handler_name)
        post_data = self.get_post_args(stanza)

        if handler_cls.__name__ == 'NoopProtocolHandler':
            # Do nothing. This is a "lookup" based threatlist and as such will
            # be incorporated by the merge thread automatically.
            return

        elif handler_cls:

            # HTTP handler expects these params:
            # ['site_user', 'app', 'debug', 'owner', 'proxy_port', 'proxy_server', 'proxy_user']

            # The handler's __init__ function will ignore any extraneous parameters.
            # The query must be passed directly to run(), not as a param to __init__.
            # This permits a single handler to be used for multiple queries.
            handler = handler_cls(logger, self._input_config.session_key, **stanza)
            temp_checkpoint_filehandle = None
            checkpoint_filename = self.gen_checkpoint_filename(stanza_name, self._name.lower())

            while retries >= 0:
                content = handler.run(url, post_data)
                if content:
                    try:
                        temp_checkpoint_filehandle = get_temporary_checkpoint_file(stanza_name, self._name.lower())                        
                        temp_checkpoint_filehandle.write(content)
                        temp_checkpoint_filehandle.close()
                    except IOError as exc:
                        logger.exception('stanza={} retries_remaining={} status="threat list could not be written to temporary file" url={} exc={}'.format(stanza_name, retries, url, exc))
                    break
                else:
                    logger.info('stanza={} retries_remaining={} status="retrying download" url={} retry_interval={}'.format(stanza_name, retries, url, retry_interval))
                    retries -= 1
                    time.sleep(retry_interval)
            # end while loop
            
            if retries >= 0:
                if temp_checkpoint_filehandle and os.path.isfile(temp_checkpoint_filehandle.name):
                    f_stat = os.stat(temp_checkpoint_filehandle.name)
                    logger.info('stanza={} retries_remaining={} status="threat list downloaded" file={} bytes={} url={}'.format(stanza_name, retries, temp_checkpoint_filehandle.name, f_stat.st_size, url))
                    # Move the file into place.
                    if os.name in ['nt', 'os2']:
                        try:
                            if os.path.exists(checkpoint_filename):
                                os.unlink(checkpoint_filename)
                            os.rename(temp_checkpoint_filehandle.name, checkpoint_filename)
                        except Exception as exc:
                            # Catch Exception since this may raise OSError or
                            # another WindowsException
                            logger.exception('stanza={} status="threat list could not be written to disk" exc={}'.format(stanza_name, exc))
                    else:
                        try:
                            os.rename(temp_checkpoint_filehandle.name, checkpoint_filename)
                        except IOError as exc:
                            logger.exception('stanza={} status="threat list could not be written to disk" exc={}'.format(stanza_name, exc))
                else:
                    # Should never get here.
                    logger.info('stanza={} retries_remaining={} status="threat list download succeeded but failed writing to disk" url={}'.format(stanza_name, retries, url))
            else:
                # File could not be downloaded after multiple retries.
                logger.info('stanza={} retries_remaining={} status="threat list download failed after multiple retries" url={}'.format(stanza_name, retries, url))

            # Clean any stray checkpoint files.
            try:
                if temp_checkpoint_filehandle and os.path.isfile(temp_checkpoint_filehandle.name):
                    os.unlink(temp_checkpoint_filehandle.name)
            except IOError as exc:
                logger.info('stanza={} status="temporary threat list file could not be deleted" exc={}'.format(stanza_name, exc))

        else:
            logger.info('stanza={} retries_remaining={} status="handler not initialized" url={}'.format(stanza, retries, url))
            sys.exit(1)

    def run(self, stanzas, *args, **kwargs):

        logger.debug("Entering run method.")
        logger.debug("Input configuration: {0}".format(str(self._input_config)))
        logger.debug("Cleaned parameters: {0}".format(str(stanzas)))

        if not isinstance(stanzas, list):
            # Case 1: single instance mode == False
            # A single stanza has been passed in. Convert to a list since shared 
            # libraries all assume a list. 
            self._stanzas = [stanzas]
        else:
            # Case 2: single instance mode == True
            # Multiple stanzas will have been passed in.
            self._stanzas = stanzas
        
        # 1. Check for existence of checkpoint directory.
        if not os.path.isdir(self._input_config.checkpoint_dir):
            os.mkdir(self._input_config.checkpoint_dir)

        # 2. Detect if we are the master host.
        # Note: Only the first stanza is checked; it is not technically an error
        # to specify the master_host setting in a non-default stanza for this 
        # input, but the value will be ignored.
        # TODO: Verify that this will not error out when no stanzas are defined. 
        exec_status, msg = should_execute(self._stanzas[0].get('master_host', ''))

        if exec_status:

            # 3. Execute the modular input.
            logger.info('status="proceeding" msg={0})'.format(msg))
            
            # Since we are NOT in single instance mode, we will have only one stanza.
            # Download the threatlist based on the stanza information. Scheduling
            # is not necessary since a threatlist is always downloaded.
            # TODO: handle unchanged content (HTTP 304 status). 
            stanza = self._stanzas[0]
            name = stanza.get('name').split('://')[1]
            download_thread = threading.Thread(name="download_{}".format(name), target=self.download_task)
            download_thread.daemon = False
            download_thread.start()
        else:
            # Exit the script if the host is a pool member but not
            # designated as the master host for this input.
            logger.info('status="exiting" msg="not master host"')

if __name__ == '__main__':        
    logger.info("Executing modular input.")
    modinput = ThreatlistModularInput()
    modinput.execute()
