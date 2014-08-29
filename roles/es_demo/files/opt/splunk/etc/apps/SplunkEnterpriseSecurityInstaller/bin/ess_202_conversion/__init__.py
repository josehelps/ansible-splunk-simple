import itertools
import logging
import logging.handlers
import os
import re
import shutil
import splunk.clilib.bundle_paths as bp
import xml.dom.minidom
import xml.parsers

LOGGER_NAME = 'es_installer_controller'

def setup_logger(level):
    """
    Setup a logger for the controller
    """
    logger = logging.getLogger(LOGGER_NAME)
    
    return logger

# Setup the handler
logger = setup_logger(logging.INFO)

class CustomConfProcessor():

    def getBasePath(self):
        """
        Returns the base path of Splunk instance - $SPLUNK_HOME/etc/apps
        """
        return os.path.join(bp.get_base_path())


    def getConfDicts(self, confReadFunc, filePathList):
        """
        input:
        - confReadFunc: a generic .conf reader function that returns the contents in dictionary format
        - filePathList:  the absolute paths to the conf files
        
        output: a single n-nested dictionary containing the contents of all conf files in list
        """
        confDict = {}
        
        for fp in filePathList:
            contents = confReadFunc(fp)
            confDict[fp]=contents
        
        logger.info("func:getConfDicts():output|" + str(confDict))
        return confDict

    def getFilePaths(self, basePath, inclusionAppFilters, inclusionFileFilters, exclusionFilters, isLocal=True):
        """
        input:
        - basePath: starting location for directory traversal
        - inclusionAppFilters: a regex that filters paths by app folder name
        - inclusionFileFilters: a regex that filters paths by filename
        - isLocal: boolean indicating which branch to crawl - default vs. local
        
        output: list of absolute paths that conform to the filters supplied 
        
        This traverses the app folders looking for particular files within a subset of apps.
        """

        pathList = []
        for root, dirs, files in os.walk(basePath):
            for f in files:
                fullPath = os.path.join(root,f)
                if re.search(inclusionAppFilters, fullPath) and re.search(inclusionFileFilters, fullPath):
                    if not re.search(exclusionFilters, fullPath):                    
                        if isLocal:
                            if "local" in fullPath:
                                pathList.append(fullPath)
                        elif not isLocal:
                            if "default" in fullPath:
                                pathList.append(fullPath)
                else:
                    pass

        logger.info("func:getFilePaths():output|" + str(pathList))
        return pathList
                    

    def filterStanzas(self, confDict, stanzaRE=None, paramNameRE=None, paramValueRE=None):
        """
        Given a dictionary of conf files, this function filters and retains only those stanzas meeting the filter criteria
        Example: Reduce the stanzas down to only a subset i.e. - [<domain> - <name> - TSIDX Gen]
        
        input:
        - confDict: the dictionary containing the subset of conf files to examine
        - stanzaRE: regex of stanzaName to retain within the confDict
        - paramNameRE: stanza parameter name to search for
        - paramValueRE: stanza parameter value to search for
        
        *** The usage of stanzaRE should be mutually exclusive of the paramNameRe and paramValueRE arguments
        
        output: the filtered confDict
        """
        result = {}
        for fileName, stanzas in confDict.items():
            matchStanzas = []
        
            for stanzaName in stanzas.keys():
                
                # filter based on stanza names
                if (stanzaRE is not None) and (paramNameRE is None) and (paramValueRE is None):
                    if re.search(stanzaRE, stanzaName):
                        matchStanzas.append(stanzaName)
                    
                # filter based on param key-values
                elif (stanzaRE is None) and (paramNameRE is not None) and (paramValueRE is not None):

                    try:
                        foundParam = [paramName for paramName in stanzas[stanzaName].keys() if re.search(paramNameRE, paramName)]
                        if any(foundParam):
                            if re.search(paramValueRE, stanzas[stanzaName][foundParam[0]]):
                                matchStanzas.append(stanzaName)
                    except KeyError:
                        # no paramNameRE found
                        pass
                    
                else:
                    # no filters set, nothing to list
                    pass    
            
            # only mark this file if it contains stanzas
            if matchStanzas:
                result[fileName] = matchStanzas

        logger.info("func:filterStanzas():output" + str(result))
        return result


    def extractStanzaNamesFromDict(self, stanzaMap):
        """
        input: confDict of savedsearches.conf files to reformat
        output: list of savedsearch names, processed according to regex 
        
        Example: [<domain> - <name> - <search type>] --> [<domain> - <name>]
        """
        patternRE = re.compile("^([^-]+\s+-\s+[^-]+\s+-\s+)\w+", re.DOTALL)
        valueList = stanzaMap.values()
        listStanzaNames = list(itertools.chain(*valueList))
        
        listStanzaNames[:] = [re.search(patternRE,elem).group(1) for elem in listStanzaNames]

        logger.info("func:extractStanzaNamesFromDict():input-stanzaMap" + str(stanzaMap))        
        logger.info("func:extractStanzaNamesFromDict():output-listStanzaNames" + str(listStanzaNames))
        return listStanzaNames
        

    def compareStanzaNames(self, fileStanzaMap, stanzaNameFilterList):
        """
        input: 
        - fileStanzaMap: A dictionary containing the filenames as keys and a list of its stanza as values i.e. {filename:[stanzas] ... , filename:[stanzas]}
        - stanzaNameFilterList: A list of stanzasNames to compare against 
        output: {files:[stanzas]}
    
        Using the stanza filters, we only keep matching stanzaNames supplied 
        """
        result = {}
        for filename, targetStanzas in fileStanzaMap.iteritems():
            matchStanzas = []

            for sourceStanzaName in stanzaNameFilterList:
                
                for target in targetStanzas:                
                    if sourceStanzaName in target:
                        # we have a match
                        matchStanzas.append(target)

            if any(matchStanzas):
                result[filename] = matchStanzas
        logger.info("func:compareStanzaNames():input-fileStanzaMap::" + str(fileStanzaMap))
        logger.info("func:compareStanzaNames():input-stanzaNameFilterList::" + str(stanzaNameFilterList))
        logger.info("func:compareStanzaNames():output-result::" + str(result))
        return result


class CustomXMLProcessor():

    LOCAL_NAV_PATH = os.path.join("local", "data", "ui", "nav", "default.xml")
    VIEW_TAG = "view"
    NAME_ATT = "name"
    
    def getDOMFromFile(self, path):
        """
        input: path to xml file
        output: XML DOM
        """
        try:
            doc = xml.dom.minidom.parse(path)
            return doc.documentElement
        except xml.parsers.expat.ExpatError as e:
            logger.error("func:getDOMFromFile()|malformed XML")
            raise
        

    def getAttVals(self, root, tag, att):
        """
        input:
          root - parsed xml document
          tag - name of tag
          att - attribute name
        output: list of attribute values for given tag
        """
        try:
            attValList = []
            elems = root.getElementsByTagName(tag)
            for e in elems:
                attVal = e.getAttribute(att)
                if len(attVal) > 0:
                    attValList.append(attVal)
                else:
                    pass

            logger.info("func:getAttVals()|output::attValList=%s" % str(attValList))
            return attValList
        except Exception as e:
            raise e


    def checkCustomLiteNavXML(self, navPath, targetTag, targetAtt):
        """
        input:
          appName - the app to which we check if a custom navigation exists
        output: dictionary of instances of lite view found per navigation (default.xml) file
        """
        outputList = []
        results = {}
        
        try:
            if os.path.exists(navPath):
                root = self.getDOMFromFile(navPath)
                attValList = self.getAttVals(root, targetTag, targetAtt)
                
                for attVal in attValList:
                    if "lite" in attVal:
                    
                        outputList.append(attVal)
            else:
                #no custom nav
                pass
                
            if len(outputList) > 0:
                results[navPath] = outputList
            else:
                ## don't report anything
                pass

        except xml.parsers.expat.ExpatError as e:
            logger.error("func:checkCustomLiteNavXML()|navigation file is malformed, failed to check conflicts")
            results[navPath] = ["ERROR: navigation file is malformed, failed to check conflicts"]
            return results
        
        except Exception as e:
            raise

        logger.info("func:checkCustomLiteNavXML()|input::navPath=%s, targetTag=%s, targetAtt=%s" % (navPath, targetTag, targetAtt))
        logger.info("func:checkCustomLiteNavXML()|output::results=%s" % str(results))
        return results


