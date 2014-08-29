
import ConfigParser
import os
import re
import splunk.clilib.bundle_paths as bundle_paths
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


def get_session_key(session_key=None, thrown_exception=True):
    
    # Try to get the session key if not provided
    if session_key is None:
        import splunk
        session_key, sessionSource = splunk.getSessionKey(return_source=True)
    
    # Do not continue if we could not get a session key and the caller wants us to thrown an exception
    if session_key is None and thrown_exception:
        raise Exception("Could not obtain a session key")
    
    # Return the session key
    return session_key


def getSplunkAppDir():
    
    # Make sure to use the bundle paths so that this works with search head pooling
    return bundle_paths.get_base_path()


def isLinux(operating_system):
    regex = re.compile("linux", re.IGNORECASE)
    r = regex.search(operating_system)
    
    return (r is not None)


def isSolaris(operating_system):
    regex = re.compile("(solaris)|(sun[ ]*os)", re.IGNORECASE)
    r = regex.search(operating_system)
    
    return (r is not None)


def isWindows(operating_system):
    regex = re.compile("(Windows)|(Microsoft)", re.IGNORECASE)
    r = regex.search(operating_system)
    
    return (r is not None)


def isMac(operating_system):
    regex = re.compile("(Darwin)|(OS[ -]?X)", re.IGNORECASE)
    r = regex.search(operating_system)
    
    return (r is not None)


def isFipsEnabled():
    rv = False
    launch_conf = open(make_splunkhome_path(['etc', 'splunk-launch.conf']), 'r')
    for line in launch_conf:
        if re.search('^\s*SPLUNK_FIPS\s*=\s*1\s*$', line):
            rv = True
            break
    return rv


def processDirectory(basedir, fn, logger=None, force=False):
    
    # Exclude the installer app.
    INSTALL_APP_NAME = 'SplunkEnterpriseSecurityInstaller'
    
    # Iterate through each directory and run the given function
    for root, dirs, files in os.walk(basedir):
        if INSTALL_APP_NAME not in root:
            for filename in files:
                fn(root, filename, logger, force)
