import os
import shutil

from . import processDirectory

def renameFilesForPCI(root, filename, logger = None, force = False):
    
    # Determine if the file is a PCI
    if filename[-4:] == ".pci":
        
        fname = root + os.sep + file[0:-4]

        # Handle default.pci files separately.        
        if filename[-12:] == ".default.pci":
            fname = root + os.sep + file[0:-12]
        
        # Make sure the file does not already exist
        if os.path.isfile( fname ) == False:
            
            # Log that we are copying the file
            if logger:
                logger.info( 'msg="Renaming default PCI file", src="%s", dest="%s"' % ( (root + os.sep + filename), fname) )
                
            # Copy the file
            shutil.copyfile( root + os.sep + filename, fname)

def deployPCIFiles( app_dir, logger = None ):
    processDirectory( app_dir, renameFilesForPCI, logger, False )
    
        