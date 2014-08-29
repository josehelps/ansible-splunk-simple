import os
import shutil
import platform
from . import isLinux, isWindows, isSolaris, isMac, getSplunkAppDir

def deployInputs( dir_name = None ):
    
    # If the directory name was not present, then determine which inputs directory ought to be copied
    if dir_name is None:
        operating_system = platform.system()
        
        if isLinux(operating_system):
            deployInputs("linux_base")
        elif isWindows(operating_system):
            deployInputs("win_base")
        elif isSolaris(operating_system):
            deployInputs("solaris_base")
        elif isMac(operating_system):
            deployInputs("osx_base")
    else:
        
        # Enable the inputs associated with the application the default/inputs.conf.local to default/inputs.conf.local
        fullpath =  getSplunkAppDir() + os.sep + dir_name
        
        if os.path.exists( fullpath ):
            
            # This is the local file to be deployed
            inputs_file = os.path.join(fullpath, 'default', 'inputs.conf.local')
            
            # This is the location of the local file that enables the inputs
            local_inputs_file = os.path.join(fullpath, 'local', 'inputs.conf')
            
            # Deploy the file
            if os.path.exists( inputs_file ) and os.path.exists(local_inputs_file) == False:
                shutil.copyfile(inputs_file, local_inputs_file)