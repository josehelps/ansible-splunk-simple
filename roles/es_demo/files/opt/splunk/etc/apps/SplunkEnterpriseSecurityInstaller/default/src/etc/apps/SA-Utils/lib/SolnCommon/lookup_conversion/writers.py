'''
Copyright (C) 2005-2012 Splunk Inc. All Rights Reserved.
'''
import errno
import os
import random
import sys
import time

from ..error import LookupConversionErrors
from ..lookups import get_lookup_table_location
from ..lookups import update_lookup_table
from ..lookups import get_lookup_transform
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# Import custom class for creating UI messages.
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Utils', 'lib']))
from SolnCommon.messaging import Messenger
from SolnCommon.modular_input import logger

# Global for context in log messages.
ctx = 'lookup_conversion'


class Writer(object):

    def __init__(self, lookups, session_key):
        '''Initialize the output writers.
        @param lookups: A dictionary of:

                {key_field: (filename, namespace, owner)}

            indicating the lookup table name to be written for each key field.

        @param session_key: A Splunk session key. The session key must have 
            permission to write to all namespaces defined in "lookups".
        '''

        self._lookups = lookups
        self._session_key = session_key    


class MultipleLookupWriter(Writer):
    
    def _move_lookup(self, key_field, output_filename, dont_use_rest_for_file_update=False):
        '''Move a single CSV into place as a Splunk lookup table.
        
        @param key_field: The key field for this lookup table.
        @param output_filename: The source filename. 
        @param dont_use_rest_for_file_update: Avoid using REST calls for file
            move operations.
        '''
        
        was_successful = False

        if key_field in self._lookups.keys():
            
            # Retrieve lookup table name.
            tgt_lookup_name, namespace, owner = self._lookups[key_field]
            
            logger.info('RETRIEVING: path for target lookup name: %s', tgt_lookup_name)
            # Retrieve the target filename from the app that currently owns the transform
            transform = get_lookup_transform(tgt_lookup_name, None, owner, self._session_key)

            if output_filename is not None and os.path.isfile(output_filename) and transform and getattr(transform, 'filename', False):
                logger.info('UPDATING: path for target lookup table: %s', transform.filename)
                logger.info('LOOKUP_GEN:temporary file retrieved: file=%s', output_filename)
                # Do a direct file move if the arguments indicate that we should
                # avoid using REST to swap the file contents with the existing 
                # lookup table. See SOLNESS-2943.
                if dont_use_rest_for_file_update or os.name in ['nt', 'os2']:
                    # Path to the new lookup table in the staging area.
                    src_lookup_path = make_splunkhome_path(["var", "run", "splunk", "lookup_tmp", output_filename])
                    # Path to the destination lookup table.
                    dst_lookup_path = make_splunkhome_path(['etc', 'apps', transform.namespace, "lookups", transform.filename])
                    # Path to the temporary location for the old lookup table, 
                    # to be deleted. Timestamp plus random integer is used to 
                    # attempt uniqueness.
                    tmp_lookup_fname = "_".join([transform.filename, str(int(time.time())), str(random.randint(0, 255))])
                    tmp_lookup_path = make_splunkhome_path(['etc', 'apps', transform.namespace, "lookups", tmp_lookup_fname])

                    retries = 5
                    while retries > 0:
                        try:
                            # On Windows, calling os.unlink() on a file that has
                            # been opened by another process puts it in a 
                            # "scheduled delete" state. Subsequent calls to
                            # os.move() targeting the same file will raise 
                            # WindowsError: [Error 5] Access is denied.
                            #
                            # For additional details see:
                            #  http://msdn.microsoft.com/en-us/library/windows/desktop/aa363858%28v=vs.85%29.aspx
                            #
                            # To avoid, we move the file out of the way, then 
                            # replace it, THEN delete the original file.
                            logger.info("MOVING: active --> inactive: src=%s dst=%s", dst_lookup_path, tmp_lookup_path)
                            os.rename(dst_lookup_path, tmp_lookup_path)
                            logger.info("MOVING: updated --> active: src=%s dst=%s", src_lookup_path, dst_lookup_path)
                            os.rename(src_lookup_path, dst_lookup_path)
                            logger.info("REMOVING: inactive: src=%s", tmp_lookup_path)
                            os.unlink(tmp_lookup_path)
                            was_successful = True
                            break
                        except Exception:
                            # Wait for a second to see if the unlink and rename
                            # is being blocked by a different process.
                            time.sleep(5)
                            continue
                        finally:
                            retries = retries - 1
                            
                    if not was_successful:
                        logger.exception('EXCEPTION: Could not rename file after multiple retries src=%s dst=%s', src_lookup_path, dst_lookup_path)
                    
                else:
                    was_successful = update_lookup_table(output_filename, transform.filename, transform.namespace, owner, self._session_key)

                if was_successful:
                    logger.info('UPDATED: Target lookup table: %s', transform.filename)
                else:
                    logger.error('FAILURE: %s: %s', LookupConversionErrors.ERR_LOOKUP_CREATION_FAILED, transform.filename)
            else:
                logger.error('FAILURE: %s: %s', LookupConversionErrors.ERR_TEMPORARY_FILE_NOT_CREATED, output_filename)
        else:
            logger.warn('FAILURE: Received a request to update a lookup table, but no lookup definition for the key exists: key=%s', key_field)

        return was_successful
    
    def _remove(self, key_field, path):
        if path is not None and os.path.isfile(path):
            try:
                os.unlink(path)
            except OSError:
                logger.exception('FAILURE: %s: (key: %s, tempfile: %s)', LookupConversionErrors.ERR_TEMPORARY_FILE_REMOVAL_FAILED, key_field, path)
        else:
            # File already removed.
            pass

    def move_lookups(self, output_files):
        '''Move a set of files into place as Splunk lookup tables.
        
        @param output_files: A dictionary of <key_field>: <output_filename> pairs.
        
        Multiple keys can point to the same file; this routine will only attempt
        a single move per unique output file.
         
        If a key in output_files does not correspond to a value in self._lookups,
        the output is discarded by self._move_lookup.
        
        If a file is zero-length, the move is skipped antirely and the original
        file is removed.
        '''
        success = True
        processed = set()
        
        for key_field, path in output_files.iteritems():
            if path is not None and path not in processed:
                # Mark file as processed.
                processed.add(path)

                # Check the file size.
                stats = os.stat(path)

                # Move the file if it's not zero-length
                if stats.st_size > 0:
                    if not self._move_lookup(key_field, path):
                        # Move failed. Take the following actions:
                        # a) Alert the user.
                        # b) Try to remove the temporary file.
                        # c) Return success = False.
                        logger.error('FAILURE: %s: (key: %s, tempfile: %s)', LookupConversionErrors.ERR_LOOKUP_CREATION_FAILED, key_field, path)
                        Messenger.createMessage('%s: %s (key: %s, tempfile: %s)' % (ctx, LookupConversionErrors.ERR_LOOKUP_CREATION_FAILED, key_field, path), self._session_key)
                        self._remove(key_field, path)
                        success = False

                # Always try to remove the temporary file.
                self._remove(key_field, path)

            else:
                # File was already processed (multiple keys targeting a single
                # output file), or the path was None.
                pass

        return success
