import logging
from logging import handlers

import os

from deploy_windows_conf import deployWindowsConfFiles
from deploy_default_lookup_files import deployDefaultLookupFiles
from deploy_readmes import deployWindowsReadmes
from deploy_app_imports import deployAppImportUpdate
from deploy_manager_inputs import deployManagerInputs
from deploy_fips_compliant_settings import deployFips

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from . import getSplunkAppDir


def setup_logger():
    """
    Setup a logger.
    """
    
    logger = logging.getLogger('essinstall')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
    
    file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'essinstall.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger


class ESSInstaller:
    """
    Performs the various operations necessary to install ESS
    """
    
    @staticmethod
    def doInstall(splunk_home=None, logger=None, force=False, session_key=None):
        
        # Compute the locations of the Splunk apps directory
        if splunk_home is None:
            splunk_app_dir = getSplunkAppDir()
            
        else:
            splunk_app_dir = os.path.join(splunk_home, "etc", "apps")
        
        # Setup a logger if none was provided
        if logger is None:
            # Get the handler
            logger = setup_logger()
        
        # Log a message noting the ESS install is starting
        if logger:
            logger.info("Enterprise Security install is starting, splunk_app_dir=%s" % (splunk_app_dir))
        
        # Run the various operations
        deployDefaultLookupFiles(splunk_app_dir, logger=logger)
        deployWindowsConfFiles(splunk_app_dir, session_key, logger=logger, force=force)
        deployWindowsReadmes(splunk_app_dir, logger=logger, force=force)
        deployAppImportUpdate(session_key, input_to_enable='update_es', namespace='SplunkEnterpriseSecuritySuite', logger=logger)
        deployManagerInputs(session_key, logger=logger)
        deployFips(session_key, logger)
        
        # Log a message noting the ESS install is done
        if logger:
            logger.info("Enterprise Security install has completed")
