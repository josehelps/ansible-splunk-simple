'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.lookup_conversion.conversion import LookupConversionSpec
from SolnCommon.lookup_conversion.fields import DomainFieldMapping
from SolnCommon.lookup_conversion.fields import FieldMapping
from SolnCommon.lookup_conversion.fields import LengthFieldMapping
from SolnCommon.lookup_conversion.fields import RegistrableLengthFieldMapping
from SolnCommon.lookup_conversion.fields import SimpleIpAddressFieldMapping
from SolnCommon.lookup_conversion.fields import KeyFieldMapping


class ThreatlistManagerAlexaConversionSpec(LookupConversionSpec):
    '''Class defining a specification used to convert a set of threat lists into 
    a static Splunk lookup table.'''
 
    def __init__(self, *args, **kwargs):
         
        fieldmap = {'rank': FieldMapping('description'),
                    'domain': FieldMapping('domain', is_key_field=True)}

        super(ThreatlistManagerAlexaConversionSpec, self).__init__(fieldmap,
            allow_custom=False,
            allow_mv_keys=False,
            merge_fields=[],
            mv_key_fields=[])


class ThreatlistManagerAsnConversionSpec(LookupConversionSpec):
    '''Class defining a specification used to convert a set of threat lists into 
    a static Splunk lookup table.'''
 
    def __init__(self, *args, **kwargs):
         
        fieldmap = {'description': FieldMapping('description'),
            'ip': SimpleIpAddressFieldMapping('ip', is_key_field=True, custom_data={'expand_subnet_size': 0})}

        super(ThreatlistManagerAsnConversionSpec, self).__init__(fieldmap,
            allow_custom=False,
            allow_mv_keys=False,
            merge_fields=[],
            mv_key_fields=[])


class ThreatlistManagerTldConversionSpec(LookupConversionSpec):
    '''Class defining a specification used to convert a set of threat lists into 
    a static Splunk lookup table.'''
 
    def __init__(self, *args, **kwargs):

        fieldmap = {'tld': DomainFieldMapping('tld', is_key_field=True)}

        super(ThreatlistManagerTldConversionSpec, self).__init__(fieldmap,
            allow_custom=False,
            allow_mv_keys=False,
            merge_fields=[],
            mv_key_fields=[])


class ThreatlistManagerMozilla_pslConversionSpec(LookupConversionSpec):
    '''Class defining a specification used to convert a set of threat lists into 
    a static Splunk lookup table.'''
 
    def __init__(self, *args, **kwargs):

        fieldmap = {'length': RegistrableLengthFieldMapping('length', requires=["rule", "domain"], delim=".", is_generated=True),
            'domain': DomainFieldMapping('domain', is_key_field=True),
            'segments': LengthFieldMapping('segments', requires=["domain"], delim=".", is_generated=True),
            }

        super(ThreatlistManagerMozilla_pslConversionSpec, self).__init__(fieldmap,
            allow_custom=False,
            allow_mv_keys=False,
            merge_fields=[],
            mv_key_fields=[])


class ThreatlistManagerThreatlistConversionSpec(LookupConversionSpec):
    '''Class defining a specification used to convert a set of threat lists into 
    a static Splunk lookup table.'''
 
    def __init__(self, *args, **kwargs):
         
        fieldmap = {'key': KeyFieldMapping('key', is_generated=True),
            'category': FieldMapping('category', is_tracked=True, delim="|", replace_null=''),
            'description': FieldMapping('description'),
            'ip': SimpleIpAddressFieldMapping('ip', is_key_field=True, custom_data={'expand_subnet_size': 24}, replace_null=''),
            'domain': FieldMapping('domain', is_key_field=True, replace_null=''),
            'url': FieldMapping('url', is_key_field=True, replace_null=''),
            'name': FieldMapping('name'),
            'risk': FieldMapping('risk', delim="|", replace_null=''),
            'type': FieldMapping('type')
            }

        super(ThreatlistManagerThreatlistConversionSpec, self).__init__(fieldmap,
            allow_custom=False,
            allow_mv_keys=False,
            merge_fields=[],
            mv_key_fields=['ip'])
