'''
Copyright (C) 2009-2013 Splunk Inc. All Rights Reserved.
Author:         Luke Murphey
Description:    This python script handles the parameters in the configuration page.
                handleList method: lists configurable parameters in the configuration page
                handleEdit method: controls the parameters and save the values in the ess.conf of SplunkESS local directory 
'''
import splunk.admin as admin


class ConfigESSApp(admin.MConfigHandler):
    
    incompatible_apps = ['unix', 'windows', 'SplunkforCiscoSecurity']
    
    '''
    Set up supported arguments
    '''
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['ESS_disable_incompatible_apps', 'ESS_do_install']:
                self.supportedArgs.addOptArg(arg)
                
    '''
    Lists configurable parameters
    '''
    def handleList(self, confInfo):
        
        stanza = "general_settings"
        
        # By default, don't disable incompatible apps (let the installer decide)
        confInfo[stanza].append('ESS_disable_incompatible_apps', '0')
        
        confInfo[stanza].append('ESS_do_install', '1')
        
    '''
    Controls parameters
    '''
    def handleEdit(self, confInfo):
        
        import splunk.entity
        from install.essinstaller import ESSInstaller
        
        if self.callerArgs.data['ESS_do_install'][0] in [1, '1']:
            # Run the installer  
            ESSInstaller.doInstall(session_key=self.getSessionKey())
        
        # The user wants to disable incompatible applications
        if self.callerArgs.data['ESS_disable_incompatible_apps'][0] in [1, '1']:
            
            # Disable the incompatible applications
            for app in ConfigESSApp.incompatible_apps:
                splunk.entity.controlEntity('disable', 'apps/local/' + app + '/', sessionKey=self.getSessionKey())

        ## reload the app to trigger splunkd restart
        self.handleReload()

    def handleReload(self, confInfo=None):
        """
        Handles refresh/reload of the configuration options
        """
        import splunk.entity
        refreshInfo = splunk.entity.refreshEntities('apps/local/SplunkEnterpriseSecuritySuite', sessionKey=self.getSessionKey())
        
# initialize the handler
admin.init(ConfigESSApp, admin.CONTEXT_NONE)
