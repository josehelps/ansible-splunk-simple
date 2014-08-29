'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import threading
import sys

import splunk.models
from splunk.models.base import SplunkAppObjModel
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.modinput import logger
from SolnCommon.lookup_conversion.lookup_modinput import LookupModularInput
from SolnCommon.modinput.fields import Field

## Uncomment for debugging.
#import logging
#logger.setLevel(logging.DEBUG)


class SplunkThreatlistInput(SplunkAppObjModel):
    '''Class for obtaining threatlist conf stanzas via REST. This is required for
    the merge thread. Unlike during introspection, default modular input fields
    must be specified here.'''
    resource = '/data/inputs/threatlist'
    category = splunk.models.field.Field()
    description = splunk.models.field.Field()
    target = splunk.models.field.Field()
    typ = splunk.models.field.Field(api_name='type')  # Note: avoiding using reserved "type"
    url = splunk.models.field.Field()
    # Parsing options
    delim_regex = splunk.models.field.Field()
    extract_regex = splunk.models.field.Field()
    fields = splunk.models.field.Field()
    ignore_regex = splunk.models.field.Field()
    skip_header_lines = splunk.models.field.IntField()
    # Default modular input options
    disabled = splunk.models.field.BoolField()
    interval = splunk.models.field.Field()


class ThreatlistManagerModularInput(LookupModularInput):

    def __init__(self):

        scheme_args = {'title': "Threat List Manager",
                       'description': "Merges threatlist information into Splunk lookup tables.",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}

        args = [Field("master_host", "Master host", "The master host for this download.", required_on_create=False, required_on_edit=False)]
        
        self._app = 'SA-ThreatIntelligence'
        self._name = 'ThreatlistManager'
        self._owner = 'nobody'
        
        # The alternate modular input name from which to retrieve stanza information.
        self._alt_modinput_name = 'threatlist'

        super(ThreatlistManagerModularInput, self).__init__(scheme_args, args)
    
    def collect_stanzas(self, alt_modinput_name=None):
        # 1. Make REST call to get stanza names. Return list of dictionary objects.
        to_ignore = ['action_links',
                     'entity',
                     'errors',
                     'id',
                     'metadata',
                     'model_fields']
        stanzas = SplunkThreatlistInput.all(sessionKey=self._input_config.session_key)
        return [{k:v for k, v in stanza.__dict__.iteritems() if k not in to_ignore} for stanza in stanzas]

    def run_threads(self, files_by_category, last_run):

        # Set up the merge handlers
        self._valid_targets = {'alexa': self.streaming_merge_task,
            'asn': self.streaming_merge_task,
            'mozilla_psl': self.streaming_merge_task,
            'threatlist': self.streaming_merge_task,
            'tld': self.streaming_merge_task}

        # Return value for this method
        all_completed = False
        
        # Determine which categories need to be merged, if any. If a single
        # input lookup has been updated, we need to re-merge due to the
        # requirement that we use automatic lookups, which don't permit 
        # complex search language. Thus all deduplication needs to be done
        # in advance.
        merge_required = set()
        
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
                    merge_thread = threading.Thread(name=target, target=self._valid_targets.get(target), args=[event], kwargs=files_by_category)
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
            logger.info('status="no merging required"')
            all_completed = True

        # True if all threads completed their work.
        return all_completed

if __name__ == '__main__':
    logger.info('status="Executing modular input"')
    modinput = ThreatlistManagerModularInput()
    modinput.execute()
