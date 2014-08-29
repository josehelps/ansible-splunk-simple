'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import importlib
import re
import sys

import splunk
# To avoid name clash with modular input package's "Field" class, make a direct
# import of the "models" class.
import splunk.models
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.models.base import SplunkAppObjModel
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))

from SolnCommon.messaging import Messenger
from SolnCommon.modinput import logger
from SolnCommon.modinput import ModularInput
from SolnCommon.modinput.fields import Field
from SolnCommon.modinput.fields import RegexField
from SolnCommon.modinput.fields import SeverityField

## Uncomment for debugging.
#import logging
#logger.setLevel(logging.DEBUG)

# constants for exit status
ERR_IMPORT_EXC = 1
ERR_REST_EXC = 2
ERR_UNKNOWN_EXC = 3


class SplunkConfigurationCheck(SplunkAppObjModel):
    '''Read-only class for configuration checks (defined as inputs.conf stanzas).'''

    resource = '/data/inputs/configuration_check'
    name = splunk.models.field.Field()
    handler = splunk.models.field.Field()
    loglevel = splunk.models.field.Field()


class SplunkConfigurationCheckModularInput(ModularInput):

    def __init__(self):

        scheme_args = {'title': "Configuration Checker",
                       'description': "Runs configuration checks.",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "false"}

        args = [
            ### General options
            Field("handler", "Handler", """The name of a Python callable object that performs the configuration check".""", required_on_create=True, required_on_edit=True),
            SeverityField("default_severity", "Log level", """The log level for this configuration check.""", required_on_create=True, required_on_edit=True),
            SeverityField("required_ui_severity", "Required UI severity", """The minimum severity required for messages raised by this configuration check to be displayed in the UI.""", required_on_create=True, required_on_edit=True),
            RegexField("suppress", "Suppression string", """Regular expression specifying messages to suppress in the UI.""", required_on_create=False, required_on_edit=False),
        ]

        ModularInput.__init__(self, scheme_args, args)

    def run(self, stanza):
        # If severity in the config is lower than the current default, reset the
        # active log level now.
        loglevel = stanza['default_severity']
        if loglevel < logger.getEffectiveLevel():
            logger.setLevel(loglevel)

        # Single instance mode is active; only one stanza passed in as parameter.
        logger.debug("Entering run method.")
        logger.debug("Input configuration: %s", self._input_config)
        logger.debug("Cleaned parameters: %s", stanza)

        # Note: This modular input always runs on all hosts, and exits. Interval
        # is required to be set to a non-zero value for this to work.
        exec_status = True
        exit_status = 0
        
        # Permit testing from command line if defined.
        if getattr(self, '_alt_session_key', False):
            self._input_config.session_key = self._alt_session_key

        if stanza and exec_status:

            logger.info('status="executing"')

            try:
                
                # 1. Obtain the name and namespace for this check.
                task_name = stanza['name'].split('//')[1]
                logger.info('status="retrieved task" task="%s"', task_name)
                entity_id = SplunkConfigurationCheck.build_id(task_name, None, None)
                entity = SplunkConfigurationCheck.get(entity_id, sessionKey=self._input_config.session_key)

                # 2. Obtain suppression regex if defined.
                suppress_rx = None
                try:
                    suppress = stanza.get('suppress', None)
                    if suppress:
                        suppress_rx = re.compile(suppress)
                        logger.info('status="enabled UI message suppression" task="%s" pattern="%s"', task_name, suppress_rx.pattern)
                    else:
                        logger.debug('status="disabled UI message suppression" task="%s"', task_name)
                except re.error:
                        logger.exception('status="skipping suppression due to invalid regular expression" task="%s"', task_name)


                if entity:
                
                    # 3. Import the callable. Note that we import from the app
                    #    that defines the task first, then from SA-Utils. The 
                    #    path order enforces this behavior. However the best 
                    #    practice is not to override the name of an existing
                    #    configuration check.
                    sys.path.extend([make_splunkhome_path(["etc", "apps", entity.namespace, "bin"]),
                                     make_splunkhome_path(["etc", "apps", 'SA-Utils', "bin"])])

                    callable_obj = None
                    
                    # The convention for writing configuration checks is as follows:
                    #
                    # a. Write a function in <app>/bin/configuration_checks/__init__.py.
                    # b. Ensure that the function takes two keyword arguments:
                    #        namespace -> the app name
                    #        sessionKey -> a valid session key
                    #    and returns a list of tuples:
                    #        [(logging.<SEVERITY>, msg), ...] 
                    try:
                        # Import the callable.
                        module = importlib.import_module('configuration_checks')
                        callable_obj = getattr(module, task_name)
                    except ImportError as e:
                        # Raise the error since execution cannot continue.
                        raise

                    # 4. Generate arguments for the callable.
                    kwargs = {'namespace': entity.namespace, 
                              'sessionKey': self._input_config.session_key}
                
                    # 5. Execute the callable.
                    messages = callable_obj(**kwargs)
                
                    for severity, message in messages:
                        
                        # a. Test for suppression.
                        if suppress_rx and suppress_rx.search(message):
                            # UI message will be skipped.
                            logger.log(severity, 'status="suppressed" task="%s" message="%s"', task_name, message)
                            continue
                                
                        # b. Log the error. The configuration check message
                        #    will be appended to the log message as-is. 
                        logger.log(severity, 'status="completed" task="%s" message="%s"', task_name, message)
                
                        # c. Generate UI messages if required and not excluded
                        #    by the configuration.                        
                        if severity >= stanza['required_ui_severity']:
                            uuid = Messenger.createMessage(message,
                                self._input_config.session_key,
                                msgid=None,
                                namespace=entity.namespace,
                                owner='nobody')

            except ImportError as e:
                logger.exception('status="ImportError when executing configuration check" exc="%s"', e)
                exit_status = ERR_IMPORT_EXC
            except splunk.RESTException as e:
                logger.exception('status="RESTException when executing configuration check" exc="%s"', e)
                exit_status = ERR_REST_EXC
            except Exception as e:
                logger.exception('status="Unknown exception when executing configuration check (traceback follows)" exc="%s"', e)
                exit_status = ERR_UNKNOWN_EXC
                
        else:
            # Should never get here.
            logger.error('status="no stanza retrieved"')

        # Exit cleanly if no errors encountered; otherwise, exit.
        # Exit status reflects the LAST error seen.
        logger.info('status="exiting" exit_status="%s"', exit_status)
        sys.exit(exit_status)

if __name__ == '__main__':
    logger.info('status="starting"')
    modinput = SplunkConfigurationCheckModularInput()
    modinput.execute()
