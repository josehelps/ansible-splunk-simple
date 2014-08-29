from splunk.models.base import SplunkRESTModel, SplunkAppObjModel
from splunk.models.field import Field, BoolField, IntField, ListField
import splunk.rest as rest
import logging

logger = logging.getLogger('splunk.models.base')

'''
Provides object mapping for input objects
'''

class Input(SplunkAppObjModel):
    
    resource              = 'data/inputs'
    disabled              = BoolField(is_mutable=False)
    host                  = Field() 
    index                 = Field()
    sourcetype            = Field()

    def _reload(self):
        path = '/'.join([self.id.rsplit('/', 1)[0], '_reload'])
        response, content = rest.simpleRequest(path,
                                 method='POST')
        if response.status == 200:
            return True
        return False

    def enable(self):
        if not self.action_links:
            return True 
        for item in self.action_links:
            if 'enable' in item: 
                response, content = rest.simpleRequest(item[1], 
                                         method='POST')
                if response.status == 200:
                    return True
        return False
 
    def disable(self):
        if not self.action_links:
            return True 
        for item in self.action_links:
            if 'disable' in item: 
                response, content = rest.simpleRequest(item[1], 
                                         method='POST')
                if response.status == 200:
                    return True
        return False
    
    def delete(self):
        if not self.action_links:
            return False
        for item in self.action_links:
            if 'remove' in item: 
                response, content = rest.simpleRequest(item[1], 
                                         method='DELETE')
                if response.status == 200:
                    return True
        return False
    
class ScriptedInput(Input):
    
    resource              = 'data/inputs/script'
    interval              = IntField()
    pass_auth             = Field(api_name='passAuth')

class MonitorInput(Input):

    resource               = 'data/inputs/monitor'
    blacklist              = Field()
    check_index            = BoolField(api_name='check-index')
    check_path             = BoolField(api_name='check-path')
    crc_salt               = Field(api_name='crc-salt')
    follow_tail            = BoolField(api_name='followTail')
    host_regex             = Field()
    host_segment           = Field()
    ignore_older_than      = Field(api_name='ignore-older-than')
    recursive              = BoolField()
    rename_source          = Field(api_name='rename-source')
    whitelist              = Field()

class EventLogCannon(Input):

    resource               = 'admin/win-alleventlogs'
    importance             = IntField(is_mutable=False)

class WinEventLogInput(Input):

    resource               = 'data/inputs/win-event-log-collections'
    disabled               = BoolField(is_mutable=False)
    hosts                  = Field()
    index                  = Field()
    logs                   = Field()
    lookup_host            = Field()

    def edit(self):
        """ 
	have to override save to remove the 'name' attribute
        as the win-event-log-collection endpoint does not
	seem to handle the 'name' field gracefully (it barfs)
	"""

        if not self.id or not self.entity:
            return False

        self._fill_entity(self.entity)

        for field in self.model_fields:
            if not self.model_fields[field].get_is_mutable():
                logger.error('removing non-mutable field: %s' % field)
                try:
                    del self.entity.properties[self.model_fields[field].get_api_name(field)]
                except KeyError:
                    logger.error('could not delete field: %s' % field)
                    pass

        messages = []

        entity = self.entity
        postargs = entity.getCommitProperties()

        try:
            entity_template = self.manager()._get_new_entity(namespace=entity.namespace, owner=entity.owner)
            allow_fields = entity_template['eai:attributes']['optionalFields']
            allow_fields.extend(entity_template['eai:attributes']['requiredFields'])
            wildcard_fields = entity_template['eai:attributes']['wildcardFields']

            to_delete = ['name']
            for arg in postargs:
                if arg not in allow_fields and not self._matches_any(arg, wildcard_fields):
                    messages.append('disallowed field being posted, removing: %s' % arg)
                    logger.info('disallowed field being posted, removing: %s' % arg)
                    to_delete.append(arg)
            for arg in to_delete:
                del postargs[arg]
            logger.error(postargs)
        except Exception, e:
            logger.info(e)

        newEntity = self.manager()._put_args(self.id, postargs, messages)

        if not newEntity:
            logger.debug(messages)
            return False

        self.entity = newEntity
        return True
    

class WinPerfmonInput(Input):

    resource               = 'data/inputs/win-perfmon'

class WinWMIInput(Input):

    resource               = 'data/inputs/win-wmi-collections'

class WinADInput(Input):

    resource               = 'data/inputs/ad'

class WinRegistryInput(Input):
  
    resource               = 'data/inputs/registry'

class SocketInput(Input):

    # TODO : cast to QueueField()
    group                  = Field(is_mutable=False)
    persistent_queue_size  = Field(api_name='persistentQueueSize')
    queue_size             = Field(api_name='queueSize')

class CookedTCPInput(SocketInput):

    resource               = 'data/inputs/tcp/cooked'
    compressed             = BoolField()
    enable_s2s_heartbeat   = BoolField()
    input_shutdown_timeout = IntField()
    # TODO: cast to RouteField()
    route                  = Field()
    s2s_heartbeat_timeout  = IntField()

class RawTCPInput(SocketInput):

    resource               = 'data/inputs/tcp/raw'
    connection_host        = Field()
    group                  = Field(is_mutable=False)
    restrict_to_host       = Field(api_name='restrictToHost')

class SSL(SplunkAppObjModel):

    resource               = 'data/inputs/tpc/ssl'
    cipher_suite           = Field(api_name='cipherSuite')
    require_client_cert    = BoolField(api_name='requireClientCert')
    root_ca                = Field(api_name='rootCA')
    server_cert            = Field(api_name='serverCert')
    server_cert_password   = Field(api_name='password')
    support_sslv3_only     = BoolField(api_name='supportSSLVOnly')

class UDPInput(Input):

    resource               = 'data/inputs/udp'
    connection_host        = Field()
    no_appending_timestamp = BoolField()
    no_priority_stripping  = BoolField()

