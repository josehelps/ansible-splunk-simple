'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import abc
import collections
import itertools
import pprint
import sys

from ..error import Errors
from ..error import LookupConversionErrors
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Utils', 'lib']))
from SolnCommon.lookup_conversion.fields import FieldMapping
from SolnCommon.modular_input import logger


class LookupConversionSpec(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, fieldmap, *args, **kwargs):
        '''Create a lookup conversion specification. A lookup conversion handler
        class should define the following:
        
        @param fieldmap: A list of FieldMappings governing how input fields
                         will be converted.
        '''

        # Positional arguments        
        self._fieldmap = fieldmap
        
        # Keyword arguments
        self._allow_custom = kwargs.get('allow_custom', True)
        self._allow_mv_keys = kwargs.get('allow_mv_keys', True)
        self._eliminate_duplicates = kwargs.get('eliminate_duplicates', False)
        self._merge_fields = kwargs.get('merge_fields', [])
        self._mv_key_fields = kwargs.get('mv_key_fields', [])
        
        # Custom data
        self._custom_data = kwargs.get('custom_data', None)

    # Properties for positional arguments        
    @property
    def fieldset(self):
        '''The set of expected fields.'''
        return set(self._fieldmap.keys())

    # Other properties
    @property
    def custom_data(self):
        '''The custom data for this specification, if any.'''
        return self._custom_data
    
    @property
    def key_fieldset(self):
        '''The set of key fields.'''
        return set([k for k, v in self._fieldmap.iteritems() if v.is_key_field])

    @property
    def mv_key_fieldset(self):
        '''The set of key fields treated as multivalued.'''
        return set(self._mv_key_fields)
    
    @property
    def merge_fieldset(self):
        '''The set of fields to merge upon output.'''
        return set(self._merge_fields)
    
    @property
    def generated_fieldset(self):
        '''The set of generated fields.'''
        return set([k for k, v in self._fieldmap.iteritems() if v.is_generated])

    @property
    def persistent_fieldset(self):
        '''The set of generated fields.'''
        return set([k for k, v in self._fieldmap.iteritems() if v.is_persistent])

    @property
    def tracked_mappings(self):
        '''The set of tracked mappings. This is used because we may have
        a mismatch between input name and output name, so we use the identity
        of the mapping to determine whether a fields contents should be
        tracked.'''            
        return set([v for v in self._fieldmap.itervalues() if v.is_tracked])

    @property
    def mappings(self):
        '''The dictionary of field mappings.'''
        return self._fieldmap
    
    @property
    def allow_custom(self):
        '''True if custom fields are allowed by this spec.'''
        return self._allow_custom or False
    
    @property
    def allow_mv_keys(self):
        '''True if multivalued key fields are allowed by this spec.'''
        return self._allow_mv_keys
    
    @property
    def eliminate_duplicates(self):
        '''True if the streaming output processor should attempt duplicate
        elimination (will increase processing time).'''
        return self._eliminate_duplicates
    
    def get_dynamic_mapping(self, field):
        '''Return a dynamic field mapping for this field name.
        Note that dynamic field mappings cannot use deferred processing.'''
        return FieldMapping(field)


class LookupConversionHandler(object):
    '''Class for generating lookup(s) from an input table.'''

    __metaclass__ = abc.ABCMeta

    def __init__(self, spec, session_key, *args, **kwargs):
        '''Create a lookup conversion specification.

        Keyword arguments:
        @param spec: A LookupConversionSpec object.
        @param session_key: A Splunk session key used for REST communication.
        '''

        self._spec = spec
        self._sessionKey = session_key
        # Container for errors. Each error is a string message that may or may
        # optionally associate with a list of records. A string-only error
        # should have a key of None.
        self._errors = {}

    def _get_field_metadata(self, all_fields):
        '''Process the fields received as input and calculate various values
        required to complete the processing. Some values (all_fields, 
        custom_fields, missing_input_fields) can only be calculated at
        conversion time; the remainder are retrieved from the specification.
        
        Returns: A named tuple containing the following:
        
        actual: The set of field names found in the input data.
        expected: The set of field names expected in the input data.
        mv_keys: The set of input field names to be regarded as multivalued key fields.
        merge: The set of field names that will be merged on output.
        output: The set of output field names.
        custom: The set of custom field names.
        missing: The set of missing fields.
        '''
        
        custom_fields = set(all_fields) - (self._spec.fieldset - self._spec.generated_fieldset)
        missing_input_fields = (self._spec.fieldset - self._spec.generated_fieldset) - set(all_fields)
        
        FieldMetadata = collections.namedtuple('FieldMetadata',
            ['actual',
             'expected',
             'generated',
             'merge',
             'mv_keys',
             'custom',
             'missing'])

        return FieldMetadata(
            set(all_fields),
            self._spec.fieldset,
            self._spec.generated_fieldset,
            self._spec.merge_fieldset,
            self._spec.mv_key_fieldset,
            custom_fields,
            missing_input_fields)
    
    def _check_errors(self):
        '''Add warning messages for input/output field mismatches, ignoring 
        generated fields.
        
        Two options that may be set in the LookupConversionspec control the
        behavior of this method in the presence or absence of data for specific
        fields:
        
        1. Extra fields may be allowed in the output by the following handler
           option (defaults to True):
        
            allow_custom_fields = True

          If False, extra input fields will be ignored. but an error message will
          be logged.
          
        2. Missing input fields may be ignored by the following handler option
           (defaults to False):
        
            ignore_missing_input = False 
            
           If True, missing input fields will not abort the script but will 
           receive a blank value. If True, missing input fields will abort the
           script processing for that record. An error will be logged in all
           cases.
           
        SIDE EFFECT: Updates self._errors.
        '''

        if self._fieldmeta.custom:
            self._errors['%s: %s'.format(LookupConversionErrors.ERR_EXTRA_INPUT_FIELDS, ','.join(self._fieldmeta.custom))] = None
        if self._fieldmeta.missing:
            self._errors['%s: %s'.format(LookupConversionErrors.ERR_MISSING_INPUT_FIELDS, ','.join(self._fieldmeta.missing))] = None
        return None

    def process(self, merged_data):
        '''This is the main conversion routine.
        
        @param merged_data: A tuple of:
            all_fields -> a set of all field names from the source data
            records    -> a list of namedtuples
        
        Each named tuple represents a record. Named tuples allow you to reference
        field values directly using getattr(), but don't require construction 
        of a dictionary object, so are more memory-efficient. Also immutable.
        '''

        all_fields, contents = merged_data 

        # Obtain all field metadata.
        self._fieldmeta = self._get_field_metadata(all_fields)

        # Collect warnings if there are missing or extra input fields.
        self._check_errors()

        # Create the output lists
        completed = []
        deferred = []
        completed_after_deferral = []
        
        # Maintain count of records for logging in INFO mode
        processed_count_log_interval = 1

        # Run field conversions (initial pass).
        src_index = 0
        index = 0
        for filename, records in contents.iteritems():
            for src_index, record in enumerate(records, 0):
                
                output, deferredFields, invalidField, missing, extra = self._process_record(record, record_num=index)
    
                if invalidField is not None:
                    # Line contains some invalid field data. this could be:
                    #    completely invalid fields
                    #    extra input fields
                    #    missing input fields
                    err = self._errors.setdefault('invalid', [])
                    err.append((filename, src_index, index))
                    continue
                elif output and deferredFields:
                    deferred.append((output, deferredFields, index))
                elif output:
                    completed.append(output)
                else:
                    err = self._errors.setdefault('unknown', [])
                    err.append((filename, src_index, index))

                # Increment index.
                index += 1

                # Log progress at increasing intervals.
                if index % processed_count_log_interval == 0:
                    logger.info('PROCESSING: %d input lines complete.', index)
                    processed_count_log_interval *= 10

        # Run post-processing actions.
        ancillary_data = self._postprocess()
                
        # Run deferred field conversions.
        if deferred:
            completed_after_deferral = self._process_deferred_records(deferred)

        logger.info('PROCESSING: All %d input lines completed.', index)

        # Format the lookup table.
        for record in itertools.chain(completed, completed_after_deferral):
            for formatted in self.format_streamed_output(record):
                yield formatted

    def _process_deferred_records(self, deferred):
        '''For each deferred record, process the deferred fields.
        
        @param deferred: An array of deferred entries to process.
        @return: A list of completed lines, as a list of dictionaries.
        
        Each entry in deferred should consist of a tuple in the form:
        
            (output, deferred_fields, num)
            
        where:
        
            output = A dictionary of key-value pairs.
            deferred_fields = A list of keys in output to be processed.
            num = The position of the record in the initial input list.
        
        The processing routine for each deferred field in deferred_fields is 
        defined in the specific FieldMapping associated with the field by name in
        self._spec.mappings; the name of this routine is always "process_deferred()".

        '''

        logger.info('PROCESSING: Beginning conversion of lines with fields marked for deferred processing.')
        completed = []

        for entry in deferred:
            output, deferred_fields, num = entry

            for deferred_field in deferred_fields:

                mapping = self._spec.mappings.get(deferred_field, None)

                # Generate the field output. Note that we do not check for
                # dependencies during deferred processing so order of 
                # processing is not guaranteed.
                if mapping is not None:
                    # Output is a simple dict here, not a tuple as when we 
                    # conducted the first pass since we have no need to 
                    # defer any more fields.
                    deferred_requirements = {i: output.get(i, None) for i in mapping.deferred_requires}
                    # Process the deferred conversion.
                    output[deferred_field] = mapping.convert_deferred(output[deferred_field], deferred_requirements, num)
                else:
                    # No mapping.
                    # TODO: return ERR_DEFERRED_CONVERSION_NOT_IMPLEMENTED error here.
                    pass

            completed.append(output)
            
        logger.info('PROCESSING: Completed conversion of lines with fields marked for deferred processing.')
        return completed

    def _process_record(self, record, record_num):
        '''Process an input record.
        
        @param record: The input record as a named tuple.
        
        @return: A tuple containing (in the order shown):
            1. output dictionary
            2. List of deferred fields.
            3. An invalid field, if present.
            4. List of extra fields in the record.
            5. List of missing fields in the record.
            
        Note that only one invalid field is returned per line. This is necessary 
        because if one field is invalid, its dependencies might become undecidable.
        An invalid field aborts processing of the line.
        '''
        
        # Set up variable to hold list of fields that require deferred processing.
        deferredFields = []

        # Maintain a list of fields remaining to be processed,
        # for dependency handling. If custom fields are permitted, add them to
        # the list. Initially this set consists of all fields.
        if self._spec.allow_custom:
            remaining = self._fieldmeta.custom | self._fieldmeta.expected
        else:
            remaining = self._fieldmeta.expected.copy()
        
        # Create output dictionary
        output = {i: '' for i in remaining}

        # Dependency mapping is handled by maintaining a list of the fields
        # remaining to be processed. Since each field can specify its own set of 
        # dependencies, we simply skip over fields that have unprocessed dependencies,
        # deferring processing until a later iteration of the "while" loop. 
        # Eventually all fields "bubble up" to the top. This can be O(n!) in the
        # worst case but in practice it is a small number of iterations, since the
        # dependency ordering is programmer-defined, in the LookupConversionSpec.
        # TODO: future; handle dependency ordering at spec initialization time.
        while len(remaining) > 0:

            # Fields being processed in this loop.
            # TODO: check this loop condition.
            for field in (self._fieldmeta.expected | self._fieldmeta.custom) & remaining:
                
                # Set to true if any fields are deferred.
                isDeferred = False
                
                # Get the field mapping. If the field mapping could not be 
                # found, AND custom fields are permitted, use the default
                # mapper (which is generally to output the field as a string).
                # Note that this prohibits the use of a field named "default_mapper"
                # in the input CSV.
                mapping = self._spec.mappings.get(field, None)
                if self._spec.allow_custom and mapping is None:
                    mapping = self._spec.get_dynamic_mapping(field)

                if mapping:
                    # A valid class to perform the mapping exists.
                    
                    # Now normalize the field value. Normalizing to None permits
                    # the mapping action to succeed, regardless of whether 
                    # the field is a generated field or converted field.
                    # Generated fields can be missing entirely from the input CSV;
                    # if they are mistakenly present, the input will be 
                    # ignored by the mapping's convert() function.
                    normalized_field = getattr(record, field, None)

                    # Validate the input; if invalid, discard the input line.
                    if not mapping.validate(normalized_field):
                        return (None, None, field, None, None)
                    
                    # Check dependencies.
                    if len(set(mapping.depends) & remaining) == 0:
                        
                        # The values of other fields PRIOR to conversion that
                        # must be passed in to process this field.
                        if mapping.requires:
                            requirements = {i: getattr(record, i, None) for i in mapping.requires}
                        else:
                            # No unconverted field values are required.
                            requirements = {}
                        # Either all dependencies are complete, or no 
                        # dependencies. Perform field conversion.
                        mapping.preprocess(normalized_field)
                        dependencies = {i: output[i] for i in mapping.depends}
                        output[field], isDeferred = mapping.convert(normalized_field, 
                            dependencies=dependencies,
                            requirements=requirements,
                            record_num=record_num)
                        remaining.discard(field)
                    else:
                        # Dependencies cannot be fulfilled right now.
                        # Leave the field in place and try again on the next loop.
                        pass

                    # If field requires deferred processing, note it in the list of deferredFields now.
                    if isDeferred:
                        deferredFields.append(field)

                else:
                    # An output field had no associated class to perform the mapping.
                    # Thus field conversion is complete (no mapping for the field)
                    remaining.discard(field)

        return (output, deferredFields, None, None, None)

    def process_streaming_record(self, record):
        '''Process an input record in streaming fashion, without
        deferral or dependency handling.
        
        @param record: The input record as a named tuple.
        
        @return: An output dictionary.

        Invalid lines are logged and discarded.
        '''
        
        # Maintain a list of fields remaining to be processed. Custom fields are
        # not yet supported in streaming conversions.
        remaining = self._fieldmeta.expected.copy()

        # Create output dictionary
        output = {i: '' for i in remaining}

        for field in remaining:
                
            # Get the field mapping. If the field mapping could not be 
            # found, AND custom fields are permitted, use the default
            # mapper (which is generally to output the field as a string).
            # Note that this prohibits the use of a field named "default_mapper"
            # in the input CSV.
            mapping = self._spec.mappings.get(field, None)
            if self._spec.allow_custom and mapping is None:
                mapping = self._spec.get_dynamic_mapping(field)

            # List of requirements for this conversion.
            requirements = None

            if mapping:
                # A valid class to perform the mapping exists.
                
                # Get requirements for this field conversion.
                if mapping.requires:
                    requirements = {i: getattr(record, i, None) for i in mapping.requires}

                # Now normalize the field value. Normalizing to None permits
                # the mapping action to succeed, regardless of whether 
                # the field is a generated field or converted field.
                # Generated fields can be missing entirely from the input CSV;
                # if they are mistakenly present, the input will be 
                # ignored by the mapping's convert() function.
                normalized_field = getattr(record, field, None)

                # Validate the input; if invalid, discard the input line.
                if not mapping.validate(normalized_field):
                    logger.info('PROCESSING: Discarded invalid record with field %s=%s', field, normalized_field)
                    yield None
                
                # Collect ancillary data.
                if mapping in self._spec.tracked_mappings and normalized_field:
                    mapping.preprocess(normalized_field)

                # Convert the field.
                output[field], isDeferred = mapping.convert(normalized_field, 
                    dependencies=None,
                    requirements=requirements,
                    record_num=None)
            else:
                logger.info('PROCESSING: Discarded record with invalid field name %s', field)
                yield None

        for formatted in self.format_streamed_output(output):
            yield formatted

    def _postprocess(self):
        '''Conduct postprocessing routines for all field mappings.
        
        @return: A dictionary { field : set(values) } for any fields that 
            have is_tracked = True.
        '''

        ancillary_data = {}
        logger.info('PROCESSING: Beginning postprocessing actions.')
        for name, mapping in self._spec.mappings.iteritems():
            values = mapping.postprocess()
            if values:
                ancillary_data[name] = values
        logger.info('PROCESSING: Completed postprocessing actions.')
        return ancillary_data

    def _format_output(self, records, merge_fields):
        '''Print CSV-formatted output to a temporary file in Splunk-acceptable
        lookup table format for multivalued field handling.
         
        @param records: A list of dictionaries representing the CSV. A
                        key-value pair in the dictionary may have a list
                        as the value.
        '''
 
        logger.info('PROCESSING: Beginning output formatting.')
        
        # Get the set of key fields. Only one multi-valued key field
        # can exist in the set, per output record).
        key_fields = self._spec.key_fieldset
 
        # Get the set of persistent fields. Persistent fields are neither key fields
        # nor multi-valued fields.
        persistent_fields = self._spec.persistent_fieldset
         
        # Create skeleton dictionary of column names for copying.
        skeldict = dict.fromkeys(self._fieldmeta.expected, '')
         
        # Sorted list of key field names.
        key_field_names = sorted(key_fields)
  
        # Maintain count of lines for logging in INFO mode
        processed_count = 0
        processed_count_log_interval = 1
         
        # List of already-processed keys. This is used for duplicate detection.
        # If the current record has a duplicate key, it can either be dropped,
        # or a selected set of fields specified in merge_fields can be merged
        # with the previous record.
        processed = {}
         
        for record in records:
             
            # Log progress at increasing intervals.
            processed_count += 1
            if processed_count % processed_count_log_interval == 0:
                logger.info('FORMATTING: %d input lines complete.', processed_count)
                processed_count_log_interval *= 10
  
            # If merge_fields is true, force the fields to be multi-valued.
            for merge_field in merge_fields:
                if merge_field in record and not isinstance(record.get(merge_field), list):
                    record[merge_field] = [record[merge_field]]
                
            # The fields that are multi-valued in the current record, which now 
            # includes any merge_fields.
            mv_fields = set([field for field in record.keys() if isinstance(record.get(field), list)])
             
            # The fields that are single-valued in the current record, sans the persistent fields
            # which will be included in each row.
            sv_fields = self._fieldmeta.expected - mv_fields - persistent_fields
 
            # Ensure that only one key field is multi-valued.
            if len(set(key_fields & mv_fields)) > 1:
                # Skip the record entirely; it would generate an ambiguous lookup table.
                logger.warn(Errors.formatErr(LookupConversionErrors.ERR_AMBIGUOUS_INPUT_RECORD, pprint.pformat(record)))
                continue
 
            # Remove the key fields from both lists if required.
            mv_fields.difference_update(key_fields)
            sv_fields.difference_update(key_fields)
             
            # Add any multi-valued key fields back.
            mv_fields.update(set(self._fieldmeta.mv_keys))
 
            # Maintain a sorted list to avoid recalculating.
            sorted_mv_fields = sorted(mv_fields)
             
            # We have now retrieved three independent sets of fields:
            #
            #    key_fields: The key fields, both multi- and single-valued.
            #    mv_fields:  The multi-valued fields (key and non-key).
            #    sv_fields:  The non-key, single-valued fields.
            #
            # Construct two additional lists using the above:
            #
            # 1. A list of the permutations of the key fields.
            #
            #    The list comprehension used to generate the permutations list
            #    is complex:
            #
            #    a. Sort the key fields so we can recover the ordering.
            #    b. Retrieve the value for each key field AS A LIST.
            #       This is necessary so that the value can be passed to
            #       itertools.product(*iterables) and itertools.izip_longest(*iterables),
            #       which both expect a variable-argument list of iterators.
            #
            #    At the end, key_field_permutations (#1) will contain all
            #    variants of the key fields. For instance:
            #
            #       ip,mac,dns,nt_host
            #       1.2.3.4-1.2.3.5,,myhost,myhost.com
            #
            #    will produce:
            #
            #       ('myhost', '1.2.3,4', '', 'myhost.com')
            #       ('myhost', '1.2.3.5', '', 'myhost.com')
            #
            #    Note that the order of the fields in the permutation is 
            #    lexicographical by field name.
            #
            # 2. A list of successive selections of multi-valued fields,
            #    selecting as many values as possible from each field until
            #    all fields are exhausted.
            #
            #    For instance, given the following list of values:
            #
            #       [ 'a', ['b', 'c'], 'd']
            #
            #    we would generate the list:
            #
            #      [  [ 'a', 'b', 'd'],
            #         [ '', 'c', ''] ]
            #
             
            key_field_values = [record.get(i) if isinstance(record.get(i), list) else [record.get(i)] for i in key_field_names]
            key_field_permutations = itertools.product(*key_field_values)
            mv_field_selections = [record.get(i) if isinstance(record.get(i), list) else [record.get(i)] for i in sorted_mv_fields]
 
            # Persistent fields can only be single-valued, so no checking for lists here.
            persistent_fields_dict = {i: record.get(i) for i in persistent_fields}
 
            # Expand the list here to avoid recalculating inside the next loop.
            mv_field_selections = [i for i in itertools.izip_longest(*mv_field_selections)]
                  
            for perm in key_field_permutations:
 
                # 1. Create a list of output rows. Each row will be expressed
                #     as a dictionary for use by the DictWriter instance.
                #     The DictWriter will print the column keys in 
                #     lexicographical order.
                outputrows = []
                 
                # 2. Add the main row with all output values for this permutation.
                outputdict = skeldict.copy()
                key_fields_dict = {k: v for k, v in zip(key_field_names, perm)}
                 
                # 3. Add the key fields to the main row
                outputdict.update(key_fields_dict)
                 
                # 4. Add all the single-valued fields to the main row.
                outputdict.update((sv_field, record.get(sv_field)) for sv_field in sv_fields)
                 
                # 5. Add all the persistent fields to the main row.
                outputdict.update(persistent_fields_dict)
                 
                # 6. If any key fields are multi-valued, drop them from the permutation
                #    as they will be handled in step 7 below. This assumes also that
                #    the multi-valued key fields have been added back to the mv_field_selections
                #    via the presence of the mv_fields.update() statement in line 418, above.
                #    This ensures that the key fields will not be duplicated in the output.
                for k in self._fieldmeta.mv_keys:
                    outputdict[k] = ''
                 
                # 7. Append the first output row.                
                outputrows.append(outputdict)
 
                # 8. Add a row for each multi-valued field WITHOUT any other fields.
                #    The asset_key field will be set later.
                for mv_field_selection in mv_field_selections:
                    mv_outputdict = skeldict.copy()
                    mv_outputdict.update(zip(sorted(mv_fields), mv_field_selection))
                    outputrows.append(mv_outputdict)

                # 9. Now for each key value, duplicate the rows
                #    once for each NON-EMPTY asset key in the original permutation.
                #    If we are outputting multi-valued key fields, also make sure
                #    to drop the row that includes the "extra" value of the current key.
                for key_field_name, key_field_values in itertools.ifilter(lambda (x, y): y not in [[''], ''], key_fields_dict.iteritems()):
                    if not isinstance(key_field_values, list):
                        key_field_values = [key_field_values]
                    for key_value in key_field_values:
                        # Output the records.
                        if not processed.get((key_field_name, key_value), False):
                            # This is a new key value.
                            processed[(key_field_name, key_value)] = []
                            for outputrowdict in outputrows:
                                tmpdict = outputrowdict.copy()
                                tmpdict.update([('key', key_value)])
                                # Add persistent fields.
                                tmpdict.update(persistent_fields_dict)
                                processed[(key_field_name, key_value)].append(tmpdict)
                        else:
                            # We have encountered a duplicate key.
                            # 1. If merge_fields is a non-empty list, merge the
                            #    fields it specifies from the current and previous 
                            #    records. The PREVIOUS records's remaining fields
                            #    will be retained.
                            # 2. If merge_fields is False, discard the current entry.
                            #    This is the default and establishes a priority
                            #    of records which may be difficult to diagnose.
                            #    In this case, there should generally NOT be overlap
                            #    in the input files.
                            if merge_fields:
                                logger.debug('MERGING: Duplicate record: %s', key_value)
                                for outputrowdict in outputrows:
                                    tmpdict = {}
                                    for merge_field in merge_fields:
                                        val = outputrowdict.get(merge_field, None)
                                        if val:
                                            tmpdict.update({merge_field: val})
                                    if tmpdict:
                                        tmpdict.update([('key', key_value)])
                                        processed[(key_field_name, key_value)].append(tmpdict)
                            else:
                                logger.info('DISCARDING: Duplicate record: %s', key_value)
 
        # 10. Return the processed items as a dictionary
        #     key_value -> list of dicts representing records.
        #     This will be consumed by the output handler and routed to the correct
        #     lookup table.
        logger.info('PROCESSING: Completed output formatting.')
        return processed

    def setup_streamed_output(self):
        '''Perform setup actions to prepare for streaming field conversions.'''

        # Obtain all field metadata. Note that custom fields are not
        # currently supported in streaming mode (this would require reading all
        # input headers in before processing any records).
        self._fieldmeta = self._get_field_metadata(self._spec.fieldset)
        
        # Key field names
        self._key_field_names = sorted(self._spec.key_fieldset)
        
        # Set of all field names, minus the field "key".
        self._all_field_names = sorted(set(self._fieldmeta.expected))
        if 'key' in self._all_field_names:
            self._all_field_names.remove('key')
        
        # Set of all field names, minus the key fields
        self._all_nonkey_field_names = sorted(set(self._fieldmeta.expected - self._spec.key_fieldset))
        if 'key' in self._all_nonkey_field_names:
            self._all_nonkey_field_names.remove('key')
        
        # Set used for duplicate detection, if requested.
        self._processed = set('')

    def format_streamed_output(self, record):
        '''Print CSV-formatted output to a temporary file in Splunk-acceptable
        lookup table format for multivalued field handling.
         
        @param record: A dictionary.
        '''

        # Ensure that only one key field is multi-valued.
        if len(set(self._key_field_names) & set([field for field in record.keys() if isinstance(record.get(field), list)])) > 1:
            # Skip the record entirely; it would generate an ambiguous lookup table.
            logger.warn(Errors.formatErr(LookupConversionErrors.ERR_AMBIGUOUS_INPUT_RECORD, pprint.pformat(record)))
            yield None
        
        # Create sorted list of iterable field values from the fields for passing to izip_longest.
        # Note that this may not have some fields; those will be filled in by izip_longest's "fillvalue" parameter.
        # Conversion to list is so we can permute the key field values via itertools.product.
        key_field_values = [record.get(i) if isinstance(record.get(i), list) else [record.get(i)] for i in self._key_field_names]
        # We should be guaranteed to have a list of length > 1 here if the entry
        # is a list, since the default field value should always be the empty string.
        # This is only used where key fields are NOT multivalued, as it drops
        # any key field values beyond the first in the list case.
        key_field_dict = zip(self._key_field_names, [record.get(i)[0] if isinstance(record.get(i), list) else record.get(i) for i in self._key_field_names])
        # Include multi-valued key fields in the output.
        if self._spec.allow_mv_keys:
            all_field_values = [record.get(i) if isinstance(record.get(i), list) else [record.get(i)] for i in self._all_field_names]
        else:
            all_field_values = [record.get(i) if isinstance(record.get(i), list) else [record.get(i)] for i in self._all_nonkey_field_names]
        key_field_permutations = itertools.product(*key_field_values)
        
        # Used to eliminate duplicate insertions of key fields.
        first = True

        # We must return a list of [(key, value) [items]] for routing
        # of output to work.
        for perm in key_field_permutations:
            for key_field, key_field_values in zip(self._key_field_names, perm):
                # Filter out values of the key field to prevent duplicates. 
                if key_field_values != ['']:
                    # Key field may be multi-valued. If it is, the value of
                    # include_mv_key_field_values governs whether or not ALL values
                    # of the multi-valued "key" field are also included in the original
                    # field's value. This can cause combinatorial explosion in the case
                    # where a subnet is expanded to 255 IP addresses, since for
                    # EVERY IP address in the subnet, the "ip" field will have 255 values.
                    if not isinstance(key_field_values, list):
                        key_field_values = [key_field_values]
                    for key_value in filter(lambda x: x != '', key_field_values):
                        if (key_field, key_value) not in self._processed:
                            outputlist = []
                            first = True
                            if self._spec.allow_mv_keys:
                                # Multi-valued key field case.
                                for fields in [value for value in itertools.izip_longest(*all_field_values, fillvalue='')]:
                                    tmpdict = {k: v for k, v in zip(self._all_field_names, fields)}
                                    tmpdict['key'] = key_value
                                    outputlist.append(tmpdict)
                            else:
                                # Single-valued field case.
                                for fields in [value for value in itertools.izip_longest(*all_field_values, fillvalue='')]:
                                    tmpdict = {k: v for k, v in zip(self._all_nonkey_field_names, fields) if k != key_field}
                                    tmpdict['key'] = key_value
                                    if first:
                                        # Add in all the values of the other key fields.
                                        tmpdict.update({k: v for k, v in key_field_dict if k != key_field and v not in [[''], '']})
                                        tmpdict[key_field] = key_value
                                        first = False
                                    outputlist.append(tmpdict)
                            yield key_field, key_value, outputlist
                        else:
                            logger.info('DISCARDING: Duplicate record: %s', key_value)
                    if self._spec.eliminate_duplicates:
                        self._processed.update([(key_field, i) for i in key_field_values])
                else:
                    # No values for this key.
                    pass

    def finalize_streaming(self):
        '''Runs post-processing actions and returns ancillary data.'''
        logger.info('FINALIZING: Collecting ancillary data.')
        return self._postprocess()
