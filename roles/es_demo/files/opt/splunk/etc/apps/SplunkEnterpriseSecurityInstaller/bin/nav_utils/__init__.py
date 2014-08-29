import splunk.clilib.bundle_paths as bp
import logging
import os
import re

APP_NAME_LOWER_PREFIX = "es"

## This logger instance name will be shared with the controller class
LOGGER_NAME = APP_NAME_LOWER_PREFIX + '_installer_controller'

def setup_logger(level):
    """
    Setup a logger for the controller
    """
    logger = logging.getLogger(LOGGER_NAME)
    
    return logger

# Setup the handler
logger = setup_logger(logging.INFO)

class NavUpgradeProcessor():

    def __init__(self, appName):
        self.appName = appName


    def getNav(self, context):
        """
        Return the local nav file for the given app.
        If one does not exist then return None.
        @context: app conf context - default or local
        @return: path to nav file or None if there is no nav
        """
        if (context == "default" or context == "local"):
            relativeLocaNavPath = os.path.join(context, "data", "ui", "nav", "default.xml")
            absoluteLocaNavPath = os.path.join(bp.get_base_path(), self.appName, relativeLocaNavPath)

            if os.path.exists(absoluteLocaNavPath):
                logger.info("nav_path=" + absoluteLocaNavPath)
                return absoluteLocaNavPath
            else:
                logger.info("nav_path=" + str(None))
                return None
        else:
            return None



    def deprecateNav(self, navPath):
        """
        Deprecate the nav.xml via rename - append ".old" to filename
        Remove any nav.xml.default so that it doesn't get re-deployed via setup
        @localNavPath: path to the local nav file
        @return: path to the local nav file
        """
        try:
            if os.path.exists(navPath):
                depNavPath = navPath + ".old"
                os.rename(navPath, depNavPath)
                logger.info("dep_nav_path=" + depNavPath)
                
                defaultLocalNavPath = navPath + ".default"
                try:
                    os.remove(defaultLocalNavPath)
                    logger.info("deleted:" + defaultLocalNavPath)
                except OSError:
                    # File doesn't exist
                    logger.info("nothing to delete - " + defaultLocalNavPath + " does not exist")
                    pass
                
                return depNavPath
            else:
                logger.info("dep_nav_path=" + str(None))
                return None
        except Exception as e:
            logger.error("error during deprecate nav")
            logger.exception(e)
