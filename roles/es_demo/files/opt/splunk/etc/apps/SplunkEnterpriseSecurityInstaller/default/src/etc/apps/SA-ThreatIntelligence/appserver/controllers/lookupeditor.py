import cherrypy
import csv
import logging
import os
import splunk
import splunk.entity as en
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.clilib.bundle_paths as bp

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.controllers.LookupEditor')

class LookupEditor(controllers.BaseController):
    '''Lookup editor Controller'''

    baseCSVPath = os.path.join(bp.get_base_path(), '%s', 'lookups')

    @route('/:load=load')
    @expose_page(must_login=True, methods=['GET']) 
    def load(self, **kwargs):
        ## Get session key
        session_key = cherrypy.session.get('sessionKey')
        
        ## Get the user name
        user = cherrypy.session['user']['name']
        
        ## Get capabilities
        capabilities = LookupEditor.getCapabilities4User(user, session_key)
        
        ## Check capabilities
        if 'edit_lookups' not in capabilities:
            signature = 'User %s does not have the capability (edit_lookups) required to perform this action: load' % (user)
            logger.critical(signature)
            return self.render_error(_(signature))
        
        namespace = kwargs.get('namespace')
        baseCSVPath = self.baseCSVPath % namespace
        
        output = jsonresponse.JsonResponse()
        output.data = []
        
        path = kwargs.get('path')
        if not path:
            return self.render_error(_('Lookup file name not provided.'))
            
        info = self.checkLookup(baseCSVPath, path)
        if not info:
            return self.render_error(_('Lookup is not allowed for editing.'))
            
        appName, lookupName = path.split('/')
        lookupPath = os.path.join(bp.get_base_path(), appName, 'lookups', lookupName)
        if not os.path.exists(lookupPath):
            return self.render_error(_('Lookup file does not exist'))

        export = kwargs.get('export', 0)
            
        csvData = None
        with file(lookupPath, 'r') as f:
            csvData = f.read()
        
        if export == '1':
            cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="%s"' % lookupName
            cherrypy.response.headers['Content-Type'] = 'text/csv'
            return csvData
        else:
            output.data.append(info)
            output.data.append(csvData)
            
            return self.render_json(output, set_mime='text/plain')
            
    @route('/:save=save')
    @expose_page(must_login=True, methods=['POST']) 
    def save(self, **kwargs):
        ## Get session key
        session_key, sessionSource = splunk.getSessionKey(return_source=True)
        
        ## Get the user name
        user = cherrypy.session['user']['name']
        
        ## Get capabilities
        capabilities = LookupEditor.getCapabilities4User(user, session_key)
        
        ## Check capabilities
        if 'edit_lookups' not in capabilities:
            signature = 'User %s does not have the capability (edit_lookups) required to perform this action: edit' % (user)
            logger.critical(signature)
            return self.render_error(_(signature))
        
        output = jsonresponse.JsonResponse()
        output.data = []
        data = kwargs.get('lookupData')
        csvFile = kwargs.get('selectedLookup')
        
        if not data or not csvFile:
            return self.render_error(_('Nothing to save.'))
            
        appName, lookupName = csvFile.split('/')
        lookupPath = os.path.join(bp.get_base_path(), appName, 'lookups', lookupName)
        if not os.path.exists(lookupPath):
            return self.render_error(_('Cannot save the lookup - file does not exist.'))
        
        with file(lookupPath, 'w') as f:
            f.write(data)
            
        return self.render_json(output, set_mime='text/plain')
        
    def checkLookup(self, baseCSVPath, path):
        '''
        Checks if specified path is defined in the list of editable lookups and returns its 
        information if true
        '''
        lookups = {}
        editableLookups = os.path.join(baseCSVPath, 'editable_lookups.csv')
        if os.path.exists(editableLookups):
            with open(editableLookups, 'rb') as f:
                try:
                    for row in csv.DictReader(f):
                        if row.get('path') == path:
                            return row
                except Exception, e:
                    error = _('Error while reading the list of editable lookups. ') + str(e)
            return None

    @staticmethod
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
    
    def render_error(self, msg):
        return self.render_template('/SA-ThreatIntelligence:/templates/lookupeditor_error.html', {"message" : msg})
        
    def render_error_json(self, msg):
        output = jsonresponse.JsonResponse()
        output.data = []
        output.success = False
        output.addError(msg)
        return self.render_json(output, set_mime='text/plain')