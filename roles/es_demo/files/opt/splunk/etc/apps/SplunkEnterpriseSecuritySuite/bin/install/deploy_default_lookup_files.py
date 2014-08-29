import os
import shutil

from . import processDirectory

def renameDefaultCSV(root, file, logger = None, force = False):
    
    # Determine if the file is a default CSV
    if file[-8:] == ".default":
        
        # Make sure the file does not already exist
        fname = root + os.sep + file[0:-8]
        
        if os.path.isfile( fname ) == False:
            
            # Log that we are copying the file
            if logger:
                logger.info( 'msg="Renaming default CSV file", src="%s", dest="%s"' % ( (root + os.sep + file), fname) )
                
            # Copy the file
            shutil.copyfile( root + os.sep + file, fname)

def deployDefaultLookupFiles( app_dir, logger = None ):
    processDirectory( app_dir, renameDefaultCSV, logger, False )
    
        