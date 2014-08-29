'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import abc
import csv
import collections


class AbstractMergeHandler(object):

    __metaclass__ = abc.ABCMeta
    
    def __init__(self):
        pass

    @abc.abstractmethod
    def collect(self):
        '''Collect the files to be merged. This method should return content in
        whatever format is expected by the conversion handler.'''
        raise NotImplementedError('This method must be overridden by a concrete class.')

    def errors(self):
        return self._errors


class CsvFileMergeHandler(AbstractMergeHandler):
    
    def __init__(self, checkpoint_dir=None, stanzas=None, files=None):
        '''Initialize the merge handler.
        
        @param checkpoint_dir: The checkpoint directory.
        @param stanzas: The list of configuration stanzas.
        @param files: A list of tuples (stanza_name, path, last_updated).
        
        '''
        self._checkpoint_dir = checkpoint_dir
        self._stanzas = stanzas
        self._files = files

        # The output as a mapping of filename -> list of named tuples.
        self._records = {}

        # List of errors encountered when merging. This is used for tracking bad
        # input lines. Errors should be added as tuples (filename, lineno, msg)
        self._errors = []

        # The set of all fields. The conversion handler will determine whether
        # extraneous fields should be retained or dropped from the output.
        self._all_fields = set()

    def collect(self, *args, **kwargs):
        '''Read in all the input files.

        @return: A mapping of source_file_name to list of namedtuples 
                representing asset or identity records

        The named tuples returned may NOT have consistent field sets. The 
        ConversionSpec is responsible for dealing with inconsistency based on the
        value of allow_custom_fields.
        '''
        
        for stanza_name, filename, last_updated in self._files:
            # Read each file contents in turn, adding fields from the header
            # line to the output line set.
            with open(filename, 'r') as fh:
                csvfile = csv.reader(fh)
                field_names = csvfile.next()
                self._all_fields.update(field_names)
                FieldTuple = collections.namedtuple('fields', field_names)
                self._records[filename] = []
                for lineno, line in enumerate(csvfile):
                    try:
                        self._records[filename].append(FieldTuple._make(line))
                    except TypeError as exc:
                        self._errors.append((filename, lineno, 'Invalid number of fields in input line.'))

        return self._all_fields, self._records


class LookupMergeHandler(CsvFileMergeHandler):
    
    def __init__(self, *args, **kwargs):
        super(LookupMergeHandler, self).__init__(*args, **kwargs)
