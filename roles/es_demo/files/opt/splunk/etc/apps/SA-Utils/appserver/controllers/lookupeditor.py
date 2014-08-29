import logging
import os
import sys
import json
import shutil
import csv
import cherrypy
import re

from splunk import AuthorizationFailed as AuthorizationFailed
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
import splunk.bundle as bundle
import splunk.entity as entity
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import splunk.clilib.bundle_paths as bundle_paths
from splunk.util import normalizeBoolean as normBool
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

dir = os.path.join(util.get_apps_dir(), __file__.split('.')[-2], 'bin')

if not dir in sys.path:
    sys.path.append(dir)

import lookupfiles

# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('splunk.appserver.SA-Utils.controllers.LookupEditor')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'lookup_editor_controller.log']), maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.INFO)

from splunk.models.base import SplunkAppObjModel
from splunk.models.field import BoolField, Field

class PermissionDeniedException(Exception):
    pass

class App(SplunkAppObjModel):
    ''' Represents a Splunk app '''
    
    resource      = 'apps/local'
    is_disabled   = BoolField('disabled')
    is_configured = BoolField('configured')
    label         = Field()
    
def isEmpty( row ):
    
    for e in row:
        if e is not None and len(e.strip()) > 0:
            return False
        
    return True

class LookupEditor(controllers.BaseController):
    '''Lookup Editor Controller'''
 
    @staticmethod
    def getCapabilities4User(user=None, session_key=None):
        roles = []
        capabilities = []
        
        ## Get user info              
        if user is not None:
            logger.info('Retrieving role(s) for current user: %s' % (user))
            userDict = entity.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
        
            for stanza, settings in userDict.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            logger.info('Successfully retrieved role(s) for user: %s' % (user))
                            roles = val
             
        ## Get capabilities
        for role in roles:
            logger.info('Retrieving capabilities for current user: %s' % (user))
            roleDict = entity.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
            
            for stanza, settings in roleDict.items():
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            logger.info('Successfully retrieved %s for user: %s' % (key, user))
                            capabilities.extend(val)
            
        return capabilities     
    
    @expose_page(must_login=True, methods=['POST', 'GET']) 
    def save(self, lookup_file, contents, namespace, **kwargs):
        """
        Save the contents of a lookup file
        """

        logger.info("Saving lookup contents...")

        user = cherrypy.session['user']['name']
        session_key = cherrypy.session.get('sessionKey')
        
        # Get capabilities
        capabilities = LookupEditor.getCapabilities4User(user, session_key)
        
        # Check capabilities
        LookupEditor.check_capabilities(lookup_file, user, session_key)
        
        # Parse the JSON
        parsed_contents = json.loads(contents)
        
        # Create the temporary file
        temp_file_handle = lookupfiles.get_temporary_lookup_file()
        
        # This is a full path already; no need to call make_splunkhome_path().
        temp_file_name = temp_file_handle.name
        destination_full_path = make_splunkhome_path(['etc', 'apps', namespace, 'lookups', lookup_file])
        
        # Write out the new file to a temporary location
        try:
            if temp_file_handle is not None and os.path.isfile(temp_file_name):
                
                csv_writer = csv.writer(temp_file_handle, lineterminator='\n')
                
                for row in parsed_contents:
                    
                    if not isEmpty(row): # Prune empty rows
                        csv_writer.writerow( row )
        
        finally:
            if temp_file_handle is not None:
                temp_file_handle.close()
        
        # Determine if the lookup file exists, create it if it doesn't
        if not os.path.exists(destination_full_path):
            shutil.move(temp_file_name, destination_full_path)
            logger.info('Lookup created successfully, user=%s, namespace=%s, lookup_file=%s', user, namespace, lookup_file)
            
        # Edit the existing lookup otherwise
        else:
            lookupfiles.update_lookup_table(filename=temp_file_name, lookup_file=lookup_file, namespace=namespace, owner="nobody", key=session_key)
            logger.info('Lookup edited successfully, user=%s, namespace=%s, lookup_file=%s', user, namespace, lookup_file)
     
    def render_error_json(self, msg):
        output = jsonresponse.JsonResponse()
        output.data = []
        output.success = False
        output.addError(msg)
        return self.render_json(output, set_mime='text/plain')
    
    @expose_page(must_login=True, methods=['GET']) 
    def get_original_lookup_file(self, lookup_file, namespace="SA-Utils", **kwargs):
        """
        Provides the contents of a lookup file.
        """
        
        try:
            
            with self.get_lookup( lookup_file, namespace, None ) as f:
                csvData = f.read()
            
            cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="%s"' % lookup_file
            cherrypy.response.headers['Content-Type'] = 'text/csv'
            return csvData
            
        except IOError:
            cherrypy.response.status = 404
            return self.render_json([])
        
        except PermissionDeniedException as e:
            cherrypy.response.status = 403
            return self.render_error_json(_(str(e)))
    
    @classmethod
    def check_capabilities(cls, lookup_file, user, session_key ):
        
        # Get the user's name and session
        user = cherrypy.session['user']['name'] 
        session_key = cherrypy.session.get('sessionKey')
        
        # Get capabilities
        capabilities = LookupEditor.getCapabilities4User(user, session_key)
        
        # Check capabilities
        if lookup_file.startswith('ppf_'):
            capability = 'edit_per_panel_filters'
        else:
            capability = 'edit_lookups'
            
        if capability not in capabilities:
            signature = 'User %s does not have the capability (edit_lookups or edit_per_panel_filters) required ' % (user)
            logger.critical(signature)
            raise PermissionDeniedException(signature)
    
    def get_lookup(self, lookup_file, namespace="SA-Utils", owner=None, get_default_csv=True ):
        """
        Get a file handle to the associated lookup file.
        """
        
        logger.info("Retrieving lookup file contents...")
        
        # Get the user's name and session
        user = cherrypy.session['user']['name'] 
        session_key = cherrypy.session.get('sessionKey')
        
        # Check capabilities
        LookupEditor.check_capabilities(lookup_file, user, session_key)
        
        # Get the file path
        # Strip pathing information so that people cannot use ".." to get to files they should not be able to access
        lookup_file = os.path.basename(lookup_file)
        namespace = os.path.basename(namespace)
        
        if owner is not None:
            owner = os.path.basename(owner)
        
        if owner is not None:
            # e.g. $SPLUNK_HOME/etc/users/luke/SA-NetworkProtection/lookups/test.csv
            lookup_path = make_splunkhome_path(["etc", "users", owner, namespace, "lookups", lookup_file])
            lookup_path_default = make_splunkhome_path(["etc", "users", owner, namespace, "lookups", lookup_file + ".default"])
        else:
            lookup_path = make_splunkhome_path(["etc", "apps", namespace, "lookups", lookup_file])
            lookup_path_default = make_splunkhome_path(["etc", "apps", namespace, "lookups", lookup_file + ".default"])
        
        # Open the file
        if get_default_csv and not os.path.exists(lookup_path) and os.path.exists(lookup_path_default):
            return open(lookup_path_default, 'rb')
        else:
            return open(lookup_path, 'rb')

    def is_valid_file_name(self, lookup_file): 
        """
        Indicate if the lookup file is valid (doesn't contain invalid characters such as "..").
        """
         
        allowed_path = re.compile("^[-A-Z0-9_ ]+([.][-A-Z0-9_ ]+)*$", re.IGNORECASE)
        
        if not allowed_path.match(lookup_file):
            return False
        else:
            return True

    @expose_page(must_login=True, methods=['GET']) 
    def get_lookup_contents(self, lookup_file, namespace="SA-Utils", owner=None, header_only=False, **kwargs):
        """
        Provides the contents of a lookup file as JSON.
        """
        
        if header_only in ["1", "true", 1, True]:
            header_only = True
        else:
            header_only = False
        
        # Ensure that the file name is valid
        if not self.is_valid_file_name(lookup_file):
            cherrypy.response.status = 400
            return self.render_error_json(_("The lookup filename contains disallowed characters"))
        
        # Ensure that the namespace is valid
        if not self.is_valid_file_name(namespace):
            cherrypy.response.status = 400
            return self.render_error_json(_("The namespace contains disallowed characters"))
        
        # Ensure that the namespace is valid
        if owner is not None and not self.is_valid_file_name(owner):
            cherrypy.response.status = 400
            return self.render_error_json(_("The owner contains disallowed characters"))
        
        try:
            with self.get_lookup(lookup_file, namespace, owner) as csv_file:
                csv_reader = csv.reader(csv_file)
            
                # Convert the content to JSON
                lookup_contents = []
                
                for row in csv_reader:
                    lookup_contents.append(row)
                    
                    # If we are only loading the header, then stop here
                    if header_only:
                        break
                
                return self.render_json(lookup_contents)
            
        except IOError:
            cherrypy.response.status = 404
            return self.render_json([])
        
        except PermissionDeniedException as e:
            cherrypy.response.status = 403
            return self.render_error_json(_(str(e)))
        
    @expose_page(must_login=True, methods=['GET']) 
    def get_lookup_header(self, lookup_file, namespace="SA-Utils", owner=None, **kwargs):
        
        pass