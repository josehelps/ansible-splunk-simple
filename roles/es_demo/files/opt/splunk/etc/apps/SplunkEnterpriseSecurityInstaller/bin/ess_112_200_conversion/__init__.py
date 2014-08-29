import copy
import logging
import logging.handlers
import os
import stat
import csv
import re

APP_NAME_LOWER_PREFIX = "es"

## This logger instance name will be shared with the controller class
LOGGER_NAME = APP_NAME_LOWER_PREFIX + '_installer_controller'

def setup_logger(level):
    """
    Setup a logger for the controller
    """
    logger = logging.getLogger(LOGGER_NAME)
    
    return logger

# Setup the handler
logger = setup_logger(logging.INFO)


class ReviewStatusProcessor():

    def __init__(self, confWriter, basePath, workspacePath):
        """
        @param confWriter: function to write conf files
        @param basePath: home path to Splunk apps, typically $SPLUNK_HOME/etc/apps
        @param workspacePath: path to the upgrader workspace
        """
        self.confWriter = confWriter
        self.basePath = basePath
        self.workspacePath = workspacePath


    def handleReviewStatuses(self):
        '''
        @return: numeric to string label mapping/dictionary
        Determine if there were any custom review statuses present in 1.1.2 install
        Migrate those to 2.0 by converting custom statuses within review_statii.csv -> reviewstatuses.conf
        Also create transition capabilities for those statuses
        Return the numeric to string label mapping
        '''
        labelToNumberMap = {}
        
        ## The "new" review_statii.csv.default that comes with 1.1.2 version release
        ## The upgrader should ship with this old default, it's possible the user can modify it!!
        defaultCsvFH = open(os.path.join(self.basePath, "SA-ThreatIntelligence","lookups","review_statii.csv.default"), "rU")
        
        if os.path.exists(os.path.join(self.basePath, "SA-ThreatIntelligence","lookups","review_statii.csv")):
            ## Get current install's review statuses
            with open(os.path.join(self.basePath, "SA-ThreatIntelligence","lookups","review_statii.csv"), "rU") as statusCsvFH:
                statusCsvList = statusCsvFH.readlines()

            chompedStatusCsvList = []
            for status in statusCsvList:
                chompedStatusCsvList.append(status.strip())
            
            defaultCsvList = defaultCsvFH.readlines()
            chompedDefaultCsvList = []
            for status in defaultCsvList:
                chompedDefaultCsvList.append(status.strip())
    
            ## 1.1.2 reviewStatuses were single column statuses so we can treat each line as a new status
            ## custom review statuses = current statuses - default statuses
            diffStatuses = list(set(chompedStatusCsvList) - set(chompedDefaultCsvList))
    
            if len(diffStatuses) == 0:
                # there are no new statuses, no translation needed
                pass
            else:
    
                ## Get the new default reviewstatuses.conf to determine the next numeric code to use for any migrated review statuses from 1.1.2
                try:
                    newReviewStatusConfFH = open(os.path.join(self.basePath, self.workspacePath, "SA-ThreatIntelligence","default","reviewstatuses.conf"), "rU")
                    defaultStatusConfList = newReviewStatusConfFH.readlines()
                except Exception as e:
                    # let the caller handle this
                    raise
                
                newReviewStatusConfFH.close()
                
                ## counter for the current number of default ES 2.0 statuses
                countDefaultStatuses = 0
                regexStanzaHeader = re.compile("^\[.*\]$")
                
                for line in defaultStatusConfList:
                    if re.search(regexStanzaHeader, line):
                        countDefaultStatuses = countDefaultStatuses + 1
    
                ## there are new statuses that we need to translate to a local conf file
                labelToNumberMap = self.writeNewReviewStatuses(countDefaultStatuses, diffStatuses)
                
                ## for each custom status, we must assign the TO and FROM status transistions
                self.writeThreatIntelAuthorize(countDefaultStatuses, len(diffStatuses))
        else:
            ## There are no custom review statuses to convert - NO review_statii.csv
            pass

        logger.info("func:handleReviewStatuses()|" + "labelToNumberMap:" + str(labelToNumberMap))
        return labelToNumberMap


    def writeNewReviewStatuses(self, statusCount, statusList):
        '''
        @param statusCount: count of review statuses within default reviewstatuses.conf 
        @param statusList: list of 1.1.2 status labels
        
        Given the a list of the count within 2.0 default reviewstatuses.conf and a list of 1.1.2 custom status labels
        transform and write out the customs status labels with respective numeric code
        
        Example: 
        2.0 default/reviewstatuses.conf
        [0] -> new
        [1] -> pending
        [2] -> resolved
        
        1.1.2 custome review statuses: myStatus-1,  myStatus-2
        
        Output
        local/reviewstatuses.conf
        [3] -> myStatus-1
        [4] -> myStatus-2
        '''
        stanzas = {}
        labelToNumberMap = {}
        
        for status in statusList:
            stanzaBody = {"disabled":"0", "selected":"False", "hidden":"False"}
            stanzaBody["label"] = status.rstrip()
            stanzaBody["description"] = status.rstrip()
            stanzas[statusCount] = stanzaBody
            labelToNumberMap[status.rstrip()] = statusCount
            statusCount += 1

        self.confWriter(os.path.join(self.basePath, self.workspacePath, "SA-ThreatIntelligence", "local", "reviewstatuses.conf"), stanzas)
        
        logger.info("func:writeNewReviewStatuses()|" + "conf:" + str(os.path.join(self.basePath, self.workspacePath, "SA-ThreatIntelligence", "local", "reviewstatuses.conf")) + "|stanzas:" + str(stanzas))
        return labelToNumberMap


    def writeThreatIntelAuthorize(self, defaultStatusCount, newCustomStatusCount):
        '''
        @param defaultStatusCount: count of existing (default) statuses
        @param newCustomStatusCount: count of custom statuses in 1.1.2
        
        Generate and write out authorize.conf for SA-ThreatIntelligence
        For each custom review status migrated from 1.1.2 -> 2.0 we need to create To and FROM transitions
        - create transitions from all existing statuses to new status
        - create transitions from new status to all existing statuses
        
        For new transition created, assign default capability for users: "role_ess_admin", "role_ess_analyst"
        
        defaultStatusCount: the count of default 2.0 review statuses 
        newCustomStatusCount the count of 'new' 1.1.2 statuses to be migrated
        '''

        stanzasToNew = {}
        stanzasFromNew = {}
        stanzaBody = {"disabled":"0"}
        
        stanzasUserCapabilities = {}
        userRoles = ["role_ess_admin", "role_ess_analyst"]
        userTransitions = []
        userStanzaBody = {}
        
        toNewCount = defaultStatusCount
        
        for x in range(newCustomStatusCount):
            ## Transitions from existing TO new status
            for i in range(toNewCount):
                transition = "transition_reviewstatus-" + str(i) + "_to_" + str(toNewCount)
                userTransitions.append(transition)
                capability = "capability::" + transition
                stanzasToNew[capability] = stanzaBody

            ## Transitions from new status to existing
            for i in range(1,toNewCount):
                transition = "transition_reviewstatus-" + str(toNewCount) + "_to_" + str(i)
                userTransitions.append(transition)
                capability = "capability::" + transition
                stanzasFromNew[capability] = stanzaBody

            ## Add transition capabilities for the default users: ess_admin and ess_user
            for uR in userRoles:
                for uT in userTransitions:
                    userStanzaBody[uT] = "enabled"
                stanzasUserCapabilities[uR] = userStanzaBody

            toNewCount += 1

        self.confWriter(os.path.join(self.basePath, self.workspacePath, "SplunkEnterpriseSecuritySuite", "local", "authorize.conf"), stanzasUserCapabilities)
        self.confWriter(os.path.join(self.basePath, self.workspacePath, "SA-ThreatIntelligence", "local", "authorize.conf"), stanzasToNew)
        self.confWriter(os.path.join(self.basePath, self.workspacePath, "SA-ThreatIntelligence", "local", "authorize.conf"), stanzasFromNew)
        
        logger.info("func:writeThreatIntelAuthorize()|" + "conf:" + str(os.path.join(self.basePath, self.workspacePath, "SplunkEnterpriseSecuritySuite", "local", "authorize.conf")) + "|stanzas:" + str(stanzasUserCapabilities))
        logger.info("func:writeThreatIntelAuthorize()|" + "conf:" + str(os.path.join(self.basePath, self.workspacePath, "SA-ThreatIntelligence", "local", "authorize.conf")) + "|stanzas:" + str(stanzasToNew))
        logger.info("func:writeThreatIntelAuthorize()|" + "conf:" + str(os.path.join(self.basePath, self.workspacePath, "SA-ThreatIntelligence", "local", "authorize.conf")) + "|stanzas:" + str(stanzasFromNew))
        return stanzasUserCapabilities, stanzasToNew, stanzasFromNew

class CsvUpgradeProcessor():

    def __init__(self, basePath, workspacePath):
        """
        @param basePath: home path to Splunk apps, typically $SPLUNK_HOME/etc/apps
        @param workspacePath: path to the upgrader workspace
        """
        self.basePath = basePath
        self.workspacePath = workspacePath

    def generateIncidentReviewFieldSub(self, customStatusLabelMap):
        '''
        @param customStatusLabelMap: numeric to string label mapping/dictionary - output from handleReviewStatuses
        Combine the retrieved custom review statuses with the default OTB mappings
        Returns a dictionary representing custom and default review statuses mapped for the status field for incident_review.csv

            Notable Status mappings
            1.1.2         2.0
            unreviewed -> new:1
            reviewed   -> resolved:4
            closed     -> closed:5
        '''
        defaultlabelToNumberMap = {"unreviewed":"1","reviewed":"4","closed":"5"}
        statusLabelMap = dict(customStatusLabelMap.items() + defaultlabelToNumberMap.items())

        logger.info("func:generateIncidentReviewFieldSub()|" + "map:" + str(statusLabelMap))
        return {"fieldName":"status", "fieldMap":statusLabelMap}
    

    def handleUpgradeCSV(self, domain, csvFilename, fieldSub=None):
        '''
        @param domain: the target domain app (SA) that contains the csv to upgrade
        @param csvFilename: name of the csv to upgrade
        @param fieldSub: dictionary used to replace any row value with a new one
        
        Side-effect:
        
        Transform old CSV to new CSV format as dictated by the .default file
        New columns are added to the header and empty string values filled into the rows
        fieldSub parameter is a dictionary used to replace any row value with a new one
        fieldSub = { "fieldName":someName, "fieldMap":{ oldVal-1 : newVal-1, oldVal-2 : newVal-2, oldVal-3 : newVal-3 } }
        '''
    
        LOOKUPS_PATH = "lookups"
    
        try:
            outputCsvPath = os.path.join(self.basePath, self.workspacePath, domain, LOOKUPS_PATH, csvFilename)
            # touch/create a blank outputCSV
            open(outputCsvPath, 'w').close()
            
            # Make output CSV file writeable
            origACL = os.stat(outputCsvPath).st_mode    
            plusWriteACL = origACL|stat.S_IWRITE
            os.chmod(outputCsvPath,plusWriteACL)
        except Exception as e:
            #let the caller handle this
            raise

        ## get the column headers from the existing CSV
        with open(os.path.join(self.basePath, domain, LOOKUPS_PATH, csvFilename), "rU") as oldCsvFH:
            oldReader = csv.reader(oldCsvFH)
            oldHeader = []
            oldFirst = True
            for row in oldReader:
                if oldFirst:
                    oldHeader = row
                    oldFirst = False

        logger.info("func:handleUpgradeCSV()|" + "oldCsvHeaders:" + str(oldHeader))

        # get the column headers from the new default CSV
        with open(os.path.join(self.basePath, self.workspacePath, domain, LOOKUPS_PATH, csvFilename + ".default"), "rU") as newDefaultCsvFH:
            newReader = csv.reader(newDefaultCsvFH)        
            newHeader = []
            newFirst = True
            for row in newReader:
                if newFirst:
                    newHeader = row
                    newFirst = False
        
        logger.info("func:handleUpgradeCSV()|" + "newCsvHeaders:" + str(newHeader))
        
        ## Get any extra (custom) fields from the old CSV and append to the new default headers (union)
        ## this ensures we retain any custom columns added by the user
        customHeaders = list(set(oldHeader) - set(newHeader))
        fieldnames = newHeader + customHeaders
        logger.info("func:handleUpgradeCSV()|" + "mergedCsvHeaders:" + str(fieldnames))
        
        # We need to put the new header row into the output and the DictWriter object requires a dictionary instead of a list
        outputHeader = {}
        for field in fieldnames:
            outputHeader[field] = field
        
        # Magic done here - essentially the missing columns are filled in by the restval='' paramter.
        # If the old CSV has a field 
        with open(outputCsvPath,"w") as outputCsvFH:
            csvwriter = csv.DictWriter(outputCsvFH, fieldnames, delimiter=',', restval='')
            csvwriter.writerow(outputHeader)

            ## Get new filehandle to the old CSV.  Its lines were consumed with the previous reader
            with open(os.path.join(self.basePath, domain, LOOKUPS_PATH, csvFilename), "rU") as oldCsvFH2:
                ## read rows from the old CSV
                for row in csv.DictReader(oldCsvFH2):
                
                    ## perform any field mappings, if needed, as specified by fieldSub parameter
                    if fieldSub is not None:
                    
                        fieldName = fieldSub["fieldName"]
                        fieldMap = fieldSub["fieldMap"]
                        row[fieldName] = fieldMap[row[fieldName]]
            
                    ## write out row from old CSV to the new output CSV
                    csvwriter.writerow(row)


class GovernanceProcessor():

    def __init__(self, basePath, workspacePath):
        """
        @param basePath: home path to Splunk apps, typically $SPLUNK_HOME/etc/apps
        @param workspacePath: path to the upgrader workspace
        """
        self.basePath = basePath
        self.workspacePath = workspacePath
        self.domainMap = {
            "Access":"SA-AccessProtection", "Audit":"SA-AuditAndDataProtection",
            "Endpoint":"SA-EndpointProtection", "Identity":"SA-IdentityManagement",
            "Network":"SA-NetworkProtection", "Threat":"SA-ThreatIntelligence"
        }

        ## ess 112 all correlation search governance defined in SA-ThreatIntelligence/local/savedsearches.conf
        self.srcGovFilePath = os.path.join("SA-ThreatIntelligence", "local", "savedsearches.conf")

        ## es 2.2.x defined in <domain>/local/governance.conf
        self.localSubPath = "local"
        self.govFileSubPath = "governance.conf"

        ## action.summary_index.<governance>_control = #
        self.govRE = re.compile("action\.summary_index\.(\w+)_control")

        ## Access - Insecure Or Cleartext Authentication - Rule
        self.corrSrchRE = re.compile("(\w+)\s+-\s+([\w|\s]+)\s+-\s+Rule")
        self.corrSrchRE_group_domain = 1
        self.corrSrchRE_group_name = 2
        
    def getExistingGovernance(self, confReader, targetFilePath):
        """
        @param confReader: function used to read conf files into dictionaries
        @return: map of search name to governance definition
        Locate saved searches that may have governance defined.
        """
        searchToGovMap = {}


        ## Look for governance definitions among the saved search conf
        confDict = confReader(os.path.join(self.basePath, targetFilePath))

        for stanza, body in confDict.iteritems():
            govToControlMap = {}

            for attName, attVal in body.iteritems():                
                govMatch = re.search(self.govRE, attName)
                
                if govMatch:
                    ## save off the governance-name (key) and control-ID (value)
                    govToControlMap[govMatch.group(1)] = attVal

            if len(govToControlMap) > 0:
                searchToGovMap[stanza] = govToControlMap

        logger.info("func:getExistingGovernance()|searchToGovMap:" + str(searchToGovMap))

        return searchToGovMap

    def writeNewGovernance(self, confWriter, searchToGovMap):
        """
        @param confWriter: function used to write conf files from dictionaries
        @param govMap: map of saved searches to governance controls that need to be written out
        side-effect: existing 112 governance controls are written out in new format
        
        @return: map of domain name to correlation search file contents to write
        
        { <domainNameLong-1> : 
            { <search-1> : {att-1:val-1, att-2:val-2, att-3:val-3},
              <search-2> : {att-1:val-1, att-2:val-2, att-3:val-3}
            } ,
          
          <domainNameLong-2> :  
            { <search-1> : {att-1:val-1, att-2:val-2, att-3:val-3},
              <search-2> : {att-1:val-1, att-2:val-2, att-3:val-3}
            }        
        }

        Output:
        
        [<DOMAIN> - <SEARCHNAME> - Rule]
        compliance.0.governance = <governance>
        compliance.0.control = <control#>
        compliance.1.governance = pci
        compliance.1.control = 4.1.1

        """
        resultDomainConfMap = {}

        for searchName, govToControlMap in searchToGovMap.iteritems():
            
            csMatch = re.search(self.corrSrchRE, searchName)

            ## this is a correlation search by naming convention <domain> - <rule_name> - Rule
            if csMatch:
                
                ## init confDict for given domain name
                domainConfDict = {}
                domainNameShort = csMatch.group(self.corrSrchRE_group_domain)

                ## determine domain name
                if domainNameShort in self.domainMap:
                
                    domainNameLong = self.domainMap[domainNameShort]
                    tempCounter = 0

                    # setdefault returns a reference to the original dictionary and can update it on the fly
                    tempDict = domainConfDict.setdefault(searchName, {})
                    
                    for govName, controlNum in govToControlMap.iteritems():
                        ## ESS 2.2.x governance format
                        govStr = "compliance.%s.governance" % tempCounter
                        ctlStr = "compliance.%s.control" % tempCounter
                        tempDict[govStr] = govName
                        tempDict[ctlStr] = controlNum
                        tempCounter += 1

                    resultDomainConfMap[domainNameLong] = domainConfDict
                    ## ADD THE MAP BACK TO THE OUTPUT
                
                else:
                    ## process non domain correlation search
                    pass

        logger.info("func:writeNewGovernance()|resultDomainConfMap:" + str(resultDomainConfMap))

        for domainName, govStanzas in resultDomainConfMap.iteritems():
            govFP = os.path.join(self.basePath, domainName, self.localSubPath)
            try:
                os.makedirs(govFP)
            except OSError:
                ## path already exists
                pass

            confWriter(os.path.join(govFP, self.govFileSubPath), govStanzas, append=True)


    def removeOldGovernance(self, confReader, confWriter, targetFilePath):
        """
        @param confReader: function used to read conf files into dictionaries
        @param confWriter: function used to write conf files into dictionaries
        @param targetFilePath: relative path base of self.basePath, to the target conf file
        Remove any governance attributes from the old file where is was defined
        """
        ## Look for governance definitions among the saved search conf
        confDict = confReader(os.path.join(self.basePath, targetFilePath))

        ## dictionary to hold the non-governance attributes
        ## the original file will be over-written with this; essentially deprecating the governance settings
        nonGovDict = copy.deepcopy(confDict)
        
        for stanza, body in confDict.iteritems():
            for attName, attVal in body.iteritems():                
                govMatch = re.search(self.govRE, attName)
                if govMatch:
                    
                    ## remove this governance setting from the original dictionary
                    del nonGovDict[stanza][attName]  

        ## remove any empty stanzas
        for stanza, body in nonGovDict.items():
            if len(body) < 1:
                del nonGovDict[stanza]

        confWriter(os.path.join(self.basePath, targetFilePath), nonGovDict, append=False)
        logger.info("func:removeOldGovernance()|nonGovDict:" + str(nonGovDict))


def convertReviewStatuses(confWriter, basePath, workspacePath):
    """
    Essentially the "run" function for the conversions
    
    @param confWriter: function to write conf files
    @param basePath: home path to Splunk apps, typically $SPLUNK_HOME/etc/apps
    @param workspacePath: path to the upgrader workspace
    
    Side-effect:
      - Converts the 1.1.2 review status CSV into an equivalent .conf
      - Converts the 1.1.2 incident_review.csv to use the new review statuses in the .conf format
    """
    rsProc = ReviewStatusProcessor(confWriter, basePath, workspacePath)
    csvProc = CsvUpgradeProcessor(basePath, workspacePath)
    labelToNumberMap = rsProc.handleReviewStatuses()    
    incidentReviewFieldSub = csvProc.generateIncidentReviewFieldSub(labelToNumberMap)
    csvProc.handleUpgradeCSV("SA-ThreatIntelligence", "incident_review.csv", fieldSub=incidentReviewFieldSub)
    csvProc.handleUpgradeCSV("SA-IdentityManagement", "assets.csv")
    

def convertGovernanceControls(confReader, confWriter, basePath, workspacePath):
    """
    @param confWriter: function to write conf files
    @param basePath: home path to Splunk apps, typically $SPLUNK_HOME/etc/apps
    @param workspacePath: path to the upgrader workspace

    Side-effect:
      - Converts the 1.1.2 governance into an equivalent governance.conf
    """
    gProc = GovernanceProcessor(basePath, workspacePath)
    searchToGovMap = gProc.getExistingGovernance(confReader, gProc.srcGovFilePath)
    gProc.writeNewGovernance(confWriter, searchToGovMap)
    gProc.removeOldGovernance(confReader, confWriter, gProc.srcGovFilePath)
    
    csvProc = CsvUpgradeProcessor(basePath, workspacePath)
    csvProc.handleUpgradeCSV("SA-ThreatIntelligence", "governance.csv")

if __name__ == "__main__":
    print "TEST-MAIN"
