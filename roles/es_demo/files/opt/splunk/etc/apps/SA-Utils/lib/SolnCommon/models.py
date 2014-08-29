'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import json
import re
import splunk
import splunk.rest
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import BoolField
from splunk.models.field import Field
from splunk.models.field import IntField


# Custom field definitions for Splunk configuration objects. 
class DelimitedField(Field):
    '''Represents a field with a delimited sequence of values.'''

    def __init__(self, api_name=None, default_value=None, is_mutable=True, delim=None):
        self.default_value = default_value
        self.api_name = api_name
        self.is_mutable = is_mutable
        self.delim = delim

    def from_apidata(self, api_dict, attrname):
        data = super(DelimitedField, self).from_apidata(api_dict, attrname)
        if data:
            data = data.split(self.delim)
            return [i.strip() for i in data]
        return None

    def to_apidata(self, attrvalue):
        return None
    

class NumberedField(Field):
    '''
    Represents a numbered sequence of fields with the same prefix name,
    e.g.:

        convention.0 = stuff
        convention.1 = stuff

    Returns a single field with the values of all numbered configuration
    items. This implementation is read-only.
    '''
    
    def from_apidata(self, api_dict, attrname):
        api_name = self.get_api_name(attrname)
        api_rx = re.compile(api_name + '\.\d')

        values = []

        for api_k, api_v in api_dict.iteritems():
            if api_rx.match(api_k):
                values.append(api_v)

        return values

    def to_apidata(self, attrvalue):
        return None


class InputStatus(SplunkAppObjModel):
    '''Class for managing scripted and modular input statuses.'''
    resource = '/admin/inputstatus'
    inputs = Field() 


class SplunkDataModel(SplunkAppObjModel):
    '''Class for retrieving data model settings.
    '''
    resource = '/configs/conf-datamodels'
    acceleration = BoolField(api_name='acceleration')
    backfill_time = Field(api_name='acceleration.backfill_time')
    cron_schedule = Field(api_name='acceleration.cron_schedule')
    description = Field()  # Contains the JSON string representation of the datamodel itself.
    displayName = Field()
    earliest_time = Field(api_name='acceleration.earliest_time')
    manual_rebuilds = BoolField(api_name='acceleration.manual_rebuilds')
    max_time = Field(api_name='acceleration.max_time')

    @classmethod
    def _bool_to_str(cls, value):
        # Simple function to turn Booleans into the preferred format for
        # the datamodels.conf file. Use only when you absolutely, positively
        # know that the value is convertible to a Boolean.
        try:
            return 'true' if splunk.util.normalizeBoolean(value, enableStrictMode=True) else 'false'
        except ValueError:
            raise

    def set_acceleration(self, session_key, **kwargs):
        '''Update the acceleration settings for a data model.

        @return: The model entity.
        '''

        if not session_key:
            raise splunk.AuthenticationFailed
        
        # Remap our settings to the correct datamodels.conf name.
        output = {'acceleration': SplunkDataModel._bool_to_str(kwargs.get('acceleration', None)),
                  'acceleration.backfill_time': kwargs.get('backfill_time', None),
                  'acceleration.cron_schedule': kwargs.get('cron_schedule', None),
                  'acceleration.earliest_time': kwargs.get('earliest_time', None),
                  'acceleration.manual_rebuilds': SplunkDataModel._bool_to_str(kwargs.get('manual_rebuilds', None)),
                  'acceleration.max_time': kwargs.get('max_time', None)}
        postargs = {k: v for k, v in output.iteritems() if v is not None}

        # Acceleration settings must be placed in the same app as the data model's
        # JSON definition file. Thus, "app" and "owner" values are derived from
        # the model itself, and are not configurable.
        model_id = SplunkDataModel.build_id(name=self.name, namespace=self.namespace, owner=self.owner)
        inst = SplunkDataModel.manager()._put_args(model_id, postargs, sessionKey=session_key)
        return inst


class SplunkIdentityLookupConf(SplunkAppObjModel):
    '''Class for identity lookup configuration as defined in identityLookup.conf.
    Intended to be read-only.
    '''

    resource = '/data/transforms/identityLookup'

    # Standard fields.    
    case_sensitive = BoolField()
    convention = BoolField()
    email = BoolField()
    email_short = BoolField()
    exact = BoolField()

    # Custom fields.
    conventions = NumberedField(api_name="convention")
    match_order = DelimitedField(delim=',')
 
    
class SplunkLookupLimits(SplunkAppObjModel):
    '''Class for retrieving limits.conf settings pertaining to Splunk lookup
    tables.
    '''
    resource = '/configs/conf-limits/lookup'
    max_memtable_bytes = IntField()
    max_matches = IntField()
    max_reverse_matches = IntField()
    batch_index_query = BoolField()
    batch_response_limit = IntField()

    
class SplunkLookupTableFile(SplunkAppObjModel):
    '''Class for Splunk lookup table files.
    
    Note that on save(), the "path" is actually
    the file that will be copied into place to replace the existing lookup
    table.
    '''

    resource = '/data/lookup-table-files'
    name = Field()
    path = Field(api_name="eai:data")
    
    @staticmethod
    def reload(session_key=None):
        path = SplunkLookupTableFile.resource + "/" + '_reload'
        response, content = splunk.rest.simpleRequest(path, method='GET', sessionKey=session_key)
        if response.status == 200:
            return True
        return False


class SplunkLookupTransform(SplunkAppObjModel):
    '''Class for Splunk lookups as defined in transforms.conf.'''

    resource = '/data/transforms/lookups'
    case_sensitive_match = BoolField()
    filename = Field()
    match_type = DelimitedField(delim=',')
    name = Field()
    
    @staticmethod
    def reload(session_key=None):
        path = SplunkLookupTransform.resource + "/" + '_reload'
        response, content = splunk.rest.simpleRequest(path, method='GET', sessionKey=session_key)
        if response.status == 200:
            return True
        return False
    

class SplunkRole(SplunkAppObjModel):
    '''Class for Splunk roles.'''

    resource = '/authorization/roles'
    capabilities = Field()
    defaultApp = Field()
    imported_capabilities = Field()
    imported_roles = Field()
    imported_rtSrchJobsQuota = Field()
    imported_srchDiskQuota = Field()
    imported_srchFilter = Field()
    imported_srchIndexesAllowed = Field()
    imported_srchIndexesDefault = Field()
    imported_srchJobsQuota = Field()
    imported_srchTimeWin = Field()
    rtSrchJobsQuota = Field()
    srchDiskQuota = Field()
    srchFilter = Field()
    srchIndexesAllowed = Field()
    srchIndexesDefault = Field()
    srchJobsQuota = Field()
    srchTimeWin = Field()   


class SplunkStoredCredential(SplunkAppObjModel):
    '''Class for managing secure credential storage.'''

    # Requires Splunk 4.3 or higher.
    resource = 'storage/passwords'

    clear_password = Field()
    encr_password = Field()
    username = Field()
    password = Field()
    realm = Field()

