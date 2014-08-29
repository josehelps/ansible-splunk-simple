'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''

import logging
import controllers.module as module
import cherrypy
import splunk.entity as en
import json
import traceback
import sys
import os
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

logger = logging.getLogger('splunk.appserver.SA-Utils.modules.SOLNLookupEditor')

# Import the lookup files helper
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "bin"]))
import lookupfiles

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.models import SplunkLookupTransform

def getNamespaceForLookupTransform( lookup_name, session_key):
    
    lookup_transform = SplunkLookupTransform.get(SplunkLookupTransform.build_id(lookup_name, None, None), sessionKey=session_key)
    
    if lookup_transform:
        return lookup_transform.namespace

def getLookupFile( lookup_name, namespace, session_key, owner=None ):
    
    if namespace is None:
        namespace = getNamespaceForLookupTransform(lookup_name, session_key)
    
    return lookupfiles.get_lookup_table_location( lookup_name, namespace, owner, key=session_key, fullpath=False )

def getCapabilities4User(user=None, session_key=None):
    roles = []
    capabilities = []
    
    ## Get user info              
    if user is not None:
        logger.info('Retrieving role(s) for current user: %s' % (user))
        userDict = en.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
    
        for stanza, settings in userDict.items():
            if stanza == user:
                for key, val in settings.items():
                    if key == 'roles':
                        logger.info('Successfully retrieved role(s) for user: %s' % (user))
                        roles = val
         
    ## Get capabilities
    for role in roles:
        logger.info('Retrieving capabilities for current user: %s' % (user))
        roleDict = en.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
        
        for stanza, settings in roleDict.items():
            if stanza == role:
                for key, val in settings.items():
                    if key == 'capabilities' or key =='imported_capabilities':
                        logger.info('Successfully retrieved %s for user: %s' % (key, user))
                        capabilities.extend(val)
        
    return capabilities


class SOLNLookupEditor(module.ModuleHandler):

    def generateResults(self, **args):
        
        # Prepare a response
        response = {}
        
        # Save the correlation search
        try:
            
            # Do something here...
            response["message"] = "No operation performed; this is a placeholder"
            response["success"] = False

        except Exception, e :
            
            tb = traceback.format_exc()
            
            response["message"] = str(e)
            response["trace"] = tb
            response["success"] = False

        # Return 
        return json.dumps(response)