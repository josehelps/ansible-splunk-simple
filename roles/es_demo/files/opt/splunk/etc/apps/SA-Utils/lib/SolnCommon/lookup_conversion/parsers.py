'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import abc
import csv
import re
import sys

import splunk
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))

from SolnCommon.context_managers import open_w_err


class Parser(object):

    __metaclass__ = abc.ABCMeta
    
    def __init__(self, *args, **kwargs):
        '''Initialize a parser. Any re.error exceptions raised will be passed to the caller.'''
        pass

    @abc.abstractmethod
    def parse(self, filename):
        '''Parse the input files.'''
        raise NotImplementedError('This method must be overridden by a concrete class.')


class GenericParser(Parser):
        
    def __init__(self, fields, delim_regex=None, extract_regex=None, ignore_regex=None):
        '''Initialize a parser. Any re.error exceptions raised will be passed to the caller.'''
        
        self._fields = fields
        self._fieldnames = set()
        
        try:
            self._delim_regex = re.compile(delim_regex, re.UNICODE) if delim_regex else None
            self._extract_regex = re.compile(extract_regex, re.UNICODE) if extract_regex else None
            self._ignore_regex = re.compile(ignore_regex, re.UNICODE) if ignore_regex else None
        except re.error:
            raise

        self._replacements = [(i.split(':', 1)) for i in csv.reader([self._fields]).next()]

    def get_field_names(self):
        
        return set([i[0] for i in self._replacements])

    def parse(self, filename):
        '''The parse method.
        
        @param filename: The file to parse.
        '''
                
        lines = []
        err = None
        match_objtype = type(re.search('', ''))

        # Method will be a callable object that accepts each line of the input
        # file as an argument.
        if self._extract_regex:
            parse_method = self._extract_regex.search
        elif self._delim_regex:
            parse_method = self._delim_regex.split
        else:
            raise ValueError('Parser could not be instantiated: one of delim_regex or extract_regex is required.')
        
        # TODO: Add code to drop remaining lines in file if > N percent error
        # out or if exact match is not found.
        with open_w_err(filename, 'r') as (f, err):
            if not err:
                for num, line in enumerate(f):
                    newfields = {}
                    if not(self._ignore_regex) or (self._ignore_regex and not self._ignore_regex.search(line)):
                        extracted_fields = parse_method(line.strip())
                        for field_name, replacement_str in self._replacements:
                            if isinstance(extracted_fields, match_objtype):
                                # Strip leading and trailing quotes from the regex.
                                rx_str = replacement_str.strip('"\'').replace('$', '\\')
                                try:
                                    newfields[field_name] = extracted_fields.expand(rx_str)
                                except (re.error, IndexError):
                                    # Replacement failed, usually due to an invalid 
                                    # group reference. Line skipped.
                                    pass
                            elif isinstance(extracted_fields, list):
                                # Strip leading and trailing quotes from the regex.
                                rx_str = replacement_str.strip('"\'')
                                # Since we can't use the MatchObject's expand() method,
                                # since we have a list of strings to work with,
                                # create a formatter from the replacement string.
                                try:
                                    formatter = re.sub('\$(\d+)', '{\\1}', replacement_str)
                                    # Note the insertion of an extra element - this
                                    # allows users to specify fields in the "normal"
                                    # fashion counting up from 1.
                                    newfields[field_name] = formatter.format('', *extracted_fields)
                                except (re.error, IndexError):
                                    # Replacement failed, usually due to an invalid 
                                    # group reference. Line skipped.
                                    pass                                    
                            else:
                                # Parsing of the line did not return a match object.
                                # This generally means there is an error in the parsing
                                # configuration, but may also indicate bad data in one line.
                                pass

                        lines.append(newfields)
                            
                    else:
                        # Line was either ignored or skipped as a header line.
                        pass
            else:
                # Error opening file.
                pass

        return lines, err


class GenericStreamingParser(Parser):
        
    def __init__(self, fields, delim_regex=None, extract_regex=None, ignore_regex=None, skip_header_lines=None):
        '''Initialize a streaming parser. Any re.error exceptions raised will be passed to the caller.'''
        
        self._fields = fields
        self._fieldnames = set()
        
        try:
            self._delim_regex = re.compile(delim_regex, re.UNICODE) if delim_regex else None
            self._extract_regex = re.compile(extract_regex, re.UNICODE) if extract_regex else None
            self._ignore_regex = re.compile(ignore_regex, re.UNICODE) if ignore_regex else None
            self._skip_header_lines = int(skip_header_lines) or 0
        except (ValueError, re.error):
            raise

        self._replacements = [(i.split(':', 1)) for i in csv.reader([self._fields]).next()]

    def get_field_names(self):
        
        return set([i[0] for i in self._replacements])

    def parse(self, filename):
        '''The parse method.
        
        @param filename: The file to parse.
        '''

        match_objtype = type(re.search('', ''))

        # Method will be a callable object that accepts each line of the input
        # file as an argument.
        if self._extract_regex:
            parse_method = self._extract_regex.search
        elif self._delim_regex:
            parse_method = self._delim_regex.split
        else:
            raise ValueError('Parser could not be instantiated: one of delim_regex or extract_regex is required.')
        
        # TODO: Add code to drop remaining lines in file if > N percent error
        # out or if exact match is not found.
        with open(filename, 'r') as f:
            for lineno, line in enumerate(f):
                newfields = {}
                if lineno >= self._skip_header_lines and (not(self._ignore_regex) or (self._ignore_regex and not self._ignore_regex.search(line))):
                    # Note: The line is not completely stripped of whitespace, 
                    # to accommodate tab-delimited formats with leading tabs. 
                    # Field processors in fields.py are responsible for
                    # stripping extraneous whitespace from field content.
                    # However, line ending characters are removed. 
                    extracted_fields = parse_method(line.strip('\r\n'))
                    for field_name, replacement_str in self._replacements:
                        if isinstance(extracted_fields, match_objtype):
                            # Strip leading and trailing quotes from the regex.
                            rx_str = replacement_str.strip('"\'').replace('$', '\\')
                            try:
                                newfields[field_name] = extracted_fields.expand(rx_str)
                            except (re.error, IndexError):
                                # Replacement failed, usually due to an invalid 
                                # group reference. Line skipped.
                                pass
                        elif isinstance(extracted_fields, list):
                            # Strip leading and trailing quotes from the regex.
                            rx_str = replacement_str.strip('"\'')
                            # Since we can't use the MatchObject's expand() method,
                            # since we have a list of strings to work with,
                            # create a formatter from the replacement string.
                            try:
                                formatter = re.sub('\$(\d+)', '{\\1}', replacement_str)
                                # Note the insertion of an extra element - this
                                # allows users to specify fields in the "normal"
                                # fashion counting up from 1.
                                newfields[field_name] = formatter.format('', *extracted_fields)
                            except (re.error, IndexError):
                                # Replacement failed, usually due to an invalid 
                                # group reference. Line skipped.
                                pass                                    
                        else:
                            # Parsing of the line did not return a match object.
                            # This generally means there is an error in the parsing
                            # configuration, but may also indicate bad data in one line.
                            pass

                    yield newfields
                        
                else:
                    # Line was either ignored or skipped as a header line.
                    yield None
