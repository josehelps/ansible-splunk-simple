import os
import shutil

import splunk.rest as rest

from . import processDirectory


def __deployWindowsConfFiles(root, filename, logger=None, force=False):
    
    if force or os.name in ['nt', 'os2']:
        
        # Determine if the file ends with a "windows" extension and is in the 
        # default directory
        if root[-7:] == 'default' and filename[-8:] == ".windows":
            
            # Create the resulting filename
            dest_file = root + os.sep + filename[0:-8]
            
            # If the file already exists, then copy the file to another with a "unix" extension
            if os.path.isfile(dest_file) == True and os.path.isfile(dest_file + ".unix") == False:
                
                # Log that we are moving the file
                if logger:
                    logger.info("msg=Moving Unix style configuration file, src=%s, dest=%s" % (dest_file, (dest_file + ".unix")))
                
                # Move the file
                shutil.move(dest_file, dest_file + ".unix")
                
            # Log that we are copying the file
            if logger:
                logger.info("msg=Copying Windows style configuration file, src=%s, dest=%s" % ((root + os.sep + filename), dest_file))
                
            # Copy the file
            shutil.copyfile(root + os.sep + filename, dest_file)
          
          
def deployWindowsConfFiles(app_dir, session_key, logger=None, force=False):

    processDirectory(app_dir, __deployWindowsConfFiles, logger, force)

    # Reload inputs.conf
    rest.simpleRequest('configs/conf-inputs/_reload', sessionKey=session_key)
