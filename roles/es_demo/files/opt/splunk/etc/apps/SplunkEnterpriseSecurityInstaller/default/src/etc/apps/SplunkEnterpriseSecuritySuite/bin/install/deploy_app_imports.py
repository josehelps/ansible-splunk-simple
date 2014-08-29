from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField
import splunk.rest as rest

class AppImportsUpdate(SplunkAppObjModel):
    
    resource              = 'data/inputs/app_imports_update'
    disabled              = BoolField(is_mutable=False)
    app_regex             = Field() 
    apps_to_update        = Field()

    def enable(self, session_key=None):
        if not self.action_links:
            return True 
        for item in self.action_links:
            if 'enable' in item: 
                response, content = rest.simpleRequest(item[1],
                                                       sessionKey=session_key,
                                                       method='POST')
                if response.status == 200:
                    return True
        return False
 
    def disable(self, session_key=None):
        if not self.action_links:
            return True 
        for item in self.action_links:
            if 'disable' in item: 
                response, content = rest.simpleRequest(item[1],
                                                       sessionKey=session_key, 
                                                       method='POST')
                if response.status == 200:
                    return True
        return False

def deployAppImportUpdate( session_key, input_to_enable, namespace, logger = None, force = False ):
    modular_input = AppImportsUpdate.get(AppImportsUpdate.build_id(input_to_enable, namespace, "nobody"), sessionKey=session_key)
    
    if force or modular_input.disabled:
        modular_input.enable(session_key=session_key)
        
        if logger:
            logger.info("Enabled the %s modular input", modular_input.name)
            
        return True
    
    else:
        return False