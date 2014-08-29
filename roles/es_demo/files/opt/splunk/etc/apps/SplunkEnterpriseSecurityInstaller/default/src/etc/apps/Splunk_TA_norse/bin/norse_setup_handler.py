'''
Copyright (C) 2009-2013 Splunk Inc. All Rights Reserved.
Author:         Luke Murphey
Description:    This python script handles the parameters in the configuration page.
                handleList method: lists configurable parameters in the configuration page
                handleEdit method: controls the parameters and save the values in the ess.conf of SplunkESS local directory 
'''
import logging
import sys
import urllib

APPNAME = 'Splunk_TA_norse'
import splunk
import splunk.admin as admin
import splunk.entity as en
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", APPNAME, "lib"]))
from credentials import CredentialManager
from log import setup_logger

# Setup the handler
logger = setup_logger('ta_norse_setup')
# Logging level doesn't hold unless set here, since it applies to 
logger.setLevel(logging.INFO)

class ConfigNorsePlugin(admin.MConfigHandler):
    
    REALM = ""
    DARKLIST_USER = "norse_darklist"
    IPVIKING_USER = "norse_ipviking"
    APP = "Splunk_TA_norse"
    PASSWORD_OWNER = "admin"
    
    inputs_to_enable = ['threatlist/norse_darklist']
    
    savedsearches_to_enable = ['Norse - Download Norse Darklist']
    
    '''
    Get current API key
    '''
    def get_current_api_key(self, name):
        
        cred_mgr = CredentialManager(self.getSessionKey())
        try:
            return cred_mgr.get_clear_password(name, self.REALM, self.APP, self.PASSWORD_OWNER)
        except:
            return ''
        
    '''
    Set up supported arguments
    '''
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['Norse_Darklist_API_Key', 'Norse_IPViking_API_Key']:
                self.supportedArgs.addOptArg(arg)
                
    '''
    Lists configurable parameters
    '''
    def handleList(self, confInfo):
        
        stanza = "general_settings"
        confInfo[stanza].append('Norse_Darklist_API_Key', self.get_current_api_key(self.DARKLIST_USER))
        confInfo[stanza].append('Norse_IPViking_API_Key', self.get_current_api_key(self.IPVIKING_USER))
        
    '''
    Controls parameters
    '''
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs
        
        # Get the API key(s)
        norse_darklist_api_key = self.callerArgs.data['Norse_Darklist_API_Key'][0]
        norse_ipviking_api_key = self.callerArgs.data['Norse_IPViking_API_Key'][0]
        
        # We cannot save an empty password. If the password is empty, then set it to a single space
        if norse_darklist_api_key is None:
            norse_darklist_api_key = ''
            action = "disable"
        else:
            action = "enable"

        if norse_ipviking_api_key is None:
            norse_ipviking_api_key = ''
        else:
            # No script actions are associated with IPViking. 
            pass

        # Save the API keys
        cred_mgr = CredentialManager(self.getSessionKey())
        if norse_darklist_api_key:
            try:
                darklist_encr_password = cred_mgr.create_or_set(self.DARKLIST_USER, self.REALM, norse_darklist_api_key, self.APP, self.PASSWORD_OWNER)
                logger.info("API keys successfully updated")
            except:
                logger.exception("Exception generated while saving Darklist credentials")
                raise Exception("The Darklist API key could not be saved")
        else:
            # Blank credential; do not set.
            pass

        if norse_ipviking_api_key:
            try:
                ipviking_encr_password = cred_mgr.create_or_set(self.IPVIKING_USER, self.REALM, norse_ipviking_api_key, self.APP, self.PASSWORD_OWNER)
                logger.info("IPViking API key successfully updated")
            except:
                logger.exception("Exception generated while saving IPViking credentials")
                raise Exception("The IPVIking API key could not be saved")
        else:
            # Blank credential; do not set.
            pass
        
        # See if SplunkEnterpriseSecuritySuite is installed.
        try:
            en.getEntity('/apps/local/', 'SplunkEnterpriseSecuritySuite', sessionKey=self.getSessionKey())
            es_installed = True
        except splunk.ResourceNotFound:
            logger.info('SplunkEnterpriseSecuritySuite is not installed. The "threatlist://norse_darklist" input will not be enabled.')
            es_installed = False

        # Enable the saved search to populate the Darklist
        if norse_darklist_api_key:
            for savedsearch_name in self.savedsearches_to_enable:
                input_uri = urllib.quote('/servicesNS/nobody/' + self.APP + '/saved/searches/' + savedsearch_name + '/')
                en.controlEntity(action, input_uri + action, sessionKey=self.getSessionKey())
                logger.info("Saved search successfully updated, savedsearch_name=%s, action=%s", savedsearch_name, action)

        # Enable or disable the inputs
        if es_installed:
            for input_name in self.inputs_to_enable:
                input_uri = '/servicesNS/nobody/' + self.APP + '/data/inputs/' + input_name + '/'
                en.controlEntity(action, input_uri + action, sessionKey=self.getSessionKey())
                logger.info("Input successfully updated, input_name=%s, action=%s", input_name, action)
        
# initialize the handler
admin.init(ConfigNorsePlugin, admin.CONTEXT_NONE)
