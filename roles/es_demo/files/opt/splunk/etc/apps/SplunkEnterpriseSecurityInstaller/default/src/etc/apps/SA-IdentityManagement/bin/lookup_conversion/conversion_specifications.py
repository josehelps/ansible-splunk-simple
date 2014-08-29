'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import splunk
import sys

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))


from SolnCommon.models import SplunkIdentityLookupConf
from SolnCommon.lookup_conversion.conversion import LookupConversionSpec
from SolnCommon.lookup_conversion.fields import AssetIdFieldMapping
from SolnCommon.lookup_conversion.fields import AssetTagFieldMapping
from SolnCommon.lookup_conversion.fields import BooleanFieldMapping
from SolnCommon.lookup_conversion.fields import CategoryFieldMapping
from SolnCommon.lookup_conversion.fields import FieldMapping
from SolnCommon.lookup_conversion.fields import IdentityFieldMapping
from SolnCommon.lookup_conversion.fields import IdentityIdFieldMapping
from SolnCommon.lookup_conversion.fields import IdentityTagFieldMapping
from SolnCommon.lookup_conversion.fields import IpAddressFieldMapping
from SolnCommon.lookup_conversion.fields import KeyFieldMapping
from SolnCommon.lookup_conversion.fields import PciDomainFieldMapping


class IdentityManagerAssetConversionSpec(LookupConversionSpec):
    '''Class defining a specification used to convert a set of asset lists into 
    a static Splunk lookup table.'''

    def __init__(self, *args, **kwargs):
        '''Initialize the field mappings for an assets lookup conversion.

        Expected input fields in assets.csv are:
        
            ip, mac, nt_host, dns, owner, priority, lat, long, city, country,
            bunit, category, pci_domain, is_expected, should_timesync,
            should_update, requires_av
        
        Generated fields:
        
            asset_tag, asset_id, key
            
        '''

        fieldmap = {'key': KeyFieldMapping('key', is_generated=True),
            'asset_id': AssetIdFieldMapping('asset_id', requires=['dns', 'ip', 'mac', 'nt_host'], is_generated=True),
            'asset_tag': AssetTagFieldMapping('asset_tag', depends=['category', 'pci_domain', 'is_expected', 'should_timesync', 'should_update', 'requires_av', 'bunit'], is_generated=True),
            'bunit': FieldMapping('bunit'),
            'category': CategoryFieldMapping('category', is_tracked=True, delim="|"),
            'city': FieldMapping('city'),
            'country': FieldMapping('country'),
            'dns': FieldMapping('dns', is_key_field=True),
            'ip': IpAddressFieldMapping('ip', depends=['asset_id'], deferred_requires=['asset_id'], is_key_field=True),
            'is_expected': BooleanFieldMapping('is_expected'), 
            'lat': FieldMapping('lat'),
            'long': FieldMapping('long'),
            'mac': FieldMapping('mac', is_key_field=True),
            'nt_host': FieldMapping('nt_host', is_key_field=True),
            'owner': FieldMapping('owner'),
            'pci_domain': PciDomainFieldMapping('pci_domain', depends=['category'], is_tracked=True, delim="|"),
            'priority': FieldMapping('priority'),
            'should_timesync': BooleanFieldMapping('should_timesync'), 
            'should_update': BooleanFieldMapping('should_update'), 
            'requires_av': BooleanFieldMapping('requires_av')}
        
        super(IdentityManagerAssetConversionSpec, self).__init__(fieldmap, 
            allow_custom=True,
            allow_mv_keys=False,
            eliminate_duplicates=True)


class IdentityManagerIdentityConversionSpec(LookupConversionSpec):
    '''Class defining a specification used to convert a set of identity lists into 
    a static Splunk lookup table.

    Expected input fields in identities lookup tables are shown below.
    
    Legend:
    
        augmented: Field exists but is added to by `identities` macro
        populated: Field is populated by `identities` macro
        mv:        Field is multi-valued
    
    Expected fields:
    
        bunit
        category (populated, mv)
        email
        endDate
        first
        identity (mv)
        last
        managedBy
        nick
        phone
        phone2
        prefix
        priority
        startDate
        suffix
        watchlist (populated)

    Generated fields:

        identity_tag (populated, mv)
        key
    
    Key fields:
    
        Only the "identity" field, which is generated based on the
        identityLookup.conf configuration, is a key field. The contents 
        of this field will be a combination of:
        
        1) Any EXACT names specified in the "identity" column. The input
           value of this field is not ignored.
        2) The EMAIL address specified in the "email" column.
        3) The EMAIL_SHORT name derived from the "email" column.
        4) Any CONVENTIONS defined from a combination of the input fields.
        
        Since the conventions can specify ANY input field, the "identity"
        column necessarily depends on the values of all other fields.
        However, we exclude the following fields from
        this requirement since in cases where generating an identity from
        the source field would make no sense:
        
        - The source field is Boolean
        - The source field is multi-valued
        - The source field is a date, phone number, or other field not
          strictly part of the identity.
        - The source field is a generated field
        - The source field is the target field (circular dependency)
        
            Exclusions
            ==========
            category
            endDate
            identity
            identity_tag
            managedBy
            phone
            phone2
            priority
            startDate
            watchlist
    '''

    def __init__(self, *args, **kwargs):
        '''Initialize the field mappings for an assets lookup conversion.'''

        # Extra data is required for the IdentityField mapping. This is passed
        # in as the "custom_data" keyword argument, which is a catch-all for data 
        # not shared across the other Field specifications.

        custom_data = IdentityManagerIdentityConversionSpec._get_custom_data(
            namespace=kwargs.get('namespace'),
            owner=kwargs.get('owner'),
            session_key=kwargs.get('session_key'))
        
        fieldmap = {'key': KeyFieldMapping('key', is_generated=True),
            'bunit': FieldMapping('bunit'),
            'category': CategoryFieldMapping('category', is_tracked=True, delim="|"),
            'email': FieldMapping('email'),
            'endDate': FieldMapping('endDate'),
            'first': FieldMapping('first'),
            'identity': IdentityFieldMapping('identity', depends=['bunit', 'email', 'first', 'last', 'nick', 'prefix', 'suffix'], is_key_field=True, custom_data=custom_data, delim="|"),
            'identity_id': IdentityIdFieldMapping('identity_id', requires=['identity', 'first', 'last', 'email'], is_generated=True, is_persistent=True),
            'identity_tag': IdentityTagFieldMapping('identity_tag', depends=['bunit', 'category', 'watchlist'], is_generated=True),
            'last': FieldMapping('last'),
            'managedBy': FieldMapping('managedBy'),
            'nick': FieldMapping('nick'),
            'phone': FieldMapping('phone'),
            'phone2': FieldMapping('phone2'),
            'prefix': FieldMapping('prefix'),
            'priority': FieldMapping('priority'),
            'startDate': FieldMapping('startDate'),
            'suffix': FieldMapping('suffix'),
            'watchlist': BooleanFieldMapping('watchlist')}
        
        mv_key_fields = ['identity']

        super(IdentityManagerIdentityConversionSpec, self).__init__(fieldmap, 
            allow_custom=True, 
            eliminate_duplicates=True,
            mv_key_fields=mv_key_fields,
            custom_data=custom_data)

    @classmethod
    def _get_custom_data(cls, namespace, owner, session_key):
        # Read in the identity lookup configuration. If this cannot be done,
        # raise an error since we cannot proceed.
        try:
            return SplunkIdentityLookupConf.get(SplunkIdentityLookupConf.build_id('identityLookup', namespace, owner), session_key)
        except splunk.SplunkdConnectionException as e:
            raise e
        except splunk.ResourceNotFound as e:
            raise e
