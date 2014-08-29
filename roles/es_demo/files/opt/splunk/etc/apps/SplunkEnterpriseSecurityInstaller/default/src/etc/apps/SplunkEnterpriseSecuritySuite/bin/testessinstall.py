'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import os
import platform
import re
import shutil
import splunk.Intersplunk
import stat
import sys
import logging
import traceback
from logging import handlers

from install.essinstaller import ESSInstaller

try:
    
    # Retrieve results and settings
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    
    # Get session key
    session_key = settings.get('sessionKey', None)
    
    # Run the install operations
    ESSInstaller.doInstall(session_key=session_key)
    
    # Make a note that the install completed and Splunk needs to be restarted
    results = splunk.Intersplunk.generateErrorResults("Initialization complete, please restart Splunk")
    splunk.Intersplunk.outputResults( results )
    
except Exception as e:
    logger.error("Error generated during execution: " + traceback.format_exc() )
        
    print_error( str(e) + "\n" + exc_trace )
        
    raise e
