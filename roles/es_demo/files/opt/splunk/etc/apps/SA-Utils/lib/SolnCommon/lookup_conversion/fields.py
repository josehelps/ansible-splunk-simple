'''
Copyright (C) 2005-2012 Splunk Inc. All Rights Reserved.
'''
import abc
import codecs
import collections
import hashlib
import heapq
import logging
import re
import sys

import splunk
import splunk.util

from identity import Identity
from identity import IdentityLookup

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from ..error import LookupConversionErrors
from SolnCommon import ipMath
from SolnCommon.ipMath import IPType
from SolnCommon.modular_input import logger

# Constants for field deferral status.
# DEFERRED indicates that a line's processing must be deferred due to a particular
# field value; NOT_DEFERRED indicates that no deferral is necessary.
DEFERRED = True
NOT_DEFERRED = False

# Constants for default argument values.
DEFAULT_DEPENDENCIES = {}
DEFAULT_DEFERRED_DEPENDENCIES = {}
DEFAULT_REQUIREMENTS = {}


class AbstractFieldMapping(object):
    '''Abstract field mapping class.'''
    __metaclass__ = abc.ABCMeta
    
    # Read-only Properties
    @abc.abstractproperty
    def name(self): 
        pass

    @abc.abstractproperty
    def depends(self): 
        pass

    @abc.abstractproperty
    def requires(self):
        pass

    @abc.abstractproperty
    def deferred_requires(self):
        pass

    @abc.abstractproperty
    def delim(self):
        pass
    
    @abc.abstractproperty
    def is_key_field(self):
        pass

    @abc.abstractproperty
    def is_generated(self):
        pass

    @abc.abstractproperty
    def is_tracked(self):
        pass

    # Methods
    @abc.abstractmethod
    def validate(self):
        pass
    
    @abc.abstractmethod
    def convert(self):
        pass
    
    @abc.abstractmethod
    def convert_deferred(self):
        pass

    @abc.abstractmethod
    def postprocess(self):
        pass

    
class FieldMapping(AbstractFieldMapping):
    '''Generic class for handling field mappings.
       Named FieldMapping to avoid conflicts with splunk.models.Field.
       
       See the code for this class for more details on the meaning of each parameter. 
    '''

    def __init__(self,
        name,
        depends=DEFAULT_DEPENDENCIES,
        requires=DEFAULT_REQUIREMENTS,
        deferred_requires=DEFAULT_DEFERRED_DEPENDENCIES,
        is_generated=False,
        is_key_field=False,
        is_persistent=False,
        is_tracked=False,
        delim=None,
        replace_null=None,
        custom_data={}):
        '''Initialize a FieldMapping class.
       
       @param name: The output field name.
       @param dependencies: A list of this conversion's dependencies.
       @param requirements: A list of this conversions requirements.
       @param deferred_requirements: A list of this conversion's deferred requirements.
       @param is_key_field: True if this value is a key field in the generated lookup table.
       @param is_generated: True if this field is generated (i.e., not present in the input file).
       @param is_tracked: True if this field should keep track of its values.
       @param delim: A delimiter for handling multi-valued input fields.
       @param replace_null: A replacement string for handling missing input values.
       '''

        ### Positional parameters ###
        self._name = name
        self._depends = depends
        self._requires = requires
        self._deferred_requires = deferred_requires
        
        ### Keyword parameters ###
        self._delim = delim
        self._is_generated = is_generated
        self._is_key_field = is_key_field
        self._is_persistent = is_persistent
        self._is_tracked = is_tracked
        self._replace_null = replace_null
        self._custom_data = custom_data

        # Internal state.        
        self._all_values = set()    # Tracks all values of the field.

    ### Properties ###
    @property
    def name(self):
        return self._name
    
    @property
    def depends(self):
        return self._depends
    
    @property
    def requires(self):
        return self._requires
    
    @property
    def deferred_requires(self):
        return self._deferred_requires

    @property
    def delim(self):
        return self._delim
    
    @property
    def is_generated(self):
        return self._is_generated
    
    @property
    def is_key_field(self):
        return self._is_key_field

    @property
    def is_persistent(self):
        return self._is_persistent

    @property
    def is_tracked(self):
        return self._is_tracked
    
    @property
    def replace_null(self):
        return self._replace_null

    @property
    def custom_data(self):
        return self._custom_data

    ### Validation actions
    def validate(self, value, *args, **kwargs):
        '''Validate that the input value of the field is correct.
        If an input field does not validate, the entire input line is 
        rejected. Default validation is to pass the field along unchanged,
        since all input fields from a csv.DictReader will be instances
        of basestring.
        
        Generated fields always validate since they do not actually exist.
        Generated fields should set self._is_generated=True in their
        Field specification since the value passed in for a field that does
        not exist in the original CSV file will be None.
        ''' 
        if isinstance(value, basestring) or (value is None and self.is_generated) or isinstance(self.replace_null, basestring):
            return True
        return False

    ### Preprocessing actions
    def preprocess(self, value, *args, **kwargs):
        # Note: Only the initial values of fields can be tracked, not their 
        # converted values.
        if self.is_tracked and value:
            if self.delim and isinstance(value, basestring):
                self._all_values.update(value.split(self.delim))
            else:
                self._all_values.add(value)

    ### Conversion actions
    def convert(self, value, dependencies, requirements, record_num):
        '''The default action is to return the string unchanged.
        Return value from any convert() function is expected to be
        a tuple consisting of:

            (val, deferred_status)

        where:
        
            val             = output value (possibly a list)
            deferred_status = Boolean indicating whether this field's
                              value forces the line to undergo deferred
                              processing.

        Deferred fields will cause the source line to be placed into
        a separate queue for processing. ONLY fields that actually 
        require deferred processing will be processed during the 
        deferred processing pass; the remainder of the line is not processed
        again.
        
        Generated fields MUST implement a convert() method of their own,
        to avoid raising AttributeError here. Only pure strings can be
        converted using the base FieldMapping class.
        '''
        if value is None and self.replace_null is not None:
            return (self.replace_null, NOT_DEFERRED)
        else:
            return (value.strip(), NOT_DEFERRED)

    def convert_deferred(self, *args, **kwargs):
        '''Conduct deferred field processing taking into account any saved 
        state accumulated by the class. Default behavior is to do nothing and return
        the value
        '''
        pass

    def postprocess(self, *args, **kwargs):
        '''Conduct postprocessing for any saved state accumulated by the 
        class. Default behavior is to do nothing and return nothing. This function
        does not return a value.
        '''
        if self.is_tracked:
            return self._all_values
        return None


