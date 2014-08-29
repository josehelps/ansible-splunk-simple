import cherrypy
import csv
import logging

import splunk
import splunk.entity as entity
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

# Setup the logger
logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.controllers.NotableInfo')

class Notable(controllers.BaseController):
    '''Returns information about notable event urgencies'''

    DEFAULT_NAMESPACE = "SA-ThreatIntelligence"
    DEFAULT_OWNER = 'nobody'
    REVIEW_STATUSES_REST_URL = '/alerts/reviewstatuses/'
    LOG_REVIEW_REST_URL = '/alerts/log_review/'

    def getUrgencies(self, addEmpty=False) :
        urgencies = []
        file_path = make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "urgency.csv"])
        
        ### get the unique urgencies.
        try:
            with open(file_path, "rb") as rFile:
                for row in csv.DictReader(rFile):
                    if row["urgency"] not in urgencies: 
                        urgencies.append(row["urgency"])
                rFile.close()
        except IOError:
            ### The file could be loaded, don't load the urgencies (this happens when setup has not been executed yet)
            pass
          
        ### return them as label,value pairs.
        urgencyDicts = []
        
        # Add an empty option that allows us to leave the urgency as the default
        if addEmpty:
            urgencyDicts.append({
                "value": "",
                "label": ""
            })
        
        for i in range(len(urgencies)):
            urgencyDicts.append({
                "value": urgencies[i],
                "label": urgencies[i].capitalize()
            })
            
        return urgencyDicts
    
    @route('/:urgencies=urgencies')
    @expose_page(must_login=True, methods=['GET'])
    def urgencies(self, **kwargs):
        urgencies = self.getUrgencies()
        
        return self.render_json(urgencies)
    
    def getUsers(self, addEmpty=False) :
        userDicts = []
        
        file_path = make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "notable_owners.csv"])
        
        try:
            with open(file_path, "rb") as rFile:
                for row in csv.DictReader(rFile):
                    if row.has_key("realname") and row["realname"] is not None and len(row["realname"]) > 0:
                        userDicts.append({
                            "value": row["owner"],
                            "label": row["realname"]
                        })
                    else:
                        userDicts.append({
                            "value": row["owner"],
                            "label": row["owner"]
                        })
                rFile.close()
        except IOError:
            ### Notable owners could not be loaded (this happens when setup has not been executed yet)
            pass
               
        # Sort the array 
        def compare(a, b):
            
            if a['label'] == 'unassigned':
                return 1
            elif b['label'] == 'unassigned':
                return -1
                
            return cmp(a['label'], b['label'])
            
        userDicts.sort(compare)
        
        # Add an empty option that allows us to leave the user as the default
        if addEmpty:
            userDicts.insert(0, {
                "value": "",
                "label": ""
            })
                
        return userDicts

    @route('/:users=users')
    @expose_page(must_login=True, methods=['GET'])
    def users(self, **kwargs):
        users = self.getUsers()
        
        return self.render_json(users)
    
    def getStatuses(self, addEmpty=False):
        
        currentUser = cherrypy.session['user']['name']   #auth.getCurrentUser()['name']
        sessionKey  = cherrypy.session.get('sessionKey') #cherrypy.session['sessionKey']
            
        try :
            statusEntities = entity.getEntities(self.REVIEW_STATUSES_REST_URL, namespace=self.DEFAULT_NAMESPACE, count=500)
        
        except Exception, e:
            raise e
        
        ## Get capabilities for current user    
        capabilities = self.getCapabilities4User(currentUser, sessionKey)
        
        ## Iterate stanza's in statuses dictionary
        for stanza in statusEntities:
            matchFound = False
            
            ## Iterate current user's capabilities
            for capability in capabilities:
                ## If user has at least one transition capability to the iterated status set matchFound to true
                ## Note this does not take into consideration the current status of the notable event
                if capability.startswith('transition_reviewstatus-') and capability.endswith('to_' + stanza):
                    matchFound = True
            
            ## If a match was not found delete the status from the dictionary
            if not matchFound:
                del statusEntities[stanza]
        
        return self.getSortedStatusArray(statusEntities, addEmpty)
    
    def getSortedStatusArray(self, statusEntities, addEmpty=False) :
        statusSortOrder = ["new","in_progress","pending","resolved","closed"]
    
        statusArray = []
    
        for stanzaName in statusEntities:
            if stanzaName in statusSortOrder :
                order = statusSortOrder.index(stanzaName)
            else :
                order = 100
                
            statusArray.append({
                "value"    : stanzaName,
                "label"    : statusEntities[stanzaName]['label'],
                "disabled" : splunk.util.normalizeBoolean(statusEntities[stanzaName]["disabled"]),
                "order"    : order
            })
        
        # Add an empty option
        if addEmpty:
            statusArray.append({
                    "value"    : "",
                    "label"    : "",
                    "disabled" : False,
                    "order"    : 0
            })
            
        statusArray.sort(key=lambda x: x["order"])
               
        return statusArray
    
    @route('/:statuses=statuses')
    @expose_page(must_login=True, methods=['GET'])
    def statuses(self):
        statuses = self.getStatuses()
        
        return self.render_json(statuses)
    
    def commentLengthRequired(self):
        """
        Returns the length of the comment required.
        """
        
        # Get the session key
        session_key = cherrypy.session.get('sessionKey')
        
        # Get the configuration from the log_review endpoint
        comment_en = entity.getEntity(self.LOG_REVIEW_REST_URL, 'comment', namespace=self.DEFAULT_NAMESPACE, owner=self.DEFAULT_OWNER, sessionKey=session_key, count=-1)

        # Determine if a comment is required
        is_required = splunk.util.normalizeBoolean(comment_en['is_required'])
        
        # If a comment is not required then return 0
        if is_required is None or not is_required:
            return 0
        
        # Determine what length of a comment is required
        if comment_en['minimum_length'] is None:
            return 0
        else:
            minimum_length = comment_en['minimum_length']
        
            # Convert the length to an integer
            try:
                return int(minimum_length)
            except ValueError:
                
                # The minimum length is invalid, print an error message
                logger.warn( "The value for the minimum length is invalid: %s" % (minimum_length) )
                return 0
    
    def getCapabilities4User(self, user=None, sessionKey=None):
        """
        Obtains a list of capabilities in an list for the given user.
        
        Arguments:
        user -- The user to get capabilities for (as a string)
        sessionKey -- The session key to be used if it is not none
        """
        
        roles = []
        capabilities = []
        
        ## Get user info              
        if user is not None:
            logger.debug('Retrieving role(s) for current user: %s' % (user))
            userEntities = entity.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=sessionKey)

            for stanza, settings in userEntities.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            logger.debug('Successfully retrieved role(s) for user: %s' % (user))
                            roles = val
        
        ## Get capabilities
        for role in roles:
            logger.debug('Retrieving capabilities for current user: %s' % (user))
            roleEntities = entity.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=sessionKey)
          
            for stanza, settings in roleEntities.items():
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            logger.debug('Successfully retrieved %s for user: %s' % (key, user))
                            capabilities.extend(val)

        return capabilities
    
    def isUrgencyOverrideAllowed(self):
        """
        Determines if urgency overrides are allowed.
        """
        
        sessionKey = cherrypy.session.get('sessionKey')
        
        notable_en = entity.getEntity(self.LOG_REVIEW_REST_URL, 'notable_editing', namespace = self.DEFAULT_NAMESPACE, owner = self.DEFAULT_OWNER, count=-1, sessionKey=sessionKey)
        
        if 'allow_urgency_override' in notable_en:
            return splunk.util.normalizeBoolean( notable_en['allow_urgency_override'] )
        else:
            return True
    
    def getLogReviewSettings(self):
        
        commentLength = self.commentLengthRequired()
        urgencyOverrideAllowed = self.isUrgencyOverrideAllowed()
        
        return commentLength, urgencyOverrideAllowed
    
    @route('/:log_review_settings=log_review_settings')
    @expose_page(must_login=True, methods=['GET'])
    def logReviewSettings(self):
        
        commentLength, urgencyOverrideAllowed = self.getLogReviewSettings()
        
        return self.render_json({
                                 'comment_length_required'   : commentLength,
                                 'urgency_override_allowed'  : urgencyOverrideAllowed
                                 })
    
    @route('/:all=all')
    @expose_page(must_login=True, methods=['GET'])
    def all(self, **kwargs):
        users = self.getUsers()
        urgencies = self.getUrgencies()
        statuses = self.getStatuses()
        
        commentLength, urgencyOverrideAllowed = self.getLogReviewSettings()
        
        return self.render_json( {
                                    'users'                     : users,
                                    'urgencies'                 : urgencies,
                                    'statuses'                  : statuses,
                                    'comment_length_required'   : commentLength,
                                    'urgency_override_allowed'  : urgencyOverrideAllowed
                                 } )