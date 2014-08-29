'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import json
import sys
import urllib2

import splunk
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))

from SolnCommon.models import SplunkDataModel
from SolnCommon.modinput import logger
from SolnCommon.modinput import ModularInput
from SolnCommon.modinput.fields import BooleanField
from SolnCommon.modinput.fields import Field
from SolnCommon.modinput.fields import FieldValidationException

## Uncomment for debugging.
#import logging
#logger.setLevel(logging.DEBUG)

# constants for exit status
ERR_REST_EXC = 1
ERR_UNKNOWN_EXC = 2
ERR_FAILED_UPDATE = 3


class DataModelAccelerationSettingsModularInput(ModularInput):

    def __init__(self):

        scheme_args = {'title': "Data Model Acceleration Enforcement",
                       'description': "Enforces data model acceleration settings.",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}

        args = [
            ### General options
            BooleanField("acceleration", "Acceleration", """If True, acceleration for the data model will be enabled and enforced at intervals.""", required_on_create=True, required_on_edit=True),
            BooleanField("manual_rebuilds", "Manual Rebuilds", """If True, data model accelerations will not automatically rebuild.""", required_on_create=True, required_on_edit=True),
        ]

        ModularInput.__init__(self, scheme_args, args)

    def run(self, stanzas):

        logger.debug("Entering run method.")
        logger.debug("Input configuration: {0}".format(str(self._input_config)))
        logger.debug("Cleaned parameters: {0}".format(str(stanzas)))

        # Note: This modular input always runs on all hosts, and exits. Interval
        # is required to be set to a non-zero value for this to work.
        exec_status = True
        exit_status = 0

        # Permit testing from command line if defined.
        if getattr(self, '_alt_session_key', False):
            self._input_config.session_key = self._alt_session_key

        # The list of argument names.
        all_args = [arg.name for arg in self.args]

        # The list of Boolean argument names.
        boolean_args = [arg.name for arg in self.args if arg.get_data_type() == Field.DATA_TYPE_BOOLEAN]

        if stanzas and exec_status:
            logger.info('status="executing"')

            for stanza in stanzas:

                try:    
                    # No app or owner context is needed to retrieve the model, 
                    # since it will be ignored on update anyway.
                    model_name = stanza['name'].split('//')[1]
                    model_id = SplunkDataModel.build_id(model_name, None, None)
                    model = SplunkDataModel.get(model_id, self._input_config.session_key)
                    
                    logger.debug('STANZA: %s', stanza)

                    # Since the acceleration settings are actually retrieved from JSON
                    # stored in the model, instead of being attributes on the model,
                    # we have to manually convert Booleans to their Pythonic representations
                    # in order to perform the comparison. Booleans come in via 
                    # the JSON as "0" for False, "1" for "True".
                    prev_state = {}
                    
                    for k, v in [(field, getattr(model, field, None)) for field in all_args]:
                        if k in boolean_args:
                            prev_state[k] = splunk.util.normalizeBoolean(v)
                        else:
                            prev_state[k] = v
                    
                    # Populate the next state. Note that we need None values here
                    # for dictionary matching to work.
                    next_state = {k: stanza.get(k, None) for k in all_args}

                    logger.debug('PREV_STATE: %s', prev_state)
                    logger.debug('NEXT_STATE: %s', next_state)

                    # CAUTION: The next comparison relies on direct dictionary
                    # comparison, for which k-v pairs must match in sorted order.
                    if prev_state == next_state:
                        logger.debug('status="Acceleration settings already correct, skipping update" model="{}", prev_state="{}", next_state="{}"'.format(model_name, prev_state, next_state))
                    else:
                        updated_model = model.set_acceleration(self._input_config.session_key, **next_state)
                        if updated_model:
                            logger.info('status="Acceleration settings updated" model={}, prev_state={}, next_state={}'.format(model_name, prev_state, next_state))
                        else:
                            logger.error('status="Failed to update acceleration settings" model={}, prev_state={}'.format(model_name, prev_state))
                            exit_status = ERR_FAILED_UPDATE
                except splunk.RESTException as e:
                    logger.error('status="REST exception encountered when updating acceleration settings" model={}, exc={}'.format(model_name, e))
                    exit_status = ERR_REST_EXC
                except Exception as e:
                    logger.error('status="Unknown exception encountered when updating acceleration settings" model={}, exc={}'.format(model_name, e))
                    exit_status = ERR_UNKNOWN_EXC

        # Exit cleanly if no errors encountered; otherwise, exit.
        # Exit status reflects the LAST error seen.
        logger.info('status="exiting" exit_status={}'.format(exit_status))
        sys.exit(exit_status)

if __name__ == '__main__':
    logger.info('status="starting"')
    modinput = DataModelAccelerationSettingsModularInput()
    modinput.execute()
