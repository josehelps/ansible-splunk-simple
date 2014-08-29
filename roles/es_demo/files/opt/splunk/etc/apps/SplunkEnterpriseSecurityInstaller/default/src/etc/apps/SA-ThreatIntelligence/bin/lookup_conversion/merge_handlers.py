'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import collections
import os
import re
import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.lookup_conversion.merge import AbstractMergeHandler
from SolnCommon.lookup_conversion.parsers import GenericStreamingParser
from SolnCommon.modinput import logger


class ParsingFileMergeHandler(AbstractMergeHandler):
    
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

        # The set of all fields. The conversion handler will determine whether
        # extraneous fields should be retained or dropped from the output.
        self._all_fields = set()
        
    def collect(self):
        '''Collect records from multiple files, applying a parsing transformation
        to each one.
                
        Currently, we only support delimited text files. Lines that are blank,
        begin with a comment character, or match the regex defined in the ignore_regex 
        parameter are excluded from further processing.
        
        Warnings will be raised in the following circumstances:
        - Missing files. Processing will proceed but raise a warning. This would
          usually indicate a failed download.
        - Files that cannot be processed using the specified Parser will raise
          a warning.
        - Files that are modified in the process of reading will be reread a
          maximum of two times before aborting and raising a warning.          
          @return: None
          
          Side Effect: Populates the self._files array with tuples of the 
          following form, for each stanza that specifies a valid parser:
          
              (checkpoint_filename, threatlist_type, threatlist_name, parser)
          
        '''
        
        # Construct dictionary of stanzas
        # - In the case of checkpoint files, the stanza name is equivalent
        #   to the file name.
        # - In the case of lookup files, this is NOT necessarily the case.
        stanza_dict = {}
        for tmp_stanza in self._stanzas:
            tmp_url = tmp_stanza.get('url', '')
            if tmp_url.startswith('lookup://'):
                stanza_dict[tmp_url.replace('lookup://', '')] = tmp_stanza
            elif tmp_url.startswith('http://') or tmp_url.startswith('https://'):
                stanza_dict[tmp_stanza['name']] = tmp_stanza
                
        # Get the stanza corresponding to the file.
        for stanza_name, filename, last_updated in self._files:
            
            stanza = stanza_dict.get(stanza_name, None)

            if stanza:
                try:
                    parser = GenericStreamingParser(
                        stanza.get('fields', None),
                        stanza.get('delim_regex', None),
                        stanza.get('extract_regex', None),
                        stanza.get('ignore_regex', None),
                        stanza.get('skip_header_lines', 0))
                except (re.error, ValueError) as e:
                    logger.exception('status="Parser error" filename="%s"', filename)
                
                # Metadata for the file, which may be used by the ConversionSpec.
                metadata_fields = ['type', 'name']
                # Avoid using "type" which is reserved word in Python.
                metadata = [stanza.get('typ', ''), stanza_name]

                if parser:
                    # Try to parse the file.
                    # If parsing fails, the file is skipped, and the next 
                    # file will be tried in turn.                        
                    field_names = sorted(parser.get_field_names())
                    FieldTuple = collections.namedtuple('fields', field_names + metadata_fields)
                    self._all_fields.update(field_names)
                    for record in parser.parse(filename):
                        try:
                            if record:
                                yield FieldTuple._make([record[i].strip('"') for i in field_names] + metadata)
                        except IOError:
                            logger.exception('status="Parser raised exception when opening file" filename="%s" record="%s"',filename, record)
                            yield None
                        except ValueError:
                            logger.exception('status="Parser raised exception when parsing file" filename="%s" record="%s"', filename, record)
                            yield None
                        except Exception:
                            logger.exception('status="Parser raised unknown exception" filename="%s" record="%s"', filename, record)
                            yield None
                else:
                    # Parser was not created correctly.
                    logger.error('status="Parser was not created successfully" filename="%s" record="%s"', filename, record)
            else:
                # Stanza was not found.
                logger.error('status="Stanza error" stanza_name="%s" filename="%s"', stanza_name, filename)


class ThreatlistManagerMergeHandler(ParsingFileMergeHandler):
    
    def __init__(self, *args, **kwargs):
        super(ThreatlistManagerMergeHandler, self).__init__(*args, **kwargs)