class GovernanceProcessor():

    def __init__(self, basePath, workspacePath):
        """
        @param basePath: home path to Splunk apps, typically $SPLUNK_HOME/etc/apps
        @param workspacePath: path to the upgrader workspace
        """
        self.basePath = basePath
        self.workspacePath = workspacePath
        self.domainList = [
            "SA-AccessProtection", "SA-AuditAndDataProtection",
            "SA-EndpointProtection", "SA-IdentityManagement",
            "SA-NetworkProtection", "SA-ThreatIntelligence",
            "SplunkEnterpriseSecuritySuite"
        ]

        ## es 2.2.x defined in <domain>/local/governance.conf
        self.localSubPath = "local"
        self.govFileName = "governance.conf"
        self.csFileName = "correlationsearches.conf"

        ## compliance.<n>.governance
        self.govRE = re.compile("compliance.\d+.governance")
        self.comRE = re.compile("compliance.\d+.control")
        
    def getExistingGovernance(self, confReader, workspacePath):
        """
        @param confReader: function used to read conf files into dictionaries
        @return: map of search name to governance definition
        Locate saved searches that may have governance defined.
        """
        foundCSFilePaths = []
        
        for root, dirs, files in os.walk(self.basePath):
            for f in files:
                fp = os.path.join(root, f)
                
                for domain in self.domainList:
                    if (domain in fp) and (self.csFileName in fp) and (not workspacePath in fp):
                        foundCSFilePaths.append(fp)

        fileToGovDictMap = {}
        
        for fp in foundCSFilePaths:
            confDict = confReader(fp)
            
            tempConfDict = {}
            for stanzaName, stanzaBody in confDict.iteritems():
            ## stanzaName = search name, stanzaBody = search attributes

                tempBody = {}  
                for key, val in stanzaBody.iteritems():
                    if (re.search(self.govRE, key)) or (re.search(self.comRE, key)):

                        ## if this is a governance attribute, keep it
                        tempBody[key] = val
                
                ## if this stanza has any governance attributes, keep it
                if len(tempBody) > 0:
                    tempConfDict[stanzaName] = tempBody

            ## if this savedsearch.conf has governance declarations, keep it
            if len(tempConfDict) > 0:
                fileToGovDictMap[fp] = tempConfDict

        logger.info("func:getExistingGovernance()|output::results=%s" % str(fileToGovDictMap))
        return fileToGovDictMap


    def writeNewGovernance(self, confWriter, fileToGovDictMap):
        """
        @param confWriter: function used to write conf files from dictionaries
        @param fileToGovDictMap: map of saved searches to governance controls that need to be written out
        side-effect: existing 2.0.x governance controls are written out in new format
        
        @return: map of domain name to correlation search file contents to write
        
        { <filePath-1> : 
            { <search-1> : {att-1:val-1, att-2:val-2, att-3:val-3},
              <search-2> : {att-1:val-1, att-2:val-2, att-3:val-3}
            } ,
          
          <filePath-2> :  
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
        
        for filePath, confDict in fileToGovDictMap.iteritems():

            ## the file paths still reference to the old correlationsearches.conf filenames because that's how we identify them
            ## we'll replace them with the new file name, governance.conf
            newOutFilePath = os.path.join(os.path.dirname(filePath), self.govFileName)
            
            confWriter(newOutFilePath, confDict, append=True)
            logger.info("func:writeNewGovernance()|newOutFilePath=%s, confDict=%s" % (str(newOutFilePath), str(confDict)))

    def removeOldGovernance(self, confReader, confWriter, workspacePath):
        """
        @param confReader: function used to read conf files into dictionaries
        @param confWriter: function used to write conf files into dictionaries
        Remove any governance attributes from the old file where is was defined
        """
        foundCSFilePaths = []
        
        for root, dirs, files in os.walk(self.basePath):
            for f in files:
                fp = os.path.join(root, f)
                
                for domain in self.domainList:
                    if (domain in fp) and (self.csFileName in fp) and (not workspacePath in fp):
                        foundCSFilePaths.append(fp)

        fileToDictMap = {}
        
        for fp in foundCSFilePaths:
            confDict = confReader(fp)
            
            tempConfDict = {}
            for stanzaName, stanzaBody in confDict.iteritems():
            ## stanzaName = search name, stanzaBody = search attributes

                tempBody = {}  
                for key, val in stanzaBody.iteritems():
                    if (not re.search(self.govRE, key)) and (not re.search(self.comRE, key)):

                        ## if this is not a governance attribute, keep it
                        tempBody[key] = val
                
                ## if this stanza has any attributes, keep it
                if len(tempBody) > 0:
                    tempConfDict[stanzaName] = tempBody

            ## if this correlationsearch has attributes, keep it
            if len(tempConfDict) > 0:
                fileToDictMap[fp] = tempConfDict

        logger.info("func:removeOldGovernance()|output::results=%s" % str(fileToDictMap))
        
        for filePath, confDict in fileToDictMap.iteritems():
            confWriter(filePath, confDict, append=False)
        
        return fileToDictMap


def convertGovernanceControls(confReader, confWriter, basePath, workspacePath):
    """
    @param confWriter: function to write conf files
    @param basePath: home path to Splunk apps, typically $SPLUNK_HOME/etc/apps
    @param workspacePath: path to the upgrader workspace

    Side-effect:
      - Converts the 2.0.x governance into an equivalent governance.conf
    """
    gProc = GovernanceProcessor(basePath, workspacePath)
    fileToGovDictMap = gProc.getExistingGovernance(confReader, workspacePath)
    gProc.writeNewGovernance(confWriter, fileToGovDictMap)
    gProc.removeOldGovernance(confReader, confWriter, workspacePath)


class AggregateReplacementProcessor():

    def __init__(self, basePath, workspacePath):
        """
        @param basePath: home path to Splunk apps, typically $SPLUNK_HOME/etc/apps
        @param workspacePath: path to the upgrader workspace
        """
        self.basePath = basePath
        self.workspacePath = workspacePath
        ##self.backupPath = "es_backup"
        self.domainList = [
            "SA-AccessProtection", "SA-AuditAndDataProtection",
            "SA-EndpointProtection", "SA-IdentityManagement",
            "SA-NetworkProtection", "SA-ThreatIntelligence",
            "SplunkEnterpriseSecuritySuite"
        ]

        ## es 2.2.x defined in <domain>/local/correlationsearches.conf
        self.localSubPath = "local"
        self.defaultSubPath = "default"
        self.aggFileName = "aggregate.conf"
        self.csFileName = "correlationsearches.conf"
        self.ssFileName = "savedsearches.conf"
        self.aggSettingsMap = {'index':'action.summary_index._name' , 'duration':'alert.suppress.period' , 'group_by':'alert.suppress.fields'}
        
        ## Settings that need to be set by default for PerEventAlerting
        ## perEventAlerting ERD mentions 'action.summary_index.savedsearch_name' as a relevant field
        ## however, savedsearches.conf doesn't have this attribute
        self.perEventAlertingDefaultAttributes = {'action.summary_index':'1', 
                                                  'alert.digest_mode':'1', 'alert.suppress':'1', 'alert.track':'false'
                                                  }

    def getExistingAggregateSettings(self, confReader):
        """
        @param confReader: function used to read conf files into dictionaries
        @return: list of savedsearch aggregation dictionaries [ { fileName: {confDict} }, ... {fileName: {confDict}}]
        """
        aggregateList = []
        for root, dirs, files in os.walk(self.basePath):
            for f in files:
                fp = os.path.join(root, f)
                
                for domain in self.domainList:
                
                    ## filter for inclusion/exclusion of similar files
                    if (os.path.join(domain, self.localSubPath, self.aggFileName) in fp) and (not self.workspacePath in fp):

                        confDict = confReader(fp)
                        aggregateList.append({fp:confDict})

        logger.info("func:getExistingAggregateSettings()|output::results=%s" % str(aggregateList))
        return aggregateList


    def convertAggregateSavedsearches(self, confReader, confWriter, aggregateList, analyzeOnly=True):
        """
        @aggregateList: list of savedsearch aggregation dictionaries [ { fileName: {confDict} }, ... {fileName: {confDict}}]
        @param confWriter: function used to write conf files from dictionaries
        @return: dictionary of invalid suppression settings detected
        Side-effect:
          - Updates the existing local/savedsearches.conf with per-event-alerting settings from old aggregate.conf
        """
        
        ## filter savedsearch settings by domain
        invalidFiles = {}
        for aggConf in aggregateList:
            
            for filePath, confDict in aggConf.items():

                ## keep the app path but replace aggregate.conf with savedsearches.conf
                ssFilePath = filePath.replace(self.aggFileName, self.ssFileName)
                
                origSaveSearchConf = confReader(ssFilePath)

                ## map to hold any bad aggregate stanzas
                invalidStanzas = {}
                
                tempConf = {}

                ## construct a new attribute format for perEventAlerting
                for stanza, body in confDict.items():
                    
                    ## work-around avoid introduction of a new "default" stanza
                    ## SOLNESS-3553: side-effect of using cli_common.readConfFile(path) introduces an empty "default" stanza that we want to avoid
                    if (stanza != "default"):
                    
                        ## init the output stanza with the default perEventAlert attributes
                        tempConf[stanza] = dict(self.perEventAlertingDefaultAttributes)
                    
                        ## map to hold any bad settings we find
                        invalidSettings = {}
                        for att, val in body.items():

                            ## temp for any changes we make to val
                            modifiedVal = val

                            try:
                                if att == 'duration' and int(val) < 1:
                                    ## warn of invalid duration
                                    invalidSettings[att] = '%s - ERROR: \'duration\' less than 1 second' % (val)

                                elif att == 'duration' and int(val) > 0:
                                    ## convert to valid suppression duration
                                    if int(val) >= 3600:
                                        modifiedVal = int(val) - 100
                                    else:
                                        modifiedVal = int(val)
                                
                                elif att == 'group_by' and len(str.strip(str(val))) < 1:
                                    ## warn of invalid group_by
                                    invalidSettings[att] = '%s - ERROR: \'group_by\' cannot be empty' % (val)
                                else:
                                    pass
                            except ValueError:
                                ## duration is not an integer
                                invalidSettings[att] = '%s - ERROR: \'duration\' not an integer' % (val)

                            ## filter settings by valid aggregate.conf settings
                            if self.aggSettingsMap.get(att, None):
                        
                                ## replace old aggregate attribute names with new perEventAlert attribute names
                                tempConf[stanza].update({self.aggSettingsMap[att]:modifiedVal})
                            
                                logger.info("func:convertAggregateSavedsearches()|converted aggregate setting:: %s" % str(tempConf))

                        ##confWriter(ssFilePath, tempConf, append=True)
                    
                        if len(invalidSettings) > 0:
                            invalidStanzas[stanza] = invalidSettings
                
                if (not analyzeOnly):
                    mergedConf = self.merge_conf(origSaveSearchConf, tempConf, overwrite=True)
                    confWriter(ssFilePath, mergedConf)
                
                if len(invalidStanzas) > 0:
                    invalidFiles[filePath] = invalidStanzas

        logger.info("func:convertAggregateSavedsearches()|INVALID aggregate settings:: %s" % str(invalidFiles))

        return invalidFiles

    def deprecateAggregateSearchCommand(self, confReader, confWriter):
        """
        @confReader: Conf file Reader function
        @confWrite: Conf file writer function
        Scan the local subdirectories in the SA's and remove 'aggregate' and 'localop' search commands from the search.
        """
        aggregateCommandRegex = re.compile('^(.*)\|\s*aggregate.*$', re.DOTALL)
        localopCommandRegex = re.compile('^(.*)\|\s*localop\s*\|\s*aggregate.*$', re.DOTALL)
        
        ## scan SA-* apps
        for root, dirs, files in os.walk(self.basePath):
            for f in files:
                fp = os.path.join(root, f)
                
                for domain in self.domainList:
                
                    ## filter on local/savedsearches.conf
                    if (os.path.join(domain, self.localSubPath, self.ssFileName) in fp) and (not self.workspacePath in fp):

                        ssFilePath = fp
                        
                        ## read savedsearch into a dictionary
                        ssConfDict = confReader(ssFilePath)

                        tempConf = {}
                        for stanza, body in ssConfDict.items():
                            newSettings = {}
                            
                            ## examine each saved search stanza and process the 'search' attribute
                            for att, val in body.items():
                                if (str.strip(str(att)) == 'search'):
                                    ## init to orig search str
                                    newSearchStr = val
                            
                                    try:
                                        ## remove any localop and trailing stuff
                                        newSearchStr = re.search(localopCommandRegex, newSearchStr).group(1)
                                    except AttributeError:
                                        ## did not find either aggregate OR localop commands
                                        pass

                                    try:
                                        ## remove any aggregate and trailing stuff
                                        newSearchStr = re.search(aggregateCommandRegex, newSearchStr).group(1)
                                    except AttributeError:
                                        ## did not find either aggregate OR localop commands
                                        pass
                            
                                    newSettings[att] = newSearchStr
                                else:
                                    newSettings[att] = val
                            if len(newSettings) > 0:
                                tempConf[stanza] = newSettings
                        if len(tempConf) > 0:
                            ## write new search string without aggregate command
                            confWriter(ssFilePath, tempConf, append=False)
                            logger.info("func:deprecateAggregateSearchCommand()|writing %s::%s" % (ssFilePath, tempConf))



    def deprecateAggregateFiles(self, aggregateList):
        """
        @aggregateList: list of savedsearch aggregation dictionaries [ { fileName: {confDict} }, ... {fileName: {confDict}}]
        Rename (deprecate) aggregate files after their settings are converted over to savedsearches.conf
        """
        for aggConf in aggregateList:
            for filePath, confDict in aggConf.items():
                origFilename = os.path.basename(filePath)
                deprecatedFilePath = os.path.join(os.path.dirname(filePath), origFilename + '.deprecated')
                try:
                    shutil.move(filePath, deprecatedFilePath)
                    logger.info("func:deprecateAggregateFiles()|%s --> %s" % (filePath, deprecatedFilePath))
                except Exception as e:
                    raise


    def detectSearchConflicts(self, confReader, aggregateList):
        """
        @confReader: Conf file Reader function
        @aggregateList: list of savedsearch aggregation dictionaries [ { fileName: {confDict} }, ... {fileName: {confDict}}]
        @return: list of custom searches that conflict with any new default searches
        """

        fileConflictMap = {}
        for localAggConf in aggregateList:
  
            confConflictMap = {}
            for filePath, confDict in localAggConf.items():

                localSavedsearchFilePath = filePath.replace(self.aggFileName, self.ssFileName)
                defaultSavedsearchFilePath = localSavedsearchFilePath.replace(self.localSubPath, self.defaultSubPath)
                
                localConf = confReader(localSavedsearchFilePath)
                defaultConf = confReader(defaultSavedsearchFilePath)
                
                for stanza, body in localConf.items():
                    for att, val in body.items():
                        if (att == 'search') and (defaultConf.get(stanza, dict()).get(att, None)):
                            ## post conversion, the local and default search strings are different.  Note as potential conflict
                            if val != str.strip(defaultConf.get(stanza, dict()).get(att, None)):
                                logger.info("func:detectSearchConflicts()|ls:%s la:%s lv:%s != dv:%s" % (stanza, att, val, defaultConf.get(stanza, dict()).get(att, None)))
                                confConflictMap[stanza] = {att:val}

                if len(confConflictMap) > 0:
                    fileConflictMap[localSavedsearchFilePath] = confConflictMap
        logger.info("func:detectSearchConflicts()|local-default conflicts:%s" % (str(fileConflictMap)))
        return fileConflictMap


    def merge_conf(self, confDict1, confDict2, overwrite=False):
        """
        @confDict1: first conf file dictionary to be merged
        @confDict2: second conf file dictionary to be merged
        @overwrite: flag indicating whether an attribute setting from confDict2 will overwrite an existing setting in confDict1
        @return: merged conf file dictionaries
        
        This function merges two conf file dictionaries into one and allows overwrite configuration.
        ConfDict1 is assumed to be the destination dictionary that confDict2 updates.
        IF overwrite == True THEN common attributes will take values from confDict2
        IF overwrite == False THEN common attributes will take/remain values from confDict1
        """
        newConfDict = dict(confDict1)
    
        for stanza, body in confDict2.items():

            ## new stanza
            if not newConfDict.get(stanza, None):
                newConfDict.update({stanza:body})
        
            ## existing stanza
            else:
                for att, val in body.items():

                    if newConfDict[stanza].get(att, False) and not overwrite:
                        ## attribute exists and do not overwrite
                        ## do not change the value
                        pass
                    elif newConfDict[stanza].get(att, False) and overwrite:
                        ## attribute exists and overwrite
                        ## update to the new value
                        newConfDict[stanza][att] = val
                    else:
                        ## attribute does not exist
                        newConfDict[stanza].update({att:val})
                        
        logger.info("func:merge_conf()|confDict1:%s" % (str(confDict1)))
        logger.info("func:merge_conf()|confDict2:%s" % (str(confDict2)))
        logger.info("func:merge_conf()|mergedConfDict:%s" % (str(newConfDict)))
        return newConfDict
        

def convertAggregateSettings(confReader, confWriter, basePath, workspacePath, analyzeOnly=False):
    """
    @param confReader: function to read conf files
    @param confWriter: function to write conf files
    @param basePath: home path to Splunk apps, typically $SPLUNK_HOME/etc/apps
    @param workspacePath: path to the upgrader workspace
    @return: list of dictionaries
        - invalid suppression settings detected during conversion of aggregate to per-event-alerting
        - custom searches found that may conflict with new default searches
    Side-effect:
      - Converts the 2.0.x governance into an equivalent governance.conf
    """
    aggProc = AggregateReplacementProcessor(basePath, workspacePath)
    aggList = aggProc.getExistingAggregateSettings(confReader)
    invalidSuppressionSettingsDict = aggProc.convertAggregateSavedsearches(confReader, confWriter, aggList, analyzeOnly)
    
    if (not analyzeOnly):
        aggProc.deprecateAggregateSearchCommand(confReader, confWriter)
        aggProc.deprecateAggregateFiles(aggList)

    modifiedSearchesDict = aggProc.detectSearchConflicts(confReader, aggList)
    return [invalidSuppressionSettingsDict, modifiedSearchesDict]

    