class AssetIdFieldMapping(FieldMapping):
    
    def convert(self, value, dependencies, requirements, record_num):
        '''Concatenate ip/mac/nt_host/dns to form an asset_id.
        Zero-length string will evaluate to false.
        
        The asset_id field refers to the value in the ORIGINAL lookup
        table, not the converted one. This allows us to correlate
        the asset with a specific line in the original user file,
        even though a single range might expand to many lines
        in the expanded lookup file.
        
        Generates the same asset_id as assetLookup.py. Order is
        important to maintain continuity with the previous assetLookup.py
        implementation.
        
        Any incoming value is ignored.
        '''
        
        asset_id = ''.join([requirements.get(i, '') for i in ['ip', 'mac', 'nt_host', 'dns']])

        # Zero-length string will evaluate to false
        return (hashlib.sha1(asset_id).hexdigest() if asset_id else '', NOT_DEFERRED)


class AssetTagFieldMapping(FieldMapping):

    def convert(self, value, dependencies, requirements, record_num):
        '''Return the asset tag for the host.'''
        
        # Incoming value is actually ignored for asset_tag as it is a generated field.
        
        # Retrieve dependencies
        bunit = dependencies.get('bunit', [])
        categories = dependencies.get('category', [])

        asset_tag = set()
        
        for bField in ['should_timesync', 'should_update', 'requires_av']:
            try:
                if splunk.util.normalizeBoolean(dependencies.get(bField, False)):
                    asset_tag.add(bField)
            except ValueError:
                # Catch exception in case the assets.csv entry cannot be
                # interpreted as a Boolean.
                pass
       
        # Make sure to add multiple categories if they exist.
        if isinstance(categories, list):
            for category in categories:
                asset_tag.add(category)
        else:
            asset_tag.add(categories)
              
        try:
            if splunk.util.normalizeBoolean(dependencies.get('is_expected', False)):
                asset_tag.add('expected')
        except ValueError:
            # Catch exception in case the assets.csv entry cannot be
            # interpreted as a Boolean.
            pass
            
        # Business unit is single-valued        
        asset_tag.add(bunit)

        # Discard empty entries.
        asset_tag.discard('')

        # Return multi-valued output IFF there is only more than one item.
        if len(asset_tag) == 0:
            return ('', NOT_DEFERRED)
        elif len(asset_tag) == 1:
            return (asset_tag.pop(), NOT_DEFERRED)
        else:
            return (list(asset_tag), NOT_DEFERRED)


class BooleanFieldMapping(FieldMapping):
    
    # Separate validation is not required here since this function is 
    # guaranteed to return a boolean value.
    
    def convert(self, value, dependencies, requirements, record_num):
        '''Return a Boolean "true" or "false" if the input field can
        be appropriately converted.
        '''
        
        try:
            if splunk.util.normalizeBoolean(value, enableStrictMode=True, includeIntegers=True):
                return ('true', NOT_DEFERRED)
        except ValueError:
            pass
        return ('false', NOT_DEFERRED)


