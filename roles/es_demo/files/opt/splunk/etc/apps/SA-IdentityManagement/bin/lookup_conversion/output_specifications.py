'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import sys

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))

from SolnCommon.lookup_conversion.output import LookupOutputSpec


class IdentityManagerAssetOutputSpec(LookupOutputSpec):
    '''Class defining how asset information will be routed to Splunk lookups.'''

    def __init__(self, namespace, owner):
        '''Initialize the specification.
        
        @param namespace: The app for all output lookup tables. Currently we do
            not support output to multiple apps.
        @param owner: The Splunk user to be used when creating lookup tables. In
            nearly all cases this will be "nobody" since lookup tables are shared.
        '''

        super(IdentityManagerAssetOutputSpec, self).__init__(
            ancillary_lookups={'category': ('category_lookup_from_assets', namespace, owner),
                'pci_domain': ('pci_domains_lookup_from_assets', namespace, owner)},
                                                             
            output_lookups={'cidr': ('asset_lookup_by_cidr', namespace, owner),
                'dns': ('asset_lookup_by_str', namespace, owner),
                'ip': ('asset_lookup_by_str', namespace, owner),
                'mac': ('asset_lookup_by_str', namespace, owner),
                'nt_host': ('asset_lookup_by_str', namespace, owner)},
                                                             
            routing={'ip': {'cidr': lambda x: '/' in x}})


class IdentityManagerIdentityOutputSpec(LookupOutputSpec):
    '''Class defining how identity information will be routed to Splunk lookups.'''

    def __init__(self, namespace, owner):
        '''Initialize the specification.
        
        @param namespace: The app for all output lookup tables. Currently we do
            not support output to multiple apps.
        @param owner: The Splunk user to be used when creating lookup tables. In
            nearly all cases this will be "nobody" since lookup tables are shared.
        '''

        super(IdentityManagerIdentityOutputSpec, self).__init__(
            ancillary_lookups={'category': ('category_lookup_from_identities', namespace, owner)}, 
            output_lookups={'identity': ('identity_lookup_expanded', namespace, owner)},
            routing=None)
