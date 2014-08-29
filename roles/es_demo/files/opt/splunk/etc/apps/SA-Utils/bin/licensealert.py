import sys
import time
import datetime
import logging
import json

#CORE SPLUNK IMPORTS
import splunk
import splunk.search as splunkSearch
from splunk.rest import simpleRequest
import splunk.version as ver



#Modify Path to include SA-Utils/bin
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Utils', 'lib']))
from SolnCommon.messaging import Messenger
from SolnCommon.modinput import ModularInput, Field



########################################################################
# UTILITIES 
########################################################################
def setupLogger(logger=None, log_format='%(asctime)s %(levelname)s [LicenseAlert] %(message)s', level=logging.DEBUG, log_name="licensealert.log", logger_name="licensealert"):
    """
    Setup a logger suitable for splunkd consumption
    """
    if logger is None:
        logger = logging.getLogger(logger_name)
    
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', log_name]), maxBytes=2500000, backupCount=5)
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    
    logger.handlers = []
    logger.addHandler(file_handler)
    
    logger.debug("Init Licensing logger")
    
    return logger


class LicenseAlert(ModularInput):

    title = "License Alert Manager"
    description = "License alert system which calculate index data from provided search against data store in license in core splunk, based upon show alert message"
    # This can be a saved search or modular inputs param but this may have security risks, hence search class param needs to overwrite 
    search = None
    # Application name
    name = None
    # Trial license version label
    trialLabel = None
    # Term license version label
    termLabel = None
    # Perpetual license version label
    perpetualLabel = None
    # Size unit of search result (values can be "BYTES", "KB", "MB","GB", "TB")
    searchResultUnit = None
    # License unit of size (values can be "BYTES", "KB", "MB","GB", "TB")
    licenseUnit = None
    # Unlimited license size in int
    unlimitedSize = None
    #App name space under which search will run
    namespace = None
    #nobody
    owner = 'nobody'

    ########################################################################
    # MESSAGES (These message needs to over write as per each application)
    # Ideal way to overwrite in inherit class that copy paste these messages
    # and replace XXX with App name 
    ########################################################################
    NO_LIC_MSG = 'You have no license for Splunk App for XXX, Contact sales for a license'
    EXPIRED_TRIAL_LIC_MSG = 'XXX App license has expired, please contact Sales'
    # Note: Below message expect one formated value which replace this with no of days left in the license, so make sure this is present in this message
    EXPIRED_TRIAL_LIC_MSG_IN_DAYS = 'You have {0} days remaining for your license of the Splunk App for XXX, Contact sales to get a license upgrade'
    EXPIRED_LIC_MSG = 'Your license to use the Splunk App for XXX is expired, Contact sales to get a license upgrade'
    EXCEED_BANDWIDTH_MSG = 'You have exceeded your daily licensing volume for Splunk App for XXX data'


    def __init__(self):
        args = [
                Field("log_level", "Logging Level", "This is the level at which the scheduler will log data.", required_on_create=False)
                ]
        scheme_args = {'title': self.title,
                       'description': self.description,
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "false"}
        ModularInput.__init__(self, scheme_args, args)


    def run(self, stanza):
        #Handle local authentication
        self.local_session_key = self._input_config.session_key
        self.local_server_uri = self._input_config.server_uri
        splunk.setDefault('sessionKey', self.local_session_key)
        if isinstance(stanza, list):
            logLevel = stanza[0].get('log_level', "WARN").upper()
        else:
            logLevel = stanza.get('log_level', "WARN").upper()
        if logLevel not in ["DEBUG", "INFO", "WARN","WARNING", "ERROR"]:
            logLevel = logging.WARN
            self.log = setupLogger(logger=None, log_format='%(asctime)s %(levelname)s [' + self.name + '] %(message)s', level=logLevel, log_name="licensealert.log", logger_name="licensealert")
            self.log.warn("logLevel was set to a non-recognizable level it has be reset to WARNING level")
        else:
            self.log = setupLogger(logger=None, log_format='%(asctime)s %(levelname)s [' + self.name + '] %(message)s', level=logLevel, log_name="licensealert.log", logger_name="licensealert")
            self.log.debug("logger reset with log level of %s", str(logLevel))

        #Check application name
        if self.name is None:
            self.log.error("LicenseAlert implementation %s did not have a application name specified, you must specify a application name.")
            raise NotImplementedError("All LicenseAlert implementations must specify a application.")

        if self.search is None:
            self.log.error("LicenseAlert implementation did not have a search specified, you must specify a search", str(self.name))
            raise NotImplementedError("All LicenseAlert implementations must specify a search which calculate index data for that application.")

        if self.trialLabel is None:
            self.log.error("LicenseAlert implementation %s did not have a application trial license label  specified, you must specify a trial license label.")
            raise NotImplementedError("All LicenseAlert implementations must specify a application.")

        if self.termLabel is None:
            self.log.error("LicenseAlert implementation %s did not have a application term license label  specified, you must specify a trial license label.")
            raise NotImplementedError("All LicenseAlert implementations must specify a application.")

        if self.perpetualLabel is None:
            self.log.error("LicenseAlert implementation %s did not have a application perpetual license label  specified, you must specify a trial license label.")
            raise NotImplementedError("All LicenseAlert implementations must specify a application.")

        try:
            unlimitedSize = int(self.unlimitedSize)
        except ValueError:
            self.log.error("LicenseAlert implementation %s did not have a valid unlimited_size specified, you must specify a valid value integer value for it", str(self.name))
            raise NotImplementedError("All LicenseAlert implementations must have a valid unlimited_size specified.")

        if self.searchResultUnit is None or self.searchResultUnit.upper() not in ["BYTES", "KB", "MB","GB", "TB"]:
            self.log.error("LicenseAlert implementation %s did not have a valid search_result_unit specified, you must specify a valid value form Bytes|KB|MB|GB|TB", str(self.name))
            raise NotImplementedError("All LicenseAlert implementations must have a valid search_result_unit specified.")

        if self.licenseUnit is None or self.licenseUnit.upper() not in ["BYTES", "KB", "MB","GB", "TB"]:
            self.log.error("LicenseAlert implementation %s did not have a valid license_unit specified, you must specify a valid value form Bytes|KB|MB|GB|TB", str(self.name))
            raise NotImplementedError("All LicenseAlert implementations must have a valid license_unit specified.")

        if ver.__version__ < '6.0':
            self.log.info("Splunk version:%s is less than 6.0 version, hence skipping the licenese check.",splunk.version.__version__)
            return
        # Perform search
        dataIndexed = self.getSearchResults()
        if dataIndexed is None:
            self.log.info("No data is indexed for app=%s or it is not configured", self.name)
            return 0
        self.log.info("Indexed data for app is %s", dataIndexed)
        # Convert search result in same license unit
        if self.searchResultUnit != self.licenseUnit:
            dataIndexed = self.convertToDataFormat(dataIndexed, self.searchResultUnit, self.licenseUnit)
            self.log.info("Indexed data for app to from format %s to %s, new value=%s", self.searchResultUnit, self.licenseUnit, dataIndexed)
        licenseInfo =  self.getLicenseInfo()
        messages = self.verifyLicense(licenseInfo, self.trialLabel, self.termLabel, self.perpetualLabel, dataIndexed, unlimitedSize)
        if isinstance(messages, list) and len(messages) > 0:
            for message in messages:
                Messenger.createMessage(message[0], self.local_session_key, namespace=self.namespace, owner=self.owner)
        elif isinstance(messages, list) and len(messages) == 0:
            # Valid licenses
            self.log.info(self.name + " has valid license.")
        else:
            Messenger.createMessage(messages, self.local_session_key, namespace=self.namespace, owner=self.owner)

    def verifyLicense(self, licenseInfo, trialLabel, termLabel, perpetualLabel, dataIndexed, unlimitedSize):
        '''
            Check license against indexed data.
            
            Note : If there is any term or perpetual license in licenseInfo list of tuple, it ignore trial license
            
            @param licenseInfo: List of tuple which hold label, expiration time (unix epoch time) and license size
            @param trialLabel: Trial license label
            @param termLabel: Term license label
            @param perpetualLabel: Perpetual license label
            @param dataIndexed : indexed data size
            @param unlimitedSize : license unlimited size
            
            @return: Messages if license is not valid or trial license remaining time frame or None  
        '''
        Messages = []
        # No licenses
        if licenseInfo is None or len(licenseInfo) == 0:
            self.log.info("No license is found")
            return self.NO_LIC_MSG

        #Check licenses labels
        labels = [ x[0] for x in licenseInfo]
        isTrial = None
        if termLabel in labels or perpetualLabel in labels:
            self.log.info("Found term or perpetual license")
            isTrial = False
        elif trialLabel in labels:
            self.log.info("Found trial license")
            isTrial = True
        else:
            # Invalid license label
            self.log.error("Invalid license(s) labels=%s", labels)
            return self.NO_LIC_MSG
        # Check data vol
        isAllLicExperied = True
        if isTrial:
            for lic in licenseInfo:
                if lic[0] != trialLabel:
                    continue
                # Assuming expiry time will be Unix epoch time
                timediff = int(lic[1]) - int(time.time())
                self.log.debug("Time difference :"+ str(timediff))
                if timediff > 0:
                    isAllLicExperied = False
                    days =  self._checkDaysInLicense(timediff)
                    if days is None:
                        self.log.debug("Trial license has enough days, so no action is taken.")
                    else:
                        Messages.append((self.EXPIRED_TRIAL_LIC_MSG_IN_DAYS.format(days), lic[0]))
                else:
                    self.log.info("There is expired trial license. expiration_time=%s, label=%s", lic[1], lic[0])
            if isAllLicExperied:
                # Expired all Trial license 
                return self.EXPIRED_TRIAL_LIC_MSG
        else:
            # Non Trial license
            licSize = 0
            licSizeUnlimited = False
            for lic in licenseInfo:
                if lic[0] == trialLabel:
                    continue
                # Expiry time will be Unix epoch time
                timediff = int(lic[1]) - int(time.time())
                self.log.debug("Time difference :"+ str(timediff))
                if timediff > 0:
                    days =  self._checkDaysInLicense(timediff)
                    if days is None :
                        self.log.debug("License has enough days, so no action is taken.")
                    else:
                        Messages.append((self.EXPIRED_TRIAL_LIC_MSG_IN_DAYS.format(days), lic[0]))

                    isAllLicExperied = False
                    # Expecting unlimited 
                    if lic[2] >= unlimitedSize:
                        self.log.info('Found unlimited license size=%s, expiration_time=%s, label=%s', lic[2], lic[1], lic[0])
                        licSizeUnlimited = True
                    else:
                        self.log.info('Found term license size=%s, expiration_time=%s, label=%s', lic[2], lic[1], lic[0])
                        licSize = licSize + int(lic[2])
                else:
                    self.log.info('Term or perpetual license has been expired license volume=%s, expiration_time=%s, label=%s', lic[2], lic[1], lic[0])
            if isAllLicExperied:
                # Expired all licenses
                self.log.debug("All licenses are expired.")
                return self.EXPIRED_LIC_MSG
            if not licSizeUnlimited:
                if licSize <= dataIndexed:
                    self.log.info("Exceeded the indexed volume")
                    # Append with expiry licenses
                    Messages.append((self.EXCEED_BANDWIDTH_MSG, ''))
        return Messages

    def _checkDaysInLicense(self, timediff, daysThreshold=7):
        '''
            @param  timediff: time in seconds
            @param  daysThreshold: threshold days after that message is shown
            @return None if days is gather than threshold time else days left out
        '''
        days = datetime.timedelta(seconds = timediff).days
        self.log.info("License is valid. Number of days=%s left in trial license ", days)
        # Week or less
        if days > daysThreshold:
            return None
        else:
            return days

    def convertToDataFormat(self, value, sourceFormatType, dstFormatType):
        '''
            Accepting value in bytes and convert into BYTES KB, MB, GB and TB format
        '''
        if value is None:
            return value
        if sourceFormatType.upper() == dstFormatType.upper():
            return value
        else:
            # Why does python does not support enum, I would have done with better way if python support enum before 3.5
            if sourceFormatType.upper() == 'BYTES' and dstFormatType.upper() in ['KB', 'MB', 'GB', 'TB']:
                sourceFormatType = 'KB'
                return self.convertToDataFormat(value/1024.0, sourceFormatType, dstFormatType)
            if sourceFormatType.upper() == 'KB' and dstFormatType.upper() in ['MB', 'GB', 'TB']:
                sourceFormatType = 'MB'
                return self.convertToDataFormat(value/1024.0, sourceFormatType, dstFormatType)
            if sourceFormatType.upper() == 'MB' and dstFormatType.upper() in [ 'GB', 'TB']:
                sourceFormatType = 'GB'
                return self.convertToDataFormat(value/1024.0, sourceFormatType, dstFormatType)
            if sourceFormatType.upper() == 'GB' and dstFormatType.upper() in ['TB']:
                sourceFormatType = 'TB'
                return self.convertToDataFormat(value/1024.0, sourceFormatType, dstFormatType)

            # Higher to lower conversion
            if sourceFormatType.upper() == 'TB' and dstFormatType.upper() in ['GB', 'MB', 'KB', 'BYTES']:
                sourceFormatType = 'GB'
                return self.convertToDataFormat(value*1024, sourceFormatType, dstFormatType)
            if sourceFormatType.upper() == 'GB' and dstFormatType.upper() in ['MB', 'KB', 'BYTES']:
                sourceFormatType = 'MB'
                return self.convertToDataFormat(value*1024, sourceFormatType, dstFormatType)
            if sourceFormatType.upper() == 'MB' and dstFormatType.upper() in ['KB', 'BYTES']:
                sourceFormatType = 'KB'
                return self.convertToDataFormat(value*1024, sourceFormatType, dstFormatType)
            if sourceFormatType.upper() == 'KB' and dstFormatType.upper() in ['BYTES']:
                sourceFormatType = 'BYTES'
                return self.convertToDataFormat(value*1024, sourceFormatType, dstFormatType)


    def getLicenseInfo(self):
        '''
            @param appName: App name which appears in licenses
            @return a list of tuple (label, expirationTime, label), if there is no license, it return empty list
        '''
        uri = self.local_server_uri + "/services/licenser/licenses"
        response, contents = simpleRequest(path=uri, getargs={'output_mode': "json", "count":2000}, sessionKey=self.local_session_key, method='GET')
        self.log.debug("Licensing endpoint response:%s and content:%s", response, contents)
        if response.status != 200:
            self.log.error("Failed to get data from server info end point=%s", uri)
            raise splunk.SplunkdException("Failed to get data from server info end point={0}".format(uri))
        # Get Addons license volumes
        licenseInfo = []
        for entry in json.loads(contents).get('entry', None):
            content = entry.get('content', None)
            if content is None:
                continue
            addOns  = content.get('add_ons', None)
            if addOns is None:
                #No add on in 
                continue
            for app, value in addOns.iteritems():
                self.log.debug("Found one addon :%s, values :%s", app, value)
                if app == self.name:
                    #Get size
                    size = int(value.get('size', 0))
                    expTime = content.get('expiration_time', None)
                    label = content.get('label', None)
                    licenseInfo.append((label, expTime, size))
        self.log.debug("License information:%s", licenseInfo)
        return licenseInfo

    # Ran the give search and get the results of data usage
    def getSearchResults(self):
        '''
            Run search and get indexed data value       
            @return: If search successful return first result otherwise none
            
        '''
        #Get results
        self.log.info("Running search ...")
        if not self.search.startswith('search'):
            search = 'search ' + self.search
        else:
            search = self.search
        results = splunkSearch.searchOne(search, hostPath=self.local_server_uri, sessionKey=self.local_session_key, namespace=self.namespace, owner=self.owner)
        self.log.debug("Search results:%s", results)
        if results is not None:
            totalIndexedData = 0.0
            for value in results.values():
                totalIndexedData = totalIndexedData + float(str(value))
            return totalIndexedData if totalIndexedData > 0 else None
        else:
            self.log.info("Failed to get any results for the search={0}".format(search))
            return None