class CategoryFieldMapping(FieldMapping):

    def convert(self, value, dependencies, requirements, record_num):
        '''Return a list of categories, given an input pipe-separated string
        of categories, conducting the following transformations:
        
        1. If category == cardholder, add category=pci
        
        Also maintain a list of categories for output to ancillary lookup file.
        The ancillary lookup file will be output during the postprocess() action.
        
        '''
        
        categories = set(value.split(self.delim))

        if 'cardholder' in categories:
            categories.add('pci')

        # Discard empty entries.
        categories.discard('')

        # Update the set of all categories.
        self._all_values.update(categories)

        # Return multi-valued IFF there is only more than one item.
        if len(categories) == 0:
            return ('', NOT_DEFERRED)
        if len(categories) == 1:
            return (categories.pop(), NOT_DEFERRED)
        else:
            return (list(categories), NOT_DEFERRED)


class DomainFieldMapping(FieldMapping):
    
    def convert(self, value, dependencies, requirements, record_num):
        '''Convert a domain name, returning both the RFC 3490-encoded form and 
        the Unicode form if applicable.
        '''

        orig = value.strip().lower()
        values = set([orig])
        try:
            values.add(codecs.decode(orig, 'idna'))
        except UnicodeDecodeError:
            pass
        try:
            values.add(codecs.encode(splunk.util.objUnicode(orig), 'idna'))
        except UnicodeDecodeError:
            pass

        if len(values) == 1:
            return (orig, NOT_DEFERRED)
        else:
            return(list(values), NOT_DEFERRED)


class IdentityFieldMapping(FieldMapping):

    def __init__(self, *args, **kwargs):
        '''Set up the order in which identity lookups will be processed.
        
        The default order, in case there is an error in retrieving the
        identityLookup.conf configuration, mimics the previous behavior
        of identityLookup.py:
        
        identity (exact match), email, email_short, convention
        '''

        # Custom data specification.
        #
        # The configuration object stored in self._custom_data is a 
        # util.SplunkIdentityLookupConf object and will have these fields:
        #
        #    case_sensitive (Boolean)
        #    convention (Boolean)
        #    conventions (List)
        #    email (Boolean)
        #    email_short (Boolean)
        #    exact (Boolean)
        #    match_order (List)
        #
        # The case_sensitive value is unused here - case sensitivity must
        # be specified in the lookup definition.

        # Regular expression for extracting e-mail addresses
        self._email_rx = re.compile(Identity.emailREpattern)
        
        # Build the regex for string replacements from the defined conventions,
        # based on the set of valid field names in the input CSV that can
        # be used for replacements (this is equivalent to the "dependencies" at
        # this point. To use ALL fields including custom fields, we would need to
        # extrapolate this to accept an ancillary value in __init__, and make the
        # identity field depend on the final values of ALL other fields including
        # custom fields).
        self._conventionValRE = self.buildReplacementConventions(kwargs.get('depends', []))
        
        super(IdentityFieldMapping, self).__init__(*args, **kwargs)

    def buildReplacementConventions(self, fields):
        '''Build a regular expression that will match all field names in the
        current identities.csv file.'''
        
        rx = []
        for field in fields:
            rx.append('{0}'.format(field))
        rx = '(' + '|'.join(rx) + ')\((\d+)?\)'

        return re.compile(rx)
        
    def convert(self, value, dependencies, requirements, record_num):
        '''Return a set of identities for the given input.'''
        
        # Create the output dictionary
        identities = {}

        # Retrieve the current field value and split into identities.
        # These are used for exact matching.
        if self.custom_data.exact:
            identities[IdentityLookup.PARAM_EXACT] = [i.strip() for i in value.split(self._delim) if i != '']
        
        if self.custom_data.email:
            # Retrieve dependencies
            email = dependencies.get('email', None)
            # Get the email address and short e-mail address
            if email is not None and email != '':
                identities[IdentityLookup.PARAM_EMAIL] = [email]
                if self.custom_data.email_short:
                    rx = self._email_rx.match(email)
                    if rx:
                        identities[IdentityLookup.PARAM_EMAIL_SHORT] = [rx.group(1)]
                
        # Format the identities based on any conventions derived from
        # identityLookup.conf.
        #
        # A convention is a string composed of <field>(<len>).<field>(<len>)
        # indicating that the <field> should be replaced with <len> 
        # characters from the actual field value.
        #
        # Per SOLNESS-3406, non-field name portions of the string
        # are also permitted in the convention. For instance:
        #
        #    first(1)last().admin
        #
        # would represent a naming scheme for administrative Kerberos principals.
        if self.custom_data.convention:
            for conventionStr in self.custom_data.conventions:

                # Get the convention string, which should be a text string
                # containing replacement parameters in the form
                # <field>(<chars>). These portions of the string will be
                # replaced directly with the corresponding field and character
                # count. If the field does not exist in the input, the empty
                # string will be used as a replacement.
                #
                # We improve on the previous handling of convention matching
                # by eliminating two cases from the output:
                # 1. Cases where zero successful field replacements could be
                #    performed. For instance, if no successful field replacements
                #    could be made, the convention string "first(1).last" could
                #    result in an identity value of ".", which is wrong.
                #
                # 2. Cases where the replacement string included only empty
                #    replacements.
                matchCount = 0
                nonEmptyMatchCount = 0
                 
                conventionValMatch = self._conventionValRE.finditer(conventionStr)

                # identityStr is the final value that we will return.
                identityStr = conventionStr
                for valMatch in conventionValMatch:
                    fieldValue = dependencies.get(valMatch.group(1), False)
                    if fieldValue and fieldValue != '':
                        matchCount += 1
                        if valMatch.group(2) is None or len(valMatch.group(2)) == 0:
                            # Convention specified no replacement character length,
                            # indicating to replace with the full string.
                            strLength = len(fieldValue)                                
                        else:
                            # Replacement character length is not empty, 
                            # indicating to replace with a substring.
                            strLength = int(valMatch.group(2))
    
                        # Get the replacement value.
                        replacementValue = fieldValue[:strLength]
                        
                        # If the replacement value is not empty, increment
                        # the count of non-empty matches.
                        if len(replacementValue) > 0:
                            nonEmptyMatchCount += 1
                        identityStr = identityStr.replace(valMatch.group(0), replacementValue)

                    else:
                        # A field value was not supplied in the input data.
                        # Replace it with a blank in the output string.
                        identityStr = identityStr.replace(valMatch.group(0), '')
    
                # Output the identity IFF more than one non-empty match was made.
                if matchCount > 0 and nonEmptyMatchCount > 0:
                    curr = identities.setdefault(IdentityLookup.PARAM_CONVENTION, [])                                                                                                                                                       
                    curr.append(identityStr)
                else:
                    # Do not add the identity.
                    pass
                      
        # Output the identity values in order based on the configuration.
        # This order will be used to output the CSV files, so that the first
        # match is successful.
        # To deduplicate entries, we use an OrderedDict to maintain the match order,
        # but also deduplicate identity keys while respecting case.
        output = collections.OrderedDict()
        for item in self.custom_data.match_order:
            for representation in identities.get(item, []):
                if self.custom_data.case_sensitive:
                    output[representation] = None
                else:
                    output[representation.lower()] = None
            
        return (output.keys(), NOT_DEFERRED)


class IdentityIdFieldMapping(FieldMapping):
    
    def convert(self, value, dependencies, requirements, record_num):
        '''Concatenate fields to form an identity ID.
        Zero-length string will evaluate to false.
        
        The ID field refers to the value in the ORIGINAL lookup
        table, not the converted one. This allows us to correlate
        the generated line with a specific line in the original input file.
                
        Any incoming value is ignored.
        '''
        
        ident_id = ''.join([requirements.get(i, '') for i in ['identity', 'first', 'last', 'email']])

        # Zero-length string will evaluate to false
        return (hashlib.sha1(ident_id).hexdigest() if ident_id else '', NOT_DEFERRED)


class IdentityTagFieldMapping(FieldMapping):

    def convert(self, value, dependencies, requirements, record_num):
        '''Return the identity_tag for the host.'''
        
        # Incoming value is actually ignored for identity_tag as it is a generated field.
        
        # Retrieve dependencies
        bunit = dependencies.get('bunit', [])
        categories = dependencies.get('category', [])
        watchlist = dependencies.get('watchlist', False)

        tag = set()
        
        # Make sure to add multiple categories if they exist.
        if isinstance(categories, list):
            for category in categories:
                tag.add(category)
        else:
            tag.add(categories)
              
        try:
            if splunk.util.normalizeBoolean(watchlist, False):
                tag.add('watchlist')
        except ValueError:
            # Catch exception in case the CSV entry cannot be
            # interpreted as a Boolean.
            pass
            
        # Business unit is single-valued        
        tag.add(bunit)

        # Discard empty entries.
        tag.discard('')

        # Return multi-valued output IFF there is only more than one item.
        if len(tag) == 0:
            return ('', NOT_DEFERRED)
        elif len(tag) == 1:
            return (tag.pop(), NOT_DEFERRED)
        else:
            return (list(tag), NOT_DEFERRED)
        
        
class IpAddressFieldMapping(FieldMapping):

    def __init__(self, *args, **kwargs):
        FieldMapping.__init__(self, *args, **kwargs)

        # Define heap of IP ranges as tuples of long integers:
        #
        #    (range_low, range_high).
        #
        # The heap is used to split IP ranges when smaller ranges (including
        # single addresses) are specified elsewhere in the lookup table.
        # In the case of a duplication or overlap, the entry with the "lowest" 
        # priority and asset_id will win. Priority is used so that assets 
        # specified as single IP addresses in the original table will always 
        # win out over ranges or subnets, and ranges or subnets defined
        # in the original asset table will win out over ranges derived by 
        # calculation. 
        self._ranges = []

    def _split_ip_ranges(self):
        '''Given a heap of tuples:
                (range_low, range_high, key)
        split the numeric ranges so that there are no overlapping
        ranges. For instance, given:
        
                (100, 101, <priority>, a)
                (100, 105, <priority>, b)
                (106, 110, <priority>, c)
        return:
                (100, 101, <priority>, [a,b])
                (102, 105, <priority>, b)
                (106, 110, <priority>, c)

        Ambiguous overlaps result in the second range being discarded.
        This can be used to sort lists of subnets in (range_low, range_high)
        format when the bounding IPs are expressed as long integers.
        This function takes advantage of Python's heapq, which
        can accept tuples and sort them properly based on all values
        in the tuple.
        
        There are some extraneous heappush() and heappop() calls here; it 
        would be possible to construct an equivalent function that
        always retained the lowest range in rangeA.
        '''
        
        overlap_warning = "Range overlap: rangeA_rows={0} rangeB_rows={1} rangeA={2}-{3} rangeB={4}-{5}"
        duplicate_warning = "Range duplicated: rangeA_rows={0} rangeB_rows={1} rangeA={2}-{3} rangeB={4}-{5}"
    
        output = []
        if len(self._ranges) > 0:
            while len(self._ranges) > 1:
                rangeA_low, rangeA_high, rangeA_priority, rangeA_rows = heapq.heappop(self._ranges)
                rangeB_low, rangeB_high, rangeB_priority, rangeB_rows = heapq.heappop(self._ranges)
                if not isinstance(rangeA_rows, list):
                    rangeA_rows = [rangeA_rows]
                if not isinstance(rangeB_rows, list):
                    rangeB_rows = [rangeB_rows]
                if rangeA_low < rangeB_low:
                    if rangeA_high < rangeB_high:
                        if rangeA_high < rangeB_low:
                            # Ranges do not overlap.
                            # 1. Push rangeA to output.
                            # 2. Push rangeB back onto heap, as it may overlap
                            #    with the next range.
                            output.append((rangeA_low, rangeA_high, rangeA_priority, rangeA_rows))
                            heapq.heappush(self._ranges, (rangeB_low, rangeB_high, rangeB_priority, rangeB_rows))
                        else:
                            # Range overlap.
                            # 1. Split BOTH ranges into range A', range C, range B'.
                            # 2. Add rows from both rangeA and rangeB to rangeC      
                            # 3. Add all three ranges back to heap, increasing priority.
                            rangeC_low, rangeC_high = rangeB_low, rangeA_high
                            rangeA_high = rangeB_low - 1
                            rangeB_low = rangeA_high + 1
                            rangeC_rows = rangeA_rows + rangeB_rows
                            # TODO: How best to calculate rangeC priority?
                            rangeC_priority = rangeA_priority
                            logger.debug(overlap_warning.format(rangeA_rows, rangeB_rows, ipMath.LongToIP(rangeA_low), ipMath.LongToIP(rangeA_high), ipMath.LongToIP(rangeB_low), ipMath.LongToIP(rangeB_high)))
                            heapq.heappush(self._ranges, (rangeA_low, rangeA_high, rangeA_priority + 1, rangeA_rows))
                            heapq.heappush(self._ranges, (rangeC_low, rangeC_high, rangeC_priority + 1, rangeC_rows))
                            heapq.heappush(self._ranges, (rangeB_low, rangeB_high, rangeB_priority + 1, rangeB_rows))
                    elif rangeA_high == rangeB_high:
                        # rangeA subsumes rangeB "on left".
                        # 1. Split rangeA into rangeA', rangeB and increase priority of A'.
                        # 2. Push rangeA to output (this is guaranteed to be OK
                        #    since rangeA_low < rangeB_low)
                        # 3. Add rangeA rows to rangeB
                        # 4. Return rangeB to heap.
                        # 5. Continue
                        rangeA_high = rangeB_low - 1
                        output.append((rangeA_low, rangeA_high, rangeA_priority + 1, rangeA_rows))
                        rangeB_rows.extend(rangeA_rows)
                        heapq.heappush(self._ranges, (rangeB_low, rangeB_high, rangeB_priority, rangeB_rows))
                    elif rangeA_high > rangeB_high:
                        # rangeA subsumes rangeB on both sides.
                        # 1. Split rangeA into rangeA', rangeB, rangeA'' and increase priority of A' and A''.
                        # 2. Push rangeA' to output (this is guaranteed to be OK
                        #    since rangeA_low < rangeB_low)
                        # 3. Add rangeA rows to rangeB
                        # 4. Return rangeB, rangeA'' to heap.
                        # 5. Continue.
                        rangeAprime_high = rangeA_high
                        rangeAprime_low = rangeB_high + 1
                        rangeA_high = rangeB_low - 1
                        output.append((rangeA_low, rangeA_high, rangeA_priority + 1, rangeA_rows))
                        rangeB_rows.extend(rangeA_rows)
                        heapq.heappush(self._ranges, (rangeAprime_low, rangeAprime_high, rangeA_priority + 1, rangeA_rows))
                        heapq.heappush(self._ranges, (rangeB_low, rangeB_high, rangeB_priority, rangeB_rows))
                    else:
                        # This should never happen due to heap ordering.
                        raise ValueError('Range ordering was invalid... aborting lookup generation.')
                elif rangeA_low == rangeB_low:
                    if rangeA_high == rangeB_high:
                        # Exact duplicate.
                        # 1. Add rangeB rows to rangeA
                        # 2. Discard rangeB.
                        # 3. Continue.
                        logger.debug(overlap_warning.format(rangeA_rows, rangeB_rows, ipMath.LongToIP(rangeA_low), ipMath.LongToIP(rangeA_high), ipMath.LongToIP(rangeB_low), ipMath.LongToIP(rangeB_high)))
                        rangeA_rows.extend(rangeB_rows)
                        heapq.heappush(self._ranges, (rangeA_low, rangeA_high, rangeA_priority, rangeA_rows))
                    elif rangeA_high < rangeB_high:
                        # rangeB subsumes rangeA "on right".
                        # 1. Split rangeB into rangeA, rangeB' and increase priority of B'.
                        # 2. Add rangeB rows to rangeA
                        # 3. Push both ranges back to heap.
                        # 4. Continue.
                        rangeB_low = rangeA_high + 1
                        rangeA_rows.extend(rangeB_rows)
                        heapq.heappush(self._ranges, (rangeA_low, rangeA_high, rangeA_priority, rangeA_rows))
                        heapq.heappush(self._ranges, (rangeB_low, rangeB_high, rangeB_priority + 1, rangeB_rows))
                    else:
                        # This is the rangeA_high > rangeB_high case: this should never happen.
                        # due to heap ordering.
                        raise ValueError('Range ordering invalid... aborting lookup generation.')
    
        # Append final range if one is present.
        if len(self._ranges) > 0:
            output.append(heapq.heappop(self._ranges))
        return output
   
    def convert(self, value, dependencies, requirements, record_num):
        '''Convert an input IP address value to a CIDR value compatible
        with a Splunk lookup table.
        
        Three possibilities:
        1. The value is a range. Processing will be deferred so that the
           range can be split into CIDR subnets and checked for overlaps
           with other entries. Ranges can be specified as <str>-<str> or
           <int>-<int>.
        2. The value is an IP. Output it directly, but add the address to
           the list of all IP ranges to avoid overlap. Thus, a specific single
           IP entry in the input CSV takes precedence over a range.
        3. The value is a CIDR address. If it is an IP in <address>/32 form, 
           treat as in step 2. Otherwise, treat as in step 1.
        4. The entry is blank. Ignore it.
        5. The entry is invalid in some other way. Return the original value.
           This should not happen due to input validation but is accounted for
           in this code for safety.
        '''

        # Remove leading and trailing whitespace.        
        value = value.strip()
        
        # Use lineno if a different sorting order is not implied by dependencies.
        # TODO: handle asset_id renaming to row_id in dependencies array.
        # TODO: specify sorting order.
        row_id = record_num
        if dependencies:
            row_id = dependencies.get('row_id', record_num)

        if '-' in value:            
            # The value is an IP range or an IP range expressed as two integers. 
            # 1. Split into tuple and validate.
            #    a. If valid, push range onto heap.
            #    b. If NOT valid, short-circuit and return original value
            #       (this should actually never happen due to validate() method).
            # 2. Return the range as (range_low, range_high) tuple and defer processing.
            range_low, range_high = value.split('-', 1)
            if ipMath.is_valid_ip(range_low) and ipMath.is_valid_ip(range_high):
                range_low = ipMath.IPToLong(range_low)
                range_high = ipMath.IPToLong(range_high)
                heapq.heappush(self._ranges, (range_low, range_high, 1, row_id))
                return ((range_low, range_high), DEFERRED)
            else:
                sys.stdout.write(LookupConversionErrors.ERR_INVALID_IP_RANGE + ': %s\n' % value)
                return (value, NOT_DEFERRED)

        elif ipMath.is_valid_ip(value):
            # This is a VALID IP ADDRESS.
            # 1. Add to the heap of IPs in /32 syntax.
            # 2. Return the value unchanged, do not conduct deferred processing
            #    (duplicate elimination is handled in converters.py::_format_output).
            ipLong = ipMath.IPToLong(value)
            heapq.heappush(self._ranges, (ipLong, ipLong, 0, row_id))
            return (value, NOT_DEFERRED)

        elif ipMath.is_valid_cidr(value):
            # This is a VALID CIDR specifier.
            # 1. If it ends in /32, convert and treat as normal IP.
            # 2. If it is a subnet, convert to range and add to range heap
            #    in (range_low, range_high) format, and defer processing.
            range_low, range_high = ipMath.CIDRToLongTuple(value)
            if range_low == range_high:
                heapq.heappush(self._ranges, (range_low, range_low, 0, row_id))
                return (value.replace('/32', ''), NOT_DEFERRED)
            else:
                heapq.heappush(self._ranges, (range_low, range_high, 1, row_id))
                return ((range_low, range_high), DEFERRED)

        elif value == '':
            # This is a BLANK value. Ignore it.
            return (value, NOT_DEFERRED)
        else:
            # This is an INVALID value. Return it, but log the event.
            logger.error(LookupConversionErrors.formatErr(LookupConversionErrors.ERR_INVALID_IP_OR_CIDR, value))
            return (value, NOT_DEFERRED)

    def postprocess(self):
        '''Conduct postprocessing.
        1. Break the collected IP ranges into non-overlapping ranges.
        2. Create directory keying the ranges by asset_id so we can easily
           process the deferred lines in convert_deferred().
        '''
        self._ranges_by_row_ids = {}

        ## Debugging code only.
        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug("=====RANGES BEFORE SPLIT=====")
            for low, high, priority, row_ids in self._ranges:
                logger.debug(str((ipMath.LongToIP(low), ipMath.LongToIP(high), priority, row_ids)))
        ## End debugging code.

        self._ranges = self._split_ip_ranges()

        # Generate [row_id] -> [ranges] dictionary
        for low, high, priority, row_ids in self._ranges:
            #print 'LOW: {} HIGH: {} PRIORITY: {} ROW_IDS: {}'.format(low, high, priority, row_ids)
            if isinstance(row_ids, list):
                for row_id in row_ids:
                    tmp = self._ranges_by_row_ids.setdefault(row_id, [])
                    tmp.append((low, high))
            else:
                # Only received one asset as input.
                tmp = self._ranges_by_row_ids.setdefault(row_ids, [])
                tmp.append((low, high))

        ## Debugging code only.
        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug("=====RANGES AFTER SPLIT=====")
            for low, high, priority, row_ids in self._ranges:
                logger.debug(str((ipMath.LongToIP(low), ipMath.LongToIP(high), priority, row_ids)))
            logger.debug("=====RANGES AFTER SPLIT BY ASSET ID=====")
            for key, value in self._ranges_by_row_ids.iteritems():
                logger.debug('%s' % key)
                for theRange in value:
                    low, high = theRange
                    logger.debug('  %s - %s' % (ipMath.LongToIP(low), ipMath.LongToIP(high)))
        ## End debugging code.

        # Clear self._ranges for a subsequent run. This is required if the script
        # runs persistently, otherwise duplicates will accumulate.
        self._ranges = []
        return

    def convert_deferred(self, value, deferred_requirements, record_num):
        '''Perform deferred conversion of any IP ranges to 
        CIDR subnets prior to writing the output lookup table.
        
        Note that the input value is ignored here, since the 
        converted IP address range has already been determined
        in postprocessing and can be determined solely from the 
        asset_id value.
        '''
        
        # If a field mapping defines a different container for the "row_id" we 
        # need to retrieve if can be used via the following idiom.
        #
        # if deferred_requirements:
        #     record_num = deferred_requirements.get('row_id', record_num)
        
        # Retrieve the ranges that are associated with the original row that
        # created this record.
        ranges = self._ranges_by_row_ids.get(record_num, None)

        cidr_list = []
        if ranges:
            [cidr_list.extend(ipMath.expand_ip_range_to_cidr(i, clean_single_ips=True, expand_subnets_smaller_than=24)) for i in ranges]
        else:
            logger.warning(LookupConversionErrors.formatErr(LookupConversionErrors.ERR_RANGES_NOT_FOUND, record_num))
        return cidr_list
    
    def validate(self, value):
        # Simple validation that the value is a string of length less than the
        # maximum of an IPv6 address. IPv4 addresses in single IP/CIDR form
        # will be validated later; non-IPv4 values are passed naively to the
        # output lookup table.
        return isinstance(value, basestring) and len(value) < 40


class LengthFieldMapping(FieldMapping):
    
    def __init__(self, *args, **kwargs):
        
        FieldMapping.__init__(self, *args, **kwargs)
        self._delim = self.custom_data.get('delim', '.')

    def convert(self, value, dependencies, requirements, record_num):
        '''Return the length of one other field.'''
        if len(requirements) == 1:
            key, value = requirements.popitem()
            return (len(value.split(self._delim)), NOT_DEFERRED)
        else:
            return (None, NOT_DEFERRED)


class RegistrableLengthFieldMapping(FieldMapping):

    def __init__(self, *args, **kwargs):
        
        FieldMapping.__init__(self, *args, **kwargs)
        self._delim = self.custom_data.get('delim', '.')

    def convert(self, value, dependencies, requirements, record_num):
        try:
            rule = requirements['rule']
            segments = len(requirements['domain'].split(self._delim))
        except KeyError:
            return ('', NOT_DEFERRED)
        if rule == '*':
            return (segments + 2, NOT_DEFERRED)
        elif rule == '!':
            return (segments, NOT_DEFERRED)
        else:
            return (segments + 1, NOT_DEFERRED)
            

class SimpleIpAddressFieldMapping(FieldMapping):

    def __init__(self, *args, **kwargs):
        
        FieldMapping.__init__(self, *args, **kwargs)
        self._expand_subnet_size = self.custom_data.get('expand_subnet_size', 24)

    def convert(self, value, dependencies, requirements, record_num):
        '''Convert an input IP address value to a CIDR value compatible
        with a Splunk lookup table.

        @param value: An IP address or range in string form. 
        
        Several possibilities, not necessarily in order of frequency:
        1. The value is a range where start == end. Convert it to a single IP.
        2. The value is a range where start < end. Convert it to a minimal CIDR
           address set.
        3. The value is an IP. Output it directly.
        4. The value is a CIDR address. If it is an IP in <address>/32 form, 
           treat as in step 1. Otherwise, validate and return it.
        5. The entry is blank. Ignore it.
        6. The entry is invalid in some other way. Return the original value.
           This should not happen due to input validation but is accounted for
           in this code for safety.
        '''

        if value is None and self.replace_null is not None:
            return (self.replace_null, NOT_DEFERRED)

        ip_repr, ip_type = IPType.get(value.strip())

        if ip_type == IPType.IPV4:
            # This is a VALID IP ADDRESS.
            return (ip_repr, NOT_DEFERRED)
        elif ip_type == IPType.IPV4_RANGE:
            return (ipMath.expand_ip_range_to_cidr(ip_repr, clean_single_ips=True, expand_subnets_smaller_than=self._expand_subnet_size), NOT_DEFERRED)
        elif ip_type == IPType.IP_INVALID:
            logger.error(LookupConversionErrors.formatErr(LookupConversionErrors.ERR_INVALID_IP_OR_CIDR, value))
            return (value, NOT_DEFERRED)

    def validate(self, value):
        if value == "":
            return True
        else:
            return isinstance(self.replace_null, basestring) or IPType.validate(value)


class KeyFieldMapping(FieldMapping):
    
    def convert(self, value, dependencies, requirements, record_num):
        '''Always return an empty string during conversion. The key field is
        only written to during output lookup table generation.
        '''
        return ("", NOT_DEFERRED)
    
    def validate(self, *args, **kwargs):
        '''Always validate any input data for this field; the input value
        will be discarded.'''
        return True


class PciDomainFieldMapping(FieldMapping):
    
    def __init__(self, *args, **kwargs):
        '''Maintain a list of all PCI domains for output to ancillary
        lookup table.
        '''
        FieldMapping.__init__(self, *args, **kwargs)
    
    def convert(self, value, dependencies, requirements, record_num):
        '''Return a list of PCI domains, given an input value conssting of a
        pipe-separated string of PCI domains, conducting the following
        transformations in the order shown:
        
        1. If category == "pci", add "trust" to pci_domain
        2. If pci_domain in ["wireless", "dmz"], add "trust" to pci_domain
        3. If category == "cardholder", add "trust" and "cardholder" to pci_domain
        4. If pci_domain is empty, return "untrust".
        '''
        
        # Retrieve dependencies
        categories = dependencies.get('category', [])
        
        domains = set(value.split(self.delim))
            
        if 'wireless' in domains or 'dmz' in domains:
            domains.add('trust')

        if 'pci' in categories:
            domains.add('trust')
            
        if 'cardholder' in categories:
            domains.update(['trust', 'cardholder'])

        # Discard empty entries.
        domains.discard('')
        
        # Update list of all PCI domains
        self._all_values.update(domains)
        
        # Return multi-valued IFF there is only more than one item.
        if len(domains) == 0:
            return ('untrust', NOT_DEFERRED)
        elif len(domains) == 1:
            return (domains.pop(), NOT_DEFERRED)
        else:
            return (list(domains), NOT_DEFERRED)
