import logging
import sys
import cherrypy

import splunk.entity as en
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk import RESTException, AuthorizationFailed

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.models import SplunkStoredCredential
from SolnCommon.credentials import CredentialManager

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('splunk.appserver.SA-Utils.controllers.CredentialManagerController')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'credential_manager_controller.log']), maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.DEBUG)
    
class CredentialManagerController(controllers.BaseController):
    '''Credential Manager Controller'''

    def __init__(self):
        try:
            self.sessionKey = cherrypy.session.get('sessionKey')
            self.cred_mgr = CredentialManager(self.sessionKey)
        except AttributeError:
            # when running test from main, there's no session
            self.sessionKey = None
            pass
        super(CredentialManagerController, self).__init__()
      
    def render_error_json(self, msg):
        """
        Render an error such that it can be returned to the client as JSON.
        
        Arguments:
        msg -- A message describing the problem (a string)
        """
        
        output = jsonresponse.JsonResponse()
        output.data = []
        output.success = False
        output.addError(msg)
        return self.render_json(output, set_mime='text/json')

    @expose_page(must_login=True, methods=['POST']) 
    def list(self, **kwargs):
        """
        Return a list of existing stored credentials
        Arguments:
        
        clear_password = Field()
        encr_password = Field()
        username = Field()
        password = Field()
        realm = Field()
        
        kwargs -- keyword args
        """
        output = jsonresponse.JsonResponse()
        output.data = []
        credSet = []
        
        try:
            en.refreshEntities(str(SplunkStoredCredential.resource), sessionKey=self.sessionKey)
            
            creds = SplunkStoredCredential.all(sessionKey = self.sessionKey)
            for cred in creds:
                credSet.append([cred.username, cred.realm, cred.namespace])

            output.data.append(credSet)
            
            return self.render_json(output)

        except AuthorizationFailed as e:
            return self.render_error_json("You do not have permission to view stored credentials")

        except Exception as e:
            logger.exception(e)
            return self.render_error_json("ERROR: CredentialManagerController::list")

    @expose_page(must_login=True, methods=['POST']) 
    def update(self, **kwargs):
        """
        Return a list of existing stored credentials
        Arguments:
        kwargs -- keyword args
        """
        output = jsonresponse.JsonResponse()
        output.data = []

        try:
            self.sessionKey = cherrypy.session.get('sessionKey')
            self.cred_mgr = CredentialManager(self.sessionKey)
            encr_password = self.cred_mgr.set_password(kwargs.get('user', None), kwargs.get('realm', None),
                                       kwargs.get('password', None), kwargs.get('app', None),
                                       kwargs.get('owner', None))
            output.data.append(encr_password)
            return self.render_json(output)

        except AuthorizationFailed as e:
            return self.render_error_json("You do not have permission to edit stored credentials")
        
        except Exception as e:
            logger.exception(e)
            return self.render_error_json("ERROR: CredentialManagerController::update")
            

    @expose_page(must_login=True, methods=['POST']) 
    def create(self, **kwargs):
        """
        Return a list of existing stored credentials
        Arguments:
        kwargs -- keyword args
        """
        output = jsonresponse.JsonResponse()
        output.data = []

        try:
            self.sessionKey = cherrypy.session.get('sessionKey')
            self.cred_mgr = CredentialManager(self.sessionKey)
            encr_password = self.cred_mgr.create(kwargs.get('user', None), kwargs.get('realm', None),
                                       kwargs.get('password', None), kwargs.get('app', None),
                                       kwargs.get('owner', None))
            output.data.append(encr_password)
            return self.render_json(output)

        except AuthorizationFailed as e:
            return self.render_error_json("You do not have permission to create stored credentials")
        
        except RESTException as e:
            
            if e.statusCode == 409:
                logger.warn("Attempt to make a duplicate of a credential")
                return self.render_error_json("Credential already exists; please use a different user field or edit the existing entry")
            else:
                logger.exception(e)
                return self.render_error_json("Credential could not be created")

        except Exception as e:
            logger.exception(e)
            return self.render_error_json("Credential could not be created")

if __name__ == "__main__":
    print "test"
