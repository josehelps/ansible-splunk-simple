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
   
   logger = logging.getLogger('user_realnames')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'splunk_user_realnames.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()

if __name__ == '__main__':
    logger.info('Starting user_realnames')
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
    app = 'SA-Utils'
    file = 'splunk_user_realnames.csv'
    
    ## Override Defaults w/ opts below
    if len(sys.argv) > 1:
        for a in sys.argv:
            if a.startswith('app='):
                where = a.find('=')
                app = a[where+1:len(a)]
            elif a.startswith('file='):
                where = a.find('=')
                file = a[where+1:len(a)]
                
    ## 1 -- Get the full file path and open the file
    logger.info('Setting up file paths and handles')
    grandparent = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) 
    usersFile = os.path.join(grandparent, app, 'lookups', file)
    usersTempMH = os.tmpfile()
    
    try:
        usersFH = open(usersFile, 'rU')
        usersFileData = usersFH.read()
    
    except Exception as e:
        logger.warn(e)
        usersFileData = ''
            
    ## 2 -- Get users
    usersEntity = 'authentication/users'
    logger.info('Retrieving users from %s' %(usersEntity))
    usersDict = entity.getEntities(usersEntity, count=-1, sessionKey=sessionKey)

    ## 3 -- Iterate users
    logger.info('Processing users')
    users = {}
    
    for stanza, settings in usersDict.items():
        user = {}
        user['user'] = stanza
        
        for key, val in settings.items():
            if key == 'realname':
                user['realname'] = val
                
        users[stanza] = user
    
    ## 4 -- Set up users
    logger.info('Writing users')
    header = ['user','realname']
    csv.writer(usersTempMH, lineterminator='\n').writerow(header)
    usersResults = csv.DictWriter(usersTempMH, header, lineterminator='\n')
    
    ## 5 -- Write out users
    for user, settings in users.items():
        usersResult = {}
        capabilities = []
                
        usersResult['user'] = user
            
        if settings.has_key('realname'):
            usersResult['realname'] = settings['realname']
                
        usersResults.writerow(usersResult)
              
    ## 6 -- Replace if necessary
    usersTempMH.seek(0)
    usersTempMemData = usersTempMH.read()
    
    if usersTempMemData == usersFileData:
        logger.info("File %s does not require change; exiting" % (usersFile))
        usersFH.close()
        usersTempMH.close()
        
    else:
        usersTempFile = usersFile + '.tmp'
        logger.info("File %s requires updating" % (usersFile))
        usersTempFH = open(usersTempFile, 'w')
        logger.info("Writing temporary file %s" % (usersTempFile))
        usersTempFH.write(usersTempMemData)
        usersTempMH.close()
        usersTempFH.close()
        logger.info("Moving temporary file %s to %s" % (usersTempFile, usersFile))
        shutil.move(usersTempFile, usersFile)