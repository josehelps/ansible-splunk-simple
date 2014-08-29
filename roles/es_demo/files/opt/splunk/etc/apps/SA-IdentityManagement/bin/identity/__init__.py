import base64
import csv
import os
import random
import re
import logging
import logging.handlers
import splunk.admin as admin
import splunk.util as util
import time

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
   
   logger = logging.getLogger('identityLookup_base_class')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'identityLookup_base_class.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()


class InvalidConfigException(Exception):
    pass


class InvalidParameterValueException(InvalidConfigException):
    """
    Describes a config parameter that has an invalid value.
    """
    
    def __init__(self, field, value, value_must_be):
        message = "The value for the parameter '%s' is invalid: %s (was %s)" % (field, value_must_be, value)
        super(InvalidConfigException, self).__init__( message)
      
        
class UnsupportedParameterException(InvalidConfigException):
    """
    Describes a config parameter that is unsupported.
    """
    pass


class Identity:
    
    PARAM_IDENTITY = 'identity'
    PARAM_EMAIL = 'email'
    PARAM_PREFIX = 'prefix'
    PARAM_NICK = 'nick'
    PARAM_FIRST = 'first'
    PARAM_LAST = 'last'
    PARAM_SUFFIX = 'suffix'
    PARAM_PHONE = 'phone'
    PARAM_PHONE2 = 'phone2'
    PARAM_MANAGEDBY = 'managedBy'
    PARAM_PRIORITY = 'priority'
    PARAM_BUNIT = 'bunit'
    PARAM_CATEGORY = 'category'
    PARAM_WATCHLIST = 'watchlist'
    PARAM_STARTDATE = 'startDate'
    PARAM_ENDDATE = 'endDate'
    PARAM_TAG = 'identity_tag'
    
    emailREpattern = '([^@]+)'
    emailRE = re.compile(emailREpattern)
    
    def __init__(self, identity, args={}):
        self.identity = {}
        
        ## initialize identity_tag    
        self.identity_tag = []
                
        ## identity - exact match
        self.identity[IdentityLookup.PARAM_EXACT] = []
        if identity.has_key(Identity.PARAM_IDENTITY) and args.has_key(IdentityLookup.PARAM_EXACT) and args[IdentityLookup.PARAM_EXACT]:
            identity[Identity.PARAM_IDENTITY] = identity[Identity.PARAM_IDENTITY].strip()
            
            if len(identity[Identity.PARAM_IDENTITY]) > 0:
                self.identity[IdentityLookup.PARAM_EXACT] = identity[Identity.PARAM_IDENTITY].split('|') 
        
        ## identity - email/email_short, email
        self.email = ''
        self.identity[IdentityLookup.PARAM_EMAIL] = []
        self.identity[IdentityLookup.PARAM_EMAIL_SHORT] = []
        
        if identity.has_key(Identity.PARAM_EMAIL):
            identity[Identity.PARAM_EMAIL] = identity[Identity.PARAM_EMAIL].strip()
            ## email
            self.email = identity[Identity.PARAM_EMAIL]
            
            ## identity - email
            if len(identity[Identity.PARAM_EMAIL]) > 0 and args.has_key(IdentityLookup.PARAM_EMAIL) and args[IdentityLookup.PARAM_EMAIL]:
                self.identity[IdentityLookup.PARAM_EMAIL] = [identity[Identity.PARAM_EMAIL]]
            
            ## identity - email_short is enabled
            if args.has_key(IdentityLookup.PARAM_EMAIL_SHORT) and args[IdentityLookup.PARAM_EMAIL_SHORT]:
                emailMatch = Identity.emailRE.match(identity[Identity.PARAM_EMAIL])
                
                ## email properly formatted
                if emailMatch:
                    self.identity[IdentityLookup.PARAM_EMAIL_SHORT] = [emailMatch.group(1)]
        
        ## identity - convention
        ## Iterate args looking for conventions
        if args.has_key(IdentityLookup.PARAM_CONVENTION) and args[IdentityLookup.PARAM_CONVENTION]:
            for key, val in args.items():
                conventionKeyMatch = IdentityLookup.conventionKeyRE.match(key)
                
                ## If a convention is found create an identity key
                if conventionKeyMatch:
                    conventionValMatch = IdentityLookup.conventionValRE.finditer(val)
                    
                    ## Iterate token specifications in convention value
                    ## and replace accordingly
                    for valMatch in conventionValMatch:
                        if identity.has_key(valMatch.group(1)):
                            ## If character length is empty
                            if valMatch.group(2) is None or len(valMatch.group(2)) == 0:
                                strLength = len(identity[valMatch.group(1)])
                                
                            ## If character length is not empty
                            else:
                                strLength = int(valMatch.group(2))
                            
                            val = val.replace(valMatch.group(0), identity[valMatch.group(1)][:strLength])
    
                    self.identity[key] = [val]
                
        ## prefix
        self.prefix = identity.get(Identity.PARAM_PREFIX, '').strip()          
        
        ## nick
        self.nick = identity.get(Identity.PARAM_NICK, '').strip()
            
        ## first
        self.first = identity.get(Identity.PARAM_FIRST, '').strip()
        
        ## last
        self.last = identity.get(Identity.PARAM_LAST, '').strip()
        
        ## suffix
        self.suffix = identity.get(Identity.PARAM_SUFFIX, '').strip()
            
        ## phone
        self.phone = identity.get(Identity.PARAM_PHONE, '').strip()
        
        ## phone2
        self.phone2 = identity.get(Identity.PARAM_PHONE2, '').strip()
        
        ## managedBy
        self.managedBy = identity.get(Identity.PARAM_MANAGEDBY, '').strip()
            
        ## priority
        self.priority = identity.get(Identity.PARAM_PRIORITY, '').strip()
        
        ## bunit
        self.bunit = identity.get(Identity.PARAM_BUNIT, '').strip()
        
        if len(self.bunit) > 0:
            self.identity_tag.append(self.bunit)
        
        ## category
        self.category = []
        if identity.has_key(Identity.PARAM_CATEGORY):
            identity[Identity.PARAM_CATEGORY] = identity[Identity.PARAM_CATEGORY].strip()
            
            if len(identity[Identity.PARAM_CATEGORY]) > 0:
                self.category = Identity.normalizeCategory(identity[Identity.PARAM_CATEGORY].split('|'))
                
                self.identity_tag.extend(self.category)
        
        ## watchlist
        if identity.has_key(Identity.PARAM_WATCHLIST):
            ## normalize boolean watchlist value to desired strings
            if util.normalizeBoolean(identity[Identity.PARAM_WATCHLIST].strip()) == True:
                self.watchlist = 'true'
                
                self.identity_tag.append(Identity.PARAM_WATCHLIST)
                
            else:
                self.watchlist = 'false'
        else:
            self.watchlist = 'false'
        
        ## startDate
        self.startDate = identity.get(Identity.PARAM_STARTDATE, '').strip()
        
        ## endDate
        self.endDate = identity.get(Identity.PARAM_ENDDATE, '').strip()

        
    def getVal(self, key, default=None):
        if key == Identity.PARAM_IDENTITY:
            identity = []
            
            for key in self.identity:
                for val in self.identity[key]:
                    if len(val) > 0:
                        identity.append(val)
            
            return identity
        
        elif key == Identity.PARAM_PREFIX:
            return self.prefix
        
        elif key == Identity.PARAM_NICK:
            return self.nick
        
        elif key == Identity.PARAM_FIRST:
            return self.first
        
        elif key == Identity.PARAM_LAST:
            return self.last
        
        elif key == Identity.PARAM_SUFFIX:
            return self.suffix
        
        elif key == Identity.PARAM_EMAIL:
            return self.email
        
        elif key == Identity.PARAM_PHONE:
            return self.phone
        
        elif key == Identity.PARAM_PHONE2:
            return self.phone2
        
        elif key == Identity.PARAM_MANAGEDBY:
            return self.managedBy
        
        elif key == Identity.PARAM_PRIORITY:
            return self.priority
        
        elif key == Identity.PARAM_BUNIT:
            return self.bunit
        
        elif key == Identity.PARAM_CATEGORY:
            return self.category
        
        elif key == Identity.PARAM_WATCHLIST:
            return self.watchlist
        
        elif key == Identity.PARAM_STARTDATE:
            return self.startDate
        
        elif key == Identity.PARAM_ENDDATE:
            return self.endDate
        
        elif key == Identity.PARAM_TAG:
            return self.identity_tag
        
        else:
            return default
        
    @staticmethod
    def normalizeCategory(category):
        pciFound = cardholderFound = False
        
        if len(category) > 0:
            for cat in category:
                if cat.lower() == 'pci':
                    pciFound = True
                    
                elif cat.lower() == 'cardholder':
                    cardholderFound = True
            
            if cardholderFound and not pciFound:
                category.append('pci')
                
        return category
    
    @staticmethod
    def getConventionsList(args):
        conventionTokens = []
        
        for key, val in args.items():
            conventionKeyMatch = IdentityLookup.conventionKeyRE.match(key)
            
            if conventionKeyMatch:
                conventionTokens.append(int(conventionKeyMatch.group(2)))
        
        conventionTokens.sort()
        
        return conventionTokens
    
    @staticmethod
    def BinSearch(search, alist, lo=0, hi=None, key=None, case_sensitive=False):
        if hi is None:
            hi = len(alist)
       
        while lo < hi:
            mid = (lo+hi)/2
            
            if key is None:
                midval = alist[mid]
                
            else:
                try:
                    midval = alist[mid][key]
                    
                except:
                    return False, -1
                
            if not case_sensitive:
                midval = midval.lower()
                search = search.lower()

            if midval < search:
                lo = mid+1
                
            elif midval > search: 
                hi = mid
                
            else:
                return True, mid
        
        return False, -1
    
    @staticmethod
    def reverseFind(outputResult, identity, identitiesHeader=[], case_sensitive=False):
        matchFound = False
        requiredMatchFields = []
        
        ## Iterate through keys in outputResult
        ## If outputResult has a value for those keys
        ## Add the key to requiredMatchFields
        for key, val in outputResult.items():
            if len(val) > 0:
                requiredMatchFields.append(key)
        
        ## Create a copy of requiredMatchFields specifically for iterating
        ## This is needed such that we don't remove items from our iterable.
        requiredMatchIter = requiredMatchFields[:]
        
        ## If there is at least one requiredMatchField
        if len(requiredMatchFields) > 0:
            ## Iterate through required match fields and look for a match
            for requiredMatchField in requiredMatchIter:
                for identityKey in identitiesHeader:
                    if requiredMatchField.endswith('_' + identityKey):
                        ## Initialize values
                        val = outputResult[requiredMatchField]
                        
                        ## Compare values
                        ## Handle identity key as a list
                        if identityKey == Identity.PARAM_IDENTITY or identityKey == Identity.PARAM_CATEGORY:
                            identityValues = identity.getVal(identityKey, [])
                            
                            for identityValue in identityValues:
                                ## Initialize case sensitivity
                                if not case_sensitive:
                                    val = val.lower()
                                    identityValue = identityValue.lower()
                            
                                if val == identityValue:
                                    requiredMatchFields.remove(requiredMatchField)
                                    break
                        
                        ## Normal comparison for other fields
                        else:
                            identityValue = identity.getVal(identityKey, '')
                            
                            if not case_sensitive:
                                val = val.lower()
                                identityValue = identityValue.lower()
                           
                            if val == identityValue:
                                requiredMatchFields.remove(requiredMatchField)
                        
            ## If all required fields have matched
            if len(requiredMatchFields) == 0:
                return True
            
            ## If required match fields still exist there is no match
            else:
                return False
        
        ## If there are no required match fields there can be no match   
        else:
            return False    
    
    @staticmethod
    def populateOutput(outputResult, identity, identitiesHeader=[]):
        ## Initialize list of outputResult objects
        outputResults = []
        
        ## Initialize list for mv identity fields
        usernameKey = ''
        usernames = []
        
        categoryKey = ''
        categories = []
        
        tagKey = ''
        tags = []
        
        ## Create a copy of output result in order to retain original outputResult
        tempOutputResult = outputResult.copy()
        
        ## Iterate through the keys in output results
        for outputKey in outputResult:
            ## Iterate through the keys in identity
            for identityKey in identitiesHeader:
                ## If outputKey matches identityKey
                if outputKey.endswith('_' + identityKey):
                    ## If key is identity, populate usernames
                    if identityKey == Identity.PARAM_IDENTITY:
                        usernameKey = outputKey
                        usernames = identity.getVal(identityKey, [])
                    
                    ## If key is category, populate categories
                    elif identityKey == Identity.PARAM_CATEGORY:
                        categoryKey = outputKey
                        categories = identity.getVal(identityKey, [])
                    
                    ## If key is watchlist
                    elif identityKey == Identity.PARAM_WATCHLIST:
                        tempOutputResult[outputKey] = identity.getVal(identityKey, 'false')
                    
                    ## If key is anything else, populate tempOutputResult    
                    else:
                        tempOutputResult[outputKey] = identity.getVal(identityKey, '')
            
            ## this is out here because Identity.PARAM_TAG is not in identitiesHeader            
            if outputKey.endswith('_' + Identity.PARAM_TAG):
                tagKey = outputKey
                tags = identity.getVal(Identity.PARAM_TAG, [])
        
        ## Add tempOutputResul
        outputResults.append(tempOutputResult)
        
        ## Handle usernames
        for username in usernames:
            ## Create a copy of output result in order to retain original outputResult
            tempOutputResult = outputResult.copy()
            tempOutputResult[usernameKey] = username
            outputResults.append(tempOutputResult)
        
        ## Handle categories
        for category in categories:
            ## Create a copy of output result in order to retain original outputResult
            tempOutputResult = outputResult.copy()
            tempOutputResult[categoryKey] = category
            outputResults.append(tempOutputResult)
            
        ## Handle tags
        for tag in tags:
            ## Create a copy of output result in order to retain original outputResult
            tempOutputResult = outputResult.copy()
            tempOutputResult[tagKey] = tag
            outputResults.append(tempOutputResult)
        
        return outputResults
    
    @staticmethod
    def reversePopulate(outputResult, usernameField, username):
        ## Create a copy of output result in order to retain original outputResult
        tempOutputResult = outputResult.copy()
        
        if outputResult.has_key(usernameField):
            tempOutputResult[usernameField] = username
            
        return tempOutputResult
   
    @staticmethod
    def makeIdentities(count, identitiesFile=None, identitiesHeader=None):
        identities = []
        
        if identitiesHeader is None:
            if identitiesFile is None:
                identitiesFile = make_splunkhome_path(["etc", "apps", IdentityLookup.DEFAULT_NAMESPACE, "lookups", IdentityLookup.DEFAULT_FILE])      
                
            identitiesHeader = IdentityLookup.getIdentitiesHeader(identitiesFile)
        
        try:
            count = int(count)
            
        except:
            return identities
        
        for x in range(0, count):
            identity = {}
            identities.append(Identity.makeIdentity(identitiesHeader))
            
        return identities
    
    @staticmethod
    def makeIdentity(identitiesHeader):
        ## Defaults
        MALE_PREFIX = ['', '', '', '', '', '', '', 'Mr.', 'Prof.', 'Capt.', 'Lt.', 'Dr.', 'Rev.']
        FEMALE_PREFIX = ['', '', '', '', '', '', 'Mrs.', 'Miss', 'Ms.', 'Prof.', 'Dr.']
        VALID_PRIORITIES = ['', '', '', '', 'low', 'medium', 'high', 'critical']
        BUNITS = ['', '', '', 'americas', 'emea', 'apac']
        CATEGORIES = ['hipaa', 'intern', 'iso27002', 'nerc', 'officer', 'pci', 'pip', 'sox', 'splunk']
        WATCHLIST = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        ENDDATE = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        
        identity = {}
                    
        if Identity.PARAM_IDENTITY in identitiesHeader:
            identity[Identity.PARAM_IDENTITY] = ''
                
        if Identity.PARAM_NICK in identitiesHeader:
            identity[Identity.PARAM_NICK] = ''
                
        if Identity.PARAM_FIRST in identitiesHeader:            
            firstKey = random.randint(0, 1)
                
            if firstKey == 0:
                if Identity.PARAM_PREFIX in identitiesHeader:
                    prefixKey = random.randint(0, len(FEMALE_PREFIX)-1)
                    identity[Identity.PARAM_PREFIX] = FEMALE_PREFIX[prefixKey]
                    
                firstFile = make_splunkhome_path(["etc", "apps", "SA-Eventgen", "samples", "dist.female.first"])
                    
            else:
                if Identity.PARAM_PREFIX in identitiesHeader:
                    prefixKey = random.randint(0, len(MALE_PREFIX)-1)
                    identity[Identity.PARAM_PREFIX] = MALE_PREFIX[prefixKey]
                      
                firstFile = make_splunkhome_path(["etc", "apps", "SA-Eventgen", "samples", "dist.male.first"])
                    
            firstFH = None
                
            try:
                firstFH = open(firstFile, 'rU')
                
                firstLines = firstFH.readlines()
                
                firstKey = random.randint(0, len(firstLines)-1)
                
                identity[Identity.PARAM_FIRST] = firstLines[firstKey][0].upper() + firstLines[firstKey][1:].strip()
                
            except:
                identity[Identity.PARAM_FIRST] = ''
                
            finally:
                if firstFH is not None:
                    firstFH.close()
        
        if Identity.PARAM_LAST in identitiesHeader:
            lastFile = make_splunkhome_path(["etc", "apps", "SA-Eventgen", "samples", "dist.all.last"])
            
            lastFH = None
            
            try:
                lastFH = open(lastFile, 'rU')
                
                lastLines = lastFH.readlines()
                
                lastKey = random.randint(0, len(lastLines)-1)
                
                identity[Identity.PARAM_LAST] = lastLines[lastKey][0].upper() + lastLines[lastKey][1:].strip()
                
            except:
                identity[Identity.PARAM_LAST] = ''
                
            finally:
                if lastFH is not None:
                    lastFH.close()
                    
        if Identity.PARAM_SUFFIX in identitiesHeader:
            identity[Identity.PARAM_SUFFIX] = ''
            
        if Identity.PARAM_EMAIL in identitiesHeader:
            email = ''
            
            if identity.has_key(Identity.PARAM_FIRST) and len(identity[Identity.PARAM_FIRST]) > 0:
                if identity.has_key(Identity.PARAM_LAST) and len(identity[Identity.PARAM_LAST]) > 0:
                    email = identity[Identity.PARAM_FIRST][0] + identity[Identity.PARAM_LAST]
                    email += '@acmecorp.com'
                    
            identity[Identity.PARAM_EMAIL] = email
            
        if Identity.PARAM_PHONE in identitiesHeader:
            phone_start = '+1 (800)55'
            phone_middle = str(random.randint(0, 9))
            phone_end = str(random.randint(0, 9999))
            
            if len(phone_end) != 4:
                while len(phone_end) < 4:
                    phone_end += '0'
            
            identity[Identity.PARAM_PHONE] = phone_start + phone_middle + '-' + phone_end
                            
        if Identity.PARAM_PHONE2 in identitiesHeader:
            identity[Identity.PARAM_PHONE2] = ''
            
        if Identity.PARAM_MANAGEDBY in identitiesHeader:
            identity[Identity.PARAM_MANAGEDBY] = ''
            
        if Identity.PARAM_PRIORITY in identitiesHeader:
            priorityKey = random.randint(0, len(VALID_PRIORITIES)-1)
            
            identity[Identity.PARAM_PRIORITY] = VALID_PRIORITIES[priorityKey]
            
        if Identity.PARAM_BUNIT in identitiesHeader:
            bunitKey = random.randint(0, len(BUNITS)-1)
            
            identity[Identity.PARAM_BUNIT] = BUNITS[bunitKey]
            
        if Identity.PARAM_CATEGORY in identitiesHeader:
            categoryCount = random.randint(0, 2)
            
            category = ''
            
            if categoryCount > 0:
                TEMP_CATEGORIES = CATEGORIES[:]
                
                for x in range(0, categoryCount):
                    categoryKey = random.randint(0, len(TEMP_CATEGORIES)-1)
                    
                    category += TEMP_CATEGORIES.pop(categoryKey) + '|'
                    
                category = category.strip('|')
                
            identity[Identity.PARAM_CATEGORY] = category                    
                
        if Identity.PARAM_WATCHLIST in identitiesHeader:
            watchlist = ''
            watchlistKey = random.randint(0, len(WATCHLIST)-1)

            if WATCHLIST[watchlistKey]:
                watchlist = 'true'
                
            identity[Identity.PARAM_WATCHLIST] = watchlist
                
        if Identity.PARAM_STARTDATE in identitiesHeader:
            nowTime = util.mktimegm(time.gmtime())
            timeOffset = random.randint(0, 315569260)
            
            startdate = time.gmtime(nowTime - timeOffset)
            
            identity[Identity.PARAM_STARTDATE] = time.strftime('%m/%d/%y %H:%M', startdate)
            
            if Identity.PARAM_ENDDATE in identitiesHeader:
                endDateKey = random.randint(0, len(ENDDATE)-1)
                enddate = ''
                
                if ENDDATE[endDateKey] and timeOffset > 31556926:
                    endOffset = random.randint(0, timeOffset-86400)
                    
                    enddate = time.gmtime(nowTime - endOffset)
                    
                    enddate = time.strftime('%m/%d/%y %H:%M', enddate)
                    
                identity[Identity.PARAM_ENDDATE] = enddate
    
        return Identity(identity, {IdentityLookup.PARAM_EXACT: True})


