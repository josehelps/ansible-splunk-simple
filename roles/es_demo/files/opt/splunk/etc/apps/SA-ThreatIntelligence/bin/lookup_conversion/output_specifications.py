'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.lookup_conversion.output import LookupOutputSpec


class ThreatlistManagerAlexaOutputSpec(LookupOutputSpec):
    def __init__(self, namespace, owner):
        super(ThreatlistManagerAlexaOutputSpec, self).__init__(
            ancillary_lookups={},
            output_lookups={'domain': ('alexa_lookup_by_str', namespace, owner)},
            routing={})


class ThreatlistManagerAsnOutputSpec(LookupOutputSpec):
    def __init__(self, namespace, owner):
        super(ThreatlistManagerAsnOutputSpec, self).__init__(
            ancillary_lookups={},
            output_lookups={'cidr': ('asn_lookup_by_cidr', namespace, owner),
                            'ip': ('asn_lookup_by_str', namespace, owner)},
            routing={'ip': {'cidr': lambda x: '/' in x}})


class ThreatlistManagerMozilla_pslOutputSpec(LookupOutputSpec):
    def __init__(self, namespace, owner):
        super(ThreatlistManagerMozilla_pslOutputSpec, self).__init__(
            ancillary_lookups={},
            output_lookups={'domain': ('mozilla_public_suffix_lookup', namespace, owner)},
            routing={})


class ThreatlistManagerThreatlistOutputSpec(LookupOutputSpec):
    '''Class defining how threat list information will be routed to Splunk lookups.'''

    def __init__(self, namespace, owner):
        '''Initialize the specification.
        
        @param namespace: The app for all output lookup tables. Currently we do
            not support output to multiple apps.
        @param owner: The Splunk user to be used when creating lookup tables. In
            nearly all cases this will be "nobody" since lookup tables are shared.
        '''

        super(ThreatlistManagerThreatlistOutputSpec, self).__init__(
            ancillary_lookups={'category': ('threatlist_categories', namespace, owner)},
            output_lookups={'cidr': ('threatlist_lookup_by_cidr', namespace, owner),
                            'ip': ('threatlist_lookup_by_str', namespace, owner),
                            'domain': ('threatlist_lookup_by_domain_or_url', namespace, owner),
                            'url': ('threatlist_lookup_by_domain_or_url', namespace, owner)},
            routing={'ip': {'cidr': lambda x: '/' in x}})


class ThreatlistManagerTldOutputSpec(LookupOutputSpec):
    def __init__(self, namespace, owner):
        super(ThreatlistManagerTldOutputSpec, self).__init__(
            ancillary_lookups={},
            output_lookups={'tld': ('cim_http_tld_lookup', namespace, owner)},
            routing={})