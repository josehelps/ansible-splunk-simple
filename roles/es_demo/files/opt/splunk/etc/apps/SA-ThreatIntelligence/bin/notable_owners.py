'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import logging
import logging.handlers
import os
import shutil
import splunk.auth as auth
import splunk.entity as entity
import sys

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('notable_owners')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'notable_owners.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()


def getImportedRoles(role, rolesDict):
    imported_roles = []
    
    if role is not None and rolesDict is not None:
        for stanza, settings in rolesDict.items():
            if stanza == role:
                for key, val in settings.items():
                    if key == 'imported_roles':
                        imported_roles = val
                        break
                    
    return imported_roles


def traverseRoles(role, roles, rolesDict):
    imported_roles = getImportedRoles(role, rolesDict)
    for imported_role in imported_roles:
        if imported_role not in roles:
            roles.append(imported_role)
            traverseRoles(imported_role, roles, rolesDict)
            

if __name__ == '__main__':
    logger.info('Starting notable_owners')
    debug = False
      
    ## Get session key sent from splunkd
    sessionKey = sys.stdin.readline().strip()
              
    if len(sessionKey) == 0:
      e = "Did not receive a session key from splunkd. Please enable passAuth in inputs.conf for this script\n"
      logger.critical(e)
      sys.stderr.write(e)
      exit(2)
        
    elif sessionKey == 'debug':
      debug = True
      sessionKey = auth.getSessionKey('admin', 'changeme')
        
    ## Defaults
    app = 'SA-ThreatIntelligence'
    file = 'notable_owners.csv'
    capability = 'can_own_notable_events'

    ## Override Defaults w/ opts below
    if len(sys.argv) > 1:
        for a in sys.argv:
            if a.startswith('app='):
                where = a.find('=')
                app = a[where+1:len(a)]
            elif a.startswith('file='):
                where = a.find('=')
                file = a[where+1:len(a)]
            elif a.startswith('capability='):
                where = a.find('=')
                capability = a[where+1:len(a)]
                
    ## 1 -- Get the full file path and open the file
    logger.info('Setting up file paths and handles')
    grandparent = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) 
    ownersFile = os.path.join(grandparent, app, 'lookups', file)
    ownersTempMH = os.tmpfile()
    
    try:
        ownersFH = open(ownersFile, 'rU')
        ownersFileData = ownersFH.read()
    
    except Exception as e:
        logger.warn(e)
        ownersFileData = ''
            
    ## 2 -- Get users
    usersEntity = 'authentication/users'
    logger.info('Retrieving users from %s' %(usersEntity))
    usersDict = entity.getEntities(usersEntity, count=-1, sessionKey=sessionKey)
    
    ## 3 -- Get roles
    rolesEntity = 'authorization/roles'
    logger.info('Retrieving roles from %s' %(rolesEntity))
    rolesDict = entity.getEntities(rolesEntity, count=-1, sessionKey=sessionKey)
    
    ## 4 -- Get capabilities
    capabilitiesDict = {}
    for stanza, settings in rolesDict.items():
        capabilitiesDict[stanza] = []
        
        for key, val in settings.items():
            if key == 'capabilities' or key =='imported_capabilities':
                capabilitiesDict[stanza].extend(val)
    
    ## 5 -- Iterate users
    logger.info('Processing users')
    owners = {}
    
    for stanza, settings in usersDict.items():
        owner = {}
        owner['owner'] = stanza
        
        for key, val in settings.items():
            if key == 'roles':
                owner['roles'] = val
            elif key == 'realname':
                owner['realname'] = val
                
        owners[stanza] = owner
    
    ## 6 -- Set up owners
    logger.info('Writing owners')
    header = ['owner','realname']
    csv.writer(ownersTempMH, lineterminator='\n').writerow(header)
    ownersResults = csv.DictWriter(ownersTempMH, header, lineterminator='\n')
    
    ## 7 -- Add unassigned user (per SOLNESS-1386)
    ownersResults.writerow({'owner': 'unassigned', 'realname': ''})
    
    ## 8 -- Recurse imported roles
    for owner, settings in owners.items():
        ownersResult = {}
        roles = owners[owner]['roles']
        orig_roles = roles[:]
        capabilities = []
        
        ## Traverse roles
        for role in orig_roles:
            traverseRoles(role, roles, rolesDict)
            
        for role in roles:
            if capabilitiesDict.has_key(role):
                capabilities.extend(capabilitiesDict[role])
                        
        if capability in capabilities:
            ownersResult['owner'] = owner
            
            if settings.has_key('realname'):
                ownersResult['realname'] = settings['realname']
                
            ownersResults.writerow(ownersResult)
              
    ## 9 -- Replace if necessary
    ownersTempMH.seek(0)
    ownersTempMemData = ownersTempMH.read()
    
    if ownersTempMemData == ownersFileData:
        logger.info("File %s does not require change; exiting" % (ownersFile))
        ownersFH.close()
        ownersTempMH.close()
        
    else:
        ownersTempFile = ownersFile + '.tmp'
        logger.info("File %s requires updating" % (ownersFile))
        ownersTempFH = open(ownersTempFile, 'w')
        logger.info("Writing temporary file %s" % (ownersTempFile))
        ownersTempFH.write(ownersTempMemData)
        ownersTempMH.close()
        ownersTempFH.close()
        logger.info("Moving temporary file %s to %s" % (ownersTempFile, ownersFile))
        shutil.move(ownersTempFile, ownersFile)