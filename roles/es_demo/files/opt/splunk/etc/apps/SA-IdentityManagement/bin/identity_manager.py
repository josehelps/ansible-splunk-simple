'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import threading
import splunk
import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.modinput import logger
from SolnCommon.lookup_conversion.lookup_modinput import LookupModularInput
from SolnCommon.models import SplunkIdentityLookupConf
from SolnCommon.modinput.fields import Field

## Uncomment for debugging.
#import logging
#logger.setLevel(logging.DEBUG)


class IdentityManagerModularInput(LookupModularInput):

    def __init__(self):

        scheme_args = {'title': "Identity Management",
                       'description': "Merges asset and identity information into Splunk lookup tables.",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}

        args = [
            Field("category", "Category", """Category of the input lookup table. Must be "asset" or "identity".""", required_on_create=True, required_on_edit=True),
            Field("description", "Description", """Description of the input lookup table.""", required_on_create=True, required_on_edit=True),
            Field("master_host", "Master host", "The master host for this download.", required_on_create=False, required_on_edit=False),
            Field("target", "Target", """Target output destination for this asset or identity table.""", required_on_create=True, required_on_edit=True),
            Field("url", "URL", """Resource locator for the asset or identity table.""", required_on_create=True, required_on_edit=True)]
        
        self._app = 'SA-IdentityManagement'
        self._name = 'IdentityManager'
        self._owner = 'nobody'

        self._valid_targets = ['asset', 'identity']

        super(IdentityManagerModularInput, self).__init__(scheme_args, args)

    def detect_updated_identity_config(self):
        '''Compare the previous identityLookup.conf configuration to the current.
        
        Returns:
        set('identity') if the configuration has been updated recently. This is
        equivalent to a boolean but we return a set for ease of use by the caller.
        '''
        
        # The name for checkpointed configuration data.
        IDENTITY_LOOKUP_CHECKPOINT_PREFIX = 'identityLookup_conf'
        
        # The return value.
        merge_required = set()

        try:
            # Refresh the identity lookup configuration
            refresh = splunk.entity.refreshEntities('properties/identityLookup', sessionKey=self._input_config.session_key)
            # Retrieve the identity lookup configuration.
            config = SplunkIdentityLookupConf.get(SplunkIdentityLookupConf.build_id('identityLookup', 'SA-IdentityManagement', 'nobody'), self._input_config.session_key)
        except Exception:
            # Abort, since this error will likely also prevent the identity merge process.
            # Usually this will be a splunk.RESTException
            logger.exception('status="Exception when retrieving identityLookup.conf"')
            raise
            
        # Compare the identityLookup.conf configuration to the previous
        # configuration.
        prev_config = None
        if self.checkpoint_data_exists(IDENTITY_LOOKUP_CHECKPOINT_PREFIX):
            prev_config = self.get_checkpoint_data(IDENTITY_LOOKUP_CHECKPOINT_PREFIX)

        # Now that we have retrieved the previous data, checkpoint the current configuration.
        if config:
            current_config = {str(k): getattr(config, k, None) for k in config.model_fields}
            try:
                self.set_checkpoint_data(IDENTITY_LOOKUP_CHECKPOINT_PREFIX, current_config)
            except Exception:
                logger.exception('status="Error when checkpointing identity lookup configuration; next identity merge will be forced"')
        
        # Compare previous to current configuration.
        if prev_config and config:
            for key, curr_value in current_config.iteritems():
                prev_value = prev_config.get(key, None)
                if curr_value != prev_value:
                    logger.info('status="identityLookup.conf configuration changed; identity merge will be forced" key="%s" prev="%s" curr="%s"', key, prev_value, curr_value)
                    merge_required.add('identity')
        else:
            # Could not retrieve previous identityLookup.conf configuration.
            # Force the next merge (although this is likely to fail if the error
            # was the cause of an error in retrieving information via REST API.
            logger.info('status="identityLookup.conf changes could not be determined. Identity merge will be forced"')
            merge_required.add('identity')

        # Note that the configuration also has an updateTime
        # conf.entity.updateTime, which is a datetime.datetime object with a 
        # time zone info class of splunk.util.TZInfo. This is irrelevant in this 
        # case since we want to detect *changes* in the configuration, not just
        # whether it has been refreshed/reloaded. This also allows us to avoid 
        # complex time zone calculations. However if those become necessary 
        # they would be as follows:
        #
        #     update_time = conf.entity.updateTime
        #     tz = update_time.tzinfo
        #     interval = self._stanzas[0].get('interval')
        #     likely_last_run_time = splunk.util.datetime.fromtimestamp(splunk.util.time.time() - interval, tz)
        #     if update_time >= likely_last_run_time:
        #         merge_required.add('identity')
        
        return merge_required

    def run_threads(self, files_by_category, last_run):

        # Return value for this method
        all_completed = False
        
        # Determine which categories need to be merged, if any. If a single
        # input lookup has been updated, we need to re-merge due to the
        # requirement that we use automatic lookups, which don't permit 
        # complex search language. Thus all deduplication needs to be done
        # in advance.
        merge_required = set()

        # Detect changes to identityLookup.conf. If identityLookup.conf 
        # has been changed, force merging of identities.
        merge_required.update(self.detect_updated_identity_config())
        
        # Detect addition/deletion of stanzas. If a stanza has been added/deleted,
        # force merge of the corresponding category.
        merge_required.update(self.detect_changed_stanzas(files_by_category))
        
        # Detect file time modifications. If a lookup table file has been
        # updated since the last run, force a merge for that category. 
        for target, filelist in files_by_category.iteritems():
            if filelist:
                for fileinfo in filelist:
                    stanza_name, path, last_updated = fileinfo
                    if last_updated > last_run:
                        merge_required.add(target)

        # For categories that must merge (i.e., one or more source files
        # have been updated), run the merge task in a new thread.
        threads = []
        events = []
        if merge_required:
            for target in merge_required:
                if target in self._valid_targets:
                    logger.info('status="merging" category=%s', target)
                    event = threading.Event()
                    merge_thread = threading.Thread(name=target, target=self.merge_task, args=[event], kwargs=files_by_category)
                    merge_thread.daemon = False
                    merge_thread.start()
                    threads.append(merge_thread)
                    events.append(event)
                else:
                    logger.error('status="Invalid output target specified" target=%s', target)

            for t in threads:
                # Block until all threads complete.
                t.join()
            
            logger.info('status="merging complete" category=%s', target)
            all_completed = all([event.is_set() for event in events])

        else:
            logger.info('status="No merging required"')
            all_completed = True
            
        # True if all threads completed their work.
        return all_completed

if __name__ == '__main__':
    logger.info('status="Executing modular input"')
    modinput = IdentityManagerModularInput()
    modinput.execute()
