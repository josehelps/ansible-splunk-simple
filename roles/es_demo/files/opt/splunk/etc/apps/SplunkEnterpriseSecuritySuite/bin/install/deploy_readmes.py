
import os
import platform
import shutil
from . import getSplunkAppDir, isWindows


def deployWindowsReadmes( app_dir, logger = None, force = False ):
    """
    Creates copies of the README files with txt extensions if the platform is Windows.
    """
    
    # Only perform this operation on Windows
    if force or isWindows( platform.system() ):
        
        # Get a list of the apps
        files = os.listdir(app_dir)
    
        # Got through each app and copy as necessary
        for f in files:
            
            # If the app is a TA, then copy the file
            if os.path.isdir( app_dir + os.sep + f ) and f[0:3] == "TA-":
                
                # Get the path to the README
                readme_file = app_dir + os.sep + f + os.sep + "README"
                
                # This is the file name we will copy to
                readme_txt_file = readme_file + ".txt"
                
                # If the file exists, then copy it
                if os.path.exists( readme_file ):
                    
                    # Log what we are about to do
                    if logger:
                        logger.info( "Deploy readme file from %s to %s" % (readme_file , readme_txt_file) )
                    
                    # Move the file unless it already exists
                    if not os.path.exists( readme_txt_file ):
                        shutil.move(readme_file, readme_txt_file)
