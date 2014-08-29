'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import abc
import csv
import itertools
import os
import sys

from ..error import Errors
from ..error import LookupConversionErrors
from ..lookups import get_temporary_lookup_file
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Utils', 'lib']))
from SolnCommon.modular_input import logger
from SolnCommon.lookup_conversion.writers import MultipleLookupWriter


class LookupOutputSpec(object):

    __metaclass__ = abc.ABCMeta
    
    def __init__(self, ancillary_lookups, output_lookups, routing):
        '''Create a lookup output specification. A lookup output handler
        will consume this specification, which defines the following:

        ancillary_lookups: A dictionary of:
        
            { <field_name>: [<value>, <value>]
              <field_name>: ...
            }
        
        output_lookups: A dictionary of:
        
            { <key_field_name>: (<output_lookup_name>, <namespace>, <owner>),
              <key_field_name: ...
            }

        routing: A nested dictionary of:
        
             key_fields -> {  new key field 1 -> callable conversion function,
                              new key field 2 -> callable conversion function,

        This dictionary defines the output lookup tables for this lookup
        conversion. Each lookup table MUST already be defined in
        the transforms.conf file for the <namespace>
        '''
        
        # Ancillary lookup tables to be created by this spec. This is usually done 
        # to create a short lookup table for "categories" within the larger lookup table,
        # to avoid loading the massive table when doing something like populating
        # a drop-down table in a view.
        # WARNING: These fields must also be defined as instances of
        # AncillaryLookupFieldMappings (or a derived class) in the conversion spec.
        self._ancillary_lookups = ancillary_lookups
        self._output_lookups = output_lookups
        self._routing = routing

    @property
    def ancillary_lookups(self):
        return self._ancillary_lookups or {}

    @property
    def output_lookups(self):
        '''Return the valid lookup tables for this handler.'''
        return self._output_lookups or {}
    
    @property
    def routing(self):
        '''Return the routing table for this handler
        (should be an empty dictionary, if left undefined by the subclass).'''
        return self._routing or {}

 
class LookupOutputHandler:
    '''Class for writing data to lookup tables.'''
    
    __metaclass__ = abc.ABCMeta

    def __init__(self, conversion_spec, output_spec, session_key):
        self._conversion_spec = conversion_spec
        self._output_spec = output_spec
        self._session_key = session_key
        
        # TODO: Clean old temporary lookup table files that may have accumulated
        # as a result of script breakage or Splunk crashes.
        
    def _create_output_files(self):
        
        self._output_writers = {}
        self._output_files = {}
          
        self._ancillary_output_writers = {}
        self._ancillary_output_files = {}

        # Define an output file and create a CSV writer for each target lookup.
        # We will output the data directly to the temporary CSVs as soon
        # as we have the data, since storing the number of permutations in
        # in memory before passing to a separate writer class can cause
        # memory usage to explode at large input sizes. The temporary
        # CSV files will be closed and returned to the caller, after which
        # they can be moved into place as Splunk lookup tables.
         
        # Keep track of filehandles already opened, so they can be reused between 
        # different keys.
        output_filehandles = {}
        ancillary_output_filehandles = {}
         
        for key_field in itertools.chain(self._conversion_spec.key_fieldset, itertools.chain.from_iterable([i.keys() for i in self._output_spec.routing.values()])):
 
            # Check the output lookup table name for this key.
            output_lookup_def = self._output_spec.output_lookups.get(key_field, None)
 
            # If the key field is associated with an output lookup table,
            # retrieve the filehandle, or raise an error if there is no
            # output lookup table defined (this would indicate an error in
            # the handler configuration. Similarly for ancillary lookup tables below.
            fh = None
            if output_lookup_def:
                logger.info('RETRIEVING: temporary output file for key: %s', key_field)
                fh = output_filehandles.setdefault(output_lookup_def[0], get_temporary_lookup_file())
                if fh is not None and os.path.isfile(fh.name):
                    logger.info('RETRIEVED: temporary file retrieved: file=%s', fh.name)
                    self._output_files[key_field] = fh
                    output_writer = self._output_writers.setdefault(key_field, csv.DictWriter(fh, self._conversion_spec.fieldset, extrasaction="ignore"))
                    # Output header line if the filehandle has just been opened.
                    if fh.tell() == 0:
                        output_writer.writeheader()
            else:
                raise ValueError(LookupConversionErrors.ERR_LOOKUP_NOT_DEFINED_FOR_KEY)
    
        for key_field in self._output_spec.ancillary_lookups:
            # Repetition of code here somewhat necessary since:
            # a) There may be overlap between the key fields and fields for which
            #    ancillary lookups are generated.
            # b) Ancillary fields may not be key fields and would not occur in
            #    the preceding loop.

            ancillary_lookup_def = self._output_spec.ancillary_lookups.get(key_field, None)

            fh = None
            if ancillary_lookup_def:
                logger.info('RETRIEVING: ancillary output file for key: %s', key_field)
                fh = ancillary_output_filehandles.setdefault(ancillary_lookup_def, get_temporary_lookup_file())
                if fh is not None and os.path.isfile(fh.name):
                    logger.info('RETRIEVED: ancillary file retrieved: file=%s', fh.name)
                    self._ancillary_output_files[key_field] = fh
                    ancillary_output_writer = self._ancillary_output_writers.setdefault(key_field, csv.DictWriter(fh, [key_field], extrasaction="ignore"))
                    # Output header line if the filehandle has just been opened.
                    if fh.tell() == 0:
                        ancillary_output_writer.writeheader()
            else:
                # An ancillary lookup table is not required to exist for every field.
                pass

    def process(self, converted_input, ancillary_data):
        '''Write the data to a set of Splunk lookup tables.
        
        @param converted_input: A dictionary of field -> list of dicts representing records.
        @param ancillary_data: A dictionary of field -> list of values
        
        Data in ancillary data will be written directly to a lookup table if one is
        defined.
        
        Data in converted_input will be ROUTED to a lookup table depending on the
        value of the key field, if routing is defined. This means that converted_input
        records can be directed to different lookup tables for different purposes (but not
        duplicated in multiple lookup tables, currently - only one output file per record
        is supported).
        '''

        # Create target lookup temporary files. This should happen here and not
        # at initialization.
        self._create_output_files()

        # Keep track of the writers that have been used.
        output_writers_used = {}

        # Threatlist conversions do not use dictionaries since they no longer 
        # deduplicate; asset/identities use dictionaries. Handle both iteration
        # methods here.
        if isinstance(converted_input, dict):
            items = converted_input.iteritems()
        else:
            items = converted_input
        for (field, value), records in items:
            # Conditionally split the lookup table if desired.
            # This is useful in instances where both a CIDR and
            # string lookup must be defined from the same input.
            # Initially, the target is whatever lookup is defined for
            # the current key_field_name; e.g., "ip" => assets_by_ip.csv
            target = field
            routers = self._output_spec.routing.get(field, None)
            # If there are routers for this field name (there can be multiple),
            # check the value against each routing function. If there is a match, 
            # redirect the output for these records. Each routing function should,
            # otherwise the LAST match will succeed.
            if routers is not None:
                for lookup_name, condition in routers.items():
                    if condition(value):
                        target = lookup_name
                        
            self._output_writers[target].writerows(records)
            output_writers_used[target] = True
   
        # CLEANUP OUTPUT
        # Recall that multiple key fields can map to a single output file,
        # via the routing table.
        # 1. Retain the file names for return to caller.
        # 2. Write a default row to any unused output files.
        # 3. Close the files.
        output_filenames = {} 
        output_files_unused = set(self._output_files.values())
  
        for k, fh in self._output_files.iteritems():
            output_filenames[k] = fh.name
              
            if output_writers_used.get(k, False):
                output_files_unused.discard(fh)
  
        for k, fh in self._output_files.iteritems():
  
            if fh in output_files_unused:
            # If no rows were written to the file, output a default line
            # which will never match. This prevents a UI error from occurring
            # when an automatic lookup table consists of only a header line.
                try:
                    self._output_writers[k].writerow({})
                except ValueError:
                    # File already written to and closed.
                    pass
            fh.close()

        # Process ancillary lookups.
        ancillary_filenames = {} 
        for target_field, values in ancillary_data.items():
            # Writerows expects a list of dicts.
            values = [{target_field: v} for v in values]
            self._ancillary_output_writers[target_field].writerows(values)
            self._ancillary_output_files[target_field].close()
            ancillary_filenames[target_field] = self._ancillary_output_files[target_field].name
        
        # Caution: move_lookups() expects a list of filenames, not open filehandles.
        output_writer = MultipleLookupWriter(self._output_spec.output_lookups, self._session_key)
        ancillary_writer = MultipleLookupWriter(self._output_spec.ancillary_lookups, self._session_key)
        return output_writer.move_lookups(output_filenames) and ancillary_writer.move_lookups(ancillary_filenames)

    def setup_writers(self):
        '''Initialize output files for processing records in streaming mode.'''
        
        # Create target lookup temporary files. This should happen here and not
        # at initialization.
        self._create_output_files()

        # Keep track of the writers that have been used.
        self._output_writers_used = {}

    def process_streaming_record(self, record):
        '''Write the data to a set of Splunk lookup tables.
        
        @param records: A dictionary of field -> list of dicts representing records.
        @param ancillary_data: A dictionary of field -> list of values
        
        Data in ancillary data will be written directly to a lookup table if one is
        defined.
        
        Data in converted_input will be ROUTED to a lookup table depending on the
        value of the key field, if routing is defined. This means that converted_input
        records can be directed to different lookup tables for different purposes (but not
        duplicated in multiple lookup tables, currently - only one output file per record
        is supported).
        '''

        key_field, key_field_value, output_rows = record
        
        # Conditionally split the lookup table if desired.
        # This is useful in instances where both a CIDR and
        # string lookup must be defined from the same input.
        # Initially, the target is whatever lookup is defined for
        # the current key_field_name; e.g., "ip" => assets_by_ip.csv
        target = key_field
        routers = self._output_spec.routing.get(key_field, None)
        # If there are routers for this field name (there can be multiple),
        # check the value against each routing function. If there is a match, 
        # redirect the output for these records. Each routing function should,
        # otherwise the LAST match will succeed.
        if routers is not None:
            for lookup_name, condition in routers.items():
                if condition(key_field_value):
                    target = lookup_name

        if output_rows:
            self._output_writers[target].writerows(output_rows)
        else:
            # Handle the single-column lookup table case.
            self._output_writers[target].writerow({key_field: key_field_value})

        self._output_writers_used[target] = True

    def close_writers(self):
        '''Move lookup table files into place.'''

        # CLEANUP OUTPUT
        # Recall that multiple key fields can map to a single output file,
        # via the routing table.
        # 1. Retain the file names for return to caller.
        # 2. Write a default row to any unused output files.
        # 3. Close the files.
        output_filenames = {} 
        output_files_unused = set(self._output_files.values())
  
        for k, fh in self._output_files.iteritems():
            output_filenames[k] = fh.name
              
            if self._output_writers_used.get(k, False):
                output_files_unused.discard(fh)
  
        for k, fh in self._output_files.iteritems():
  
            if fh in output_files_unused:
            # If no rows were written to the file, output a default line
            # which will never match. This prevents a UI error from occurring
            # when an automatic lookup table consists of only a header line.
                try:
                    self._output_writers[k].writerow({})
                except ValueError:
                    # File already written to and closed.
                    pass
            fh.close()
            
        # Caution: move_lookups() expects a list of filenames, not open filehandles.
        output_writer = MultipleLookupWriter(self._output_spec.output_lookups, self._session_key)
        return output_writer.move_lookups(output_filenames)

    def write_ancillary_data(self, ancillary_data):
        
        ancillary_filenames = {} 
        for target_field, values in ancillary_data.items():
            # Writerows expects a list of dicts.
            values = [{target_field: v} for v in values]
            self._ancillary_output_writers[target_field].writerows(values)
            self._ancillary_output_files[target_field].close()
            ancillary_filenames[target_field] = self._ancillary_output_files[target_field].name
         
        ancillary_writer = MultipleLookupWriter(self._output_spec.ancillary_lookups, self._session_key)
        return ancillary_writer.move_lookups(ancillary_filenames)