class IdentityLookup: 
    '''
    Set up supported arguments
    '''
    ## Default keys
    PARAM_MATCH_ORDER = 'match_order'
    PARAM_EXACT = 'exact'
    PARAM_EMAIL = 'email'
    PARAM_EMAIL_SHORT = 'email_short'
    PARAM_CONVENTION = 'convention'
    PARAM_CASE_SENSITIVE = 'case_sensitive'
    
    ## convention
    ## Patterns are included for easier export to classes that want to use them (eliminates Eclipse IDE errors)
    ## this regex is meant to match the convention key specification per identityLookup.conf
    conventionKeyREpattern = '^(convention\.(\d+))$'
    conventionKeyRE = re.compile(conventionKeyREpattern)
    ## this regex is meant to match the convention value specification per identityLookup.conf.spec
    conventionValREpattern = '(\w+)\((\d+)?\)'
    conventionValRE = re.compile(conventionValREpattern)
    
    VALID_MATCH_ORDER = [PARAM_EXACT, PARAM_EMAIL, PARAM_EMAIL_SHORT, PARAM_CONVENTION]
    
    VALID_PARAMS = [PARAM_MATCH_ORDER, PARAM_EXACT, PARAM_EMAIL, PARAM_EMAIL_SHORT, PARAM_CONVENTION, PARAM_CASE_SENSITIVE]
    REQUIRED_PARAMS = [PARAM_MATCH_ORDER, PARAM_EXACT, PARAM_EMAIL, PARAM_EMAIL_SHORT, PARAM_CONVENTION, PARAM_CASE_SENSITIVE]
    BOOLEAN_PARAMS = [PARAM_EXACT, PARAM_EMAIL, PARAM_EMAIL_SHORT, PARAM_CONVENTION, PARAM_CASE_SENSITIVE]

    ## Default Vals
    DEFAULT_STANZA = 'identityLookup'
    DEFAULT_NAMESPACE = 'SA-IdentityManagement'
    DEFAULT_OWNER = 'nobody'
    DEFAULT_FILE = 'identities.csv'

    def __init__(self):
        pass

    @staticmethod
    def confString2Dict(confString):
        settings = {}
        
        confStringRE = re.compile('([^=]+)=(.*?)(?:\t|$)')
        
        confStringMatch = confStringRE.finditer(confString.strip())
        
        for match in confStringMatch:
            settings[match.group(1)] = match.group(2)

        confDict = {IdentityLookup.DEFAULT_STANZA: settings}
        
        return confDict

    @staticmethod
    def confDict2String(identityLookupDict):
        confString = ''
          
        for stanza, settings in identityLookupDict.items():
            if stanza == IdentityLookup.DEFAULT_STANZA:
                for key, val in settings.items():
                    conventionKeyMatch = IdentityLookup.conventionKeyRE.match(key)
                      
                    if val is None:
                        val = ''
                          
                    if key in IdentityLookup.VALID_PARAMS or conventionKeyMatch:
                        subString = key + '=' + val + '\t'
                        confString += subString
          
        confString = confString.strip()
        
        return confString

    @staticmethod
    def decodeConf(encodedConfString):
        return base64.b64decode(encodedConfString)
                
    @staticmethod
    def encodeConf(confString):
        return base64.b64encode(confString)
    
    @staticmethod
    def str_to_bool(str):
        """
        Converts the given string to a boolean; raises a ValueError if the str cannot be converted to a boolean.
        
        Arguments:
        str -- the string that needs to be converted to a boolean.
        """
        
        bool_str = str.strip().lower()
        
        if bool_str in ["t", "true", "1"]:
            return True
        elif bool_str in ["f", "false", "0"]:
            return False
        else:
            raise ValueError("The value is not a valid boolean")
    
    @staticmethod
    def getIdentities(identitiesFile):
        logger.info("Retrieving identities csv")
                  
        ## Open the file
        identitiesFH = open(identitiesFile, 'rU')
          
        ## Read the file
        identitiesCSV = csv.reader(identitiesFH)
         
        logger.info("Successfully retrieved identities CSV")
        return identitiesFH, identitiesCSV  
                  
    @staticmethod
    def getIdentitiesHeader(identitiesFile=None, identitiesFH=None, identitiesCSV=None, closeFH=True):
        logger.info("Retrieving identities header")
        
        ## Initialize empty header
        header = []
        
        ## Initialize first variable
        first = True
        
        ## If a FH was not passed in, let's get it and a CSV object
        if identitiesFH is None:
           
            if identitiesFile is not None:     
                ## Since we are getting our own FH & CSV we will close FH explicitly
                closeFH = True
    
                try:
                    identitesFH, identitiesCSV = IdentityLookup.getIdentities(identitiesFile)
                   
                except Exception as e:
                    logger.error("Error retrieving identities CSV: %s" % (str(e)))                    
                
                ## There is no need for the finally block here as closeFH is handled
                ## at the bootom of this method and will always be executed
                #finally:
                #    if identitiesFH is not None:
                #       identitiesFH.close()
                
            ## If there is no FH and no File, just return
            else:
                return header
        
        ## Verify CSV object
        if identitiesCSV is not None:
            for row in identitiesCSV:
                if first:
                    logger.info("Successfully retrieved identities header")
                    header = row
                    first = False
                    break
      
        ## If closing FH make sure it exists; then close
        if closeFH:
            if identitiesFH is not None:
                identitiesFH.close()
        
        ## If not closing FH make sure it exists; then seek to 0
        else:
            if identitiesFH is not None:
                identitiesFH.seek(0)
                 
        ## Return the header
        return header
           
    @staticmethod
    def checkConf(settings, stanza=None, confInfo=None, identitiesHeader=[], checkConventionVals=True, throwExceptionOnError=False):
        """
        Checks the settings and raises an exception if the configuration is invalid.
        """ 
        ## Below is a list of the required fields. The entries in this list will be removed as they
        ## are observed. An empty list at the end of the config check indicates that all necessary
        ## fields where provided.
        required_fields = IdentityLookup.REQUIRED_PARAMS[:]
        
        if confInfo is not None:
            
            if stanza == IdentityLookup.DEFAULT_STANZA:
                # Add each of the settings
                for key, val in settings.items():                  
                    conventionKeyMatch = IdentityLookup.conventionKeyRE.match(key)
                    
                    ## Set val to empty if None
                    if val is None:
                        val = ''
                        
                    if key in IdentityLookup.VALID_PARAMS or conventionKeyMatch:
                        confInfo[stanza].append(key, val)
                    
                    ## Key is eai; Set meta  
                    elif key.startswith(admin.EAI_ENTRY_ACL):
                        confInfo[stanza].setMetadata(key, val)
                                
                    ## Key is eai; userName/appName
                    elif key.startswith(admin.EAI_META_PREFIX):
                        confInfo[stanza].append(key, val)
                        
                    ## Key is not proper
                    else:
                        pass
        
        ## Check each of the settings individually
        logger.info("Checking general settings for identityLookup")
        if stanza is None or stanza == IdentityLookup.DEFAULT_STANZA:
            for key, val in settings.items():
                conventionKeyMatch = IdentityLookup.conventionKeyRE.match(key)
                
                ## Set val to empty if None
                if val is None:
                    val = ''
                
                ## Check the disabled/selected value
                if key in IdentityLookup.BOOLEAN_PARAMS:
                    try:
                        IdentityLookup.str_to_bool(val)
                        
                        ## Remove the field from the list of required fields
                        try:
                            required_fields.remove(key)
                            
                        except ValueError:
                            pass # Field not available, probably because it is not required
                            
                    except ValueError:
                        raise InvalidParameterValueException(key, val, "must be a valid boolean")
                
                elif key == IdentityLookup.PARAM_MATCH_ORDER:
                    valIter = val.split(',')
                    
                    if len(valIter) == 0:
                        raise InvalidParameterValueException(key, val, "%s must follow identityLookup specification" % (IdentityLookup.PARAM_MATCH_ORDER))
                    
                    else:
                        for valItem in valIter:
                            valItem = valItem.strip()
                            
                            if valItem not in IdentityLookup.VALID_MATCH_ORDER:
                                raise InvalidParameterValueException(key, val, "%s must follow identityLookup specification" % (IdentityLookup.PARAM_MATCH_ORDER))
                    
                    ## Remove the field from the list of required fields
                    try:
                        required_fields.remove(key)
                            
                    except ValueError:
                        pass # Field not available, probably because it is not required
                    
                ## Convention validation (if enabled)
                elif conventionKeyMatch:
                    if checkConventionVals:
                        IdentityLookup.checkConvention(key, val, identitiesHeader)           
                    
                elif key in IdentityLookup.REQUIRED_PARAMS:
                    ## Remove the field from the list of required fields
                    try:
                        required_fields.remove(key)
                            
                    except ValueError:
                        pass # Field not available, probably because it is not required
                            
                elif key in IdentityLookup.VALID_PARAMS:
                    pass
                                       
                ## Key is eai
                elif key.startswith(admin.EAI_META_PREFIX):
                    pass
                     
                ## Key is not proper
                else:
                    if throwExceptionOnError:
                        raise UnsupportedParameterException()
                    
                    else:
                        logger.warn("The configuration for identityLookup contains an unsupported parameter: %s" % (key))
        
            ## Error if some of the required fields were not provided
            if len(required_fields) > 0:
                raise InvalidConfigException('The following fields must be defined in the configuration but were not: ' + ', '.join(required_fields).strip())
                 
        else:
            raise InvalidConfigException("identityLookup.conf should only contain an '%s' stanza (was %s)" % (IdentityLookup.DEFAULT_STANZA, stanza))
        
    @staticmethod
    def checkConvention(conventionKey, conventionVal, identitiesHeader=[]):
        conventionValMatch = IdentityLookup.conventionValRE.findall(conventionVal)
                
        if len(conventionValMatch) == 0:
            raise InvalidParameterValueException(conventionKey, conventionVal, "%s must follow identityLookup specification" % (IdentityLookup.PARAM_CONVENTION))
                    
        else:
            for valMatch in conventionValMatch:
                valMatch = valMatch[0]               
                
                if valMatch not in identitiesHeader:
                    raise InvalidParameterValueException(conventionKey, conventionVal, "%s must follow identityLookup specification" % (IdentityLookup.PARAM_CONVENTION))