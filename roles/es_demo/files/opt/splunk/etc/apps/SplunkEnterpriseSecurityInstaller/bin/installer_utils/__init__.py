from splunk import ResourceNotFound
import splunk.clilib.bundle_paths as bp
import splunk.clilib.cli_common as cli_common
import splunk.entity as entity
import logging
import logging.handlers
import cherrypy
import os
import re
import hashlib
import shutil
import glob
import zipfile
import datetime
import fnmatch
import json
import stat
import csv

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

class PreReqProcessor():

    ## Installation action parameters to pass to view
    INSTALL_ACTION_NOOP = "NOOP"
    INSTALL_ACTION_INSTALL = "INSTALL"
    INSTALL_ACTION_UPGRADE_MAJOR = "UPGRADE_MAJOR"
    INSTALL_ACTION_UPGRADE_MINOR = "UPGRADE_MINOR"
    INSTALL_ACTION_UPGRADE_MAINT = "UPGRADE_MAINT"
    INSTALL_ACTION_UPGRADE_BUILD = "UPGRADE_BUILD"
    INSTALL_ACTION_DISABLE = "DISABLE"
    INSTALL_ACTION_UNSUPPORT = "UNSUPPORTED"
    INSTALL_ACTION_SERVER_UNSUPPORT = "SERVER_UNSUPPORTED"
    
    ## enumeration of the string blocks within a version string
    VERSION_MAJOR = 0
    VERSION_MINOR = 1
    VERSION_MAINT = 2

    NUM_VERSION_BLOCKS = 3

    '''
    Util function to get a session key
    '''
    def getSessionKey(self):
        try:
            return cherrypy.session['sessionKey']
        except Exception as e:
            raise

    '''
    Determine App Version installed.  Return None if not installed
    '''
    def getAppVersion(self, appName, session_key):
        try:
            myEntity = entity.getEntity('apps/local', appName, sessionKey = session_key)
            version = myEntity["version"]
        except:
            version = None
        logger.info("func:getAppVersion()|App:" + appName + ";version:" + str(version))
        return version


    '''
    Determine App Build installed.  Return None if not installed
    We read app.conf via cli_common because app build is not available after disable
    '''
    def getAppBuild(self, appName):
        try:
            appConf = cli_common.readConfFile(os.path.join(bp.get_base_path(), appName, "default", "app.conf"))
            build = appConf["install"]["build"]

        ## handle case where app doesn't have a build number in app.conf
        except KeyError as e:
            build = None
            
        buildInt = self.parseInt(build, True)
        logger.info("func:getAppBuild()|build=%s" % (buildInt))
        return buildInt

    
    '''
    Returns a list of names of the installed apps with savedsearches
    The criteria for which apps contain savedsearches is defined in appFiltersREList
    '''
    def getInstalledApps(self, appFiltersREList, session_key):
        try:
            
            ## Important to have count = -1 otherwise the results maybe limited to a preset number of apps to return
            myEntities = entity.getEntities('apps/local', sessionKey = session_key, count = -1)
            appNames = myEntities.keys()
        except:
            raise
            
        installedApps = []
        for app in appNames:
            for compRE in appFiltersREList:
                if re.search(compRE, str(app)):
                    installedApps.append(str(app))

        logger.info("func:getInstalledApps()|installedAppsAll:" + str(appNames))
        logger.info("func:getInstalledApps()|installedAppsOfInterest:" + str(installedApps))
        return installedApps

    '''
    Determines if a given list of apps are disabled
    '''
    def checkAppsDisabled(self, appList, session_key):
    
        outMap = {}
        disabledList = []
        
        if len(appList) > 0:
            for app in appList:
                appEntity = entity.getEntity('apps/local', str(app), sessionKey = session_key)
                appDisabledKey = appEntity["disabled"]
                outMap[str(app)] = appDisabledKey
                disabledList.append(appDisabledKey)
        else:
            ## No components detected, pass
            pass

        logger.info("func:checkAppsDisabled()|appDisabledStatuses:" + str(outMap))
        ## If any apps are enabled then there exists a "0" --> disabled = 0
        return (not "0" in disabledList)
        

    '''
    Enables or Disables a given list of apps
    Defaults to enable
    '''
    def controlApps(self, appList, session_key, control="enable"):

        controlResult = {}
        for app in appList:
            myEn = entity.controlEntity(control,"apps/local/%s/%s" % (str(app), control), session_key)
            controlResult[app] = myEn

        logger.info("func:controlApps()|controlApps:control=%s ; result=%s" % (control, str(controlResult)))
        return controlResult

    
    '''
    Utility function to convert string into integer
    If the conversion fails, return the original string OR None, depending on the value of the argument retNoneOnError.
    '''        
    def parseInt(self, myString, retNoneOnError=False):
            result = None if retNoneOnError else myString
            try:
                result = int(myString)
            except ValueError as e:
                logger.error("func:parseInt()|%s|ValueError when converting string to integer" % str(e))
            except Exception as e:
                logger.error("func:parseInt()|%s|Unknown error when converting string to integer" % str(e))
            return result
        
    '''
    Utility function - Given a version string, this splits by the decimal character and pads, with zero, lists less than the specified length
    '''
    def padVersionBlockList(self, versionStr, padNum):
        try:
            versionList = versionStr.split(".")
            while len(versionList) < padNum:
                versionList.append("0")
            
        # If version is None then 0.0.0
        except AttributeError as e:
            versionList = list("0" * padNum)
            logger.info("func:padVersionBlockList()|version:%s" % versionStr)

        return versionList

    '''
    Get the Splunk Server Version
    '''
    def getServerVersion(self, session_key):
        try:
            myEntity = entity.getEntity("server/info", "server-info", sessionKey=session_key)
            serverVersion = myEntity['version']
        except:
            raise
            
        logger.info("func:getServerVersion()|serverVersion=%s" % serverVersion)
        return str(serverVersion)

    '''
    Compares current server version to minimum required server version
    Input parameters are expected as string format "major.minor.maint"
    The return value is negative if current < minimum, zero if current == minimum and strictly positive if current > minimum
    '''
    def compareServerVersions(self, currentVersion, minVersion):

        minVersionList = self.padVersionBlockList(minVersion, self.NUM_VERSION_BLOCKS)
        currentVersionList = self.padVersionBlockList(currentVersion, self.NUM_VERSION_BLOCKS)
        
        minVersionListInt = [self.parseInt(x) for x in minVersionList]
        currentVersionListInt = [self.parseInt(x) for x in currentVersionList]

        logger.info("func:getServerVersion()|currentServerVersion=%s; minServerVersion=%s" % (currentVersionListInt, minVersionListInt))
        return cmp(currentVersionListInt, minVersionListInt)


    '''
    Compare currently installed version against the current release version ES
    Return an install/upgrade action code
    '''
    def handleInstallationAction(self, releaseVersion, installedVersion, releaseBuild, installedBuild, unsupportedVersions, appDisabled, currentServerVersion, isMinServerVersion):
        
        installAction = None

        if isMinServerVersion < 0:
            installAction = self.INSTALL_ACTION_SERVER_UNSUPPORT
            versionBuild = currentServerVersion

        else:

            ## install if no app is found
            if installedVersion is None:
                installAction = self.INSTALL_ACTION_INSTALL
            
            else:
                ##proceed upgrade
    
                releaseVersionBlockList = self.padVersionBlockList(releaseVersion, self.NUM_VERSION_BLOCKS)
                installedVersionBlockList = self.padVersionBlockList(installedVersion, self.NUM_VERSION_BLOCKS)
                
                installedMajor = self.parseInt(installedVersionBlockList[self.VERSION_MAJOR])
                installedMinor = self.parseInt(installedVersionBlockList[self.VERSION_MINOR])
                installedMaint = self.parseInt(installedVersionBlockList[self.VERSION_MAINT])
                installedBuildInt = self.parseInt(installedBuild)
        
                releaseMajor = self.parseInt(releaseVersionBlockList[self.VERSION_MAJOR])
                releaseMinor = self.parseInt(releaseVersionBlockList[self.VERSION_MINOR])
                releaseMaint = self.parseInt(releaseVersionBlockList[self.VERSION_MAINT])
                releaseBuildInt = self.parseInt(releaseBuild)
                
                logger.info("func:handleInstallationAction()|releaseVersion=%s" % (releaseVersion))
                logger.info("func:handleInstallationAction()|installedVersion=%s" % (installedVersion))
                logger.info("func:handleInstallationAction()|ProcessedVersions|installedMajor=%s,installedMinor=%s,installedMaint=%s" % (installedMajor,installedMinor,installedMaint))
                logger.info("func:handleInstallationAction()|ProcessedVersions|releaseMajor=%s,releaseMinor=%s,releaseMaint=%s" % (releaseMajor,releaseMinor,releaseMaint))
                logger.info("func:handleInstallationAction()|ProcessedVersions|releaseBuild=%s,installedBuild=%s" % (releaseBuildInt, installedBuildInt))
                
                ## Check if installed version is unsupported by this install/upgrader
                supportedVersion = True
                for version in unsupportedVersions:
                    versionRE = re.compile(version)
                    if re.search(versionRE, installedVersion):
                        supportedVersion = False
                
                if not supportedVersion:
                    installAction = self.INSTALL_ACTION_UNSUPPORT
    
                ## SPECIAL CASE: Beta installs do not update version or revision numbers, thus we should check the build number
                ## Normally, we can simply check the version/revision numbers
                elif (installedBuildInt >= releaseBuildInt):
                    installAction = self.INSTALL_ACTION_NOOP
                    logger.info("func:handleInstallationAction()|NOOP:installedBuild >= releaseBuild")
                
                
                ## If a Beta version is installed we need to exclude that from version value comparisons.
                ## The string "beta" will always greater than a numeric value.  
                elif ("beta" not in installedVersion.lower()) and \
                    ( (installedMajor > releaseMajor) or \
                    (installedMajor == releaseMajor and installedMinor > releaseMinor) or \
                    (installedMajor == releaseMajor and installedMinor == releaseMinor and installedMaint > releaseMaint) or \
                    (installedMajor == releaseMajor and installedMinor == releaseMinor and installedMaint == releaseMaint and installedBuildInt > releaseBuildInt) or \
                    (installedMajor == releaseMajor and installedMinor == releaseMinor and installedMaint == releaseMaint and installedBuildInt == releaseBuildInt) ):
                   
                    installAction = self.INSTALL_ACTION_NOOP
                    logger.info("func:handleInstallationAction()|NOOP:installedVersion >= releaseVersion")
    
                else:
                    
                    if not appDisabled:
                        installAction = self.INSTALL_ACTION_DISABLE
                    
                    elif installedMajor < releaseMajor:
                        installAction = self.INSTALL_ACTION_UPGRADE_MAJOR
            
                    elif (installedMajor == releaseMajor) and (installedMinor < releaseMinor):
                        installAction = self.INSTALL_ACTION_UPGRADE_MINOR
            
                    elif (installedMajor == releaseMajor) and (installedMinor == releaseMinor) and (installedMaint < releaseMaint):
                        installAction = self.INSTALL_ACTION_UPGRADE_MAINT
                        
                    elif (installedBuildInt < releaseBuildInt):
                        installAction = self.INSTALL_ACTION_UPGRADE_BUILD
                        
                    else:
                        installAction = self.INSTALL_ACTION_NOOP
                        logger.info("func:handleInstallationAction()|NOOP:version check error")

            versionBuild = "(version:%s, build:%s)" % (installedVersion,installedBuild)

        logger.info("func:handleInstallationAction()|installAction:" + str(installAction))

        return [installAction, versionBuild]


class FileDiffProcessor():

    def __init__(self, srcAppName, hashAlg):
        self.thisAppName = srcAppName
        self.hashAlg = hashAlg

    '''
    Utility function to return FILENAME|hash:#### for given files in homepath
    filterPaths: allow you to target specific subdirectories
    homepath: path to start iteration of hash generation
    '''
    def getInstalledFileList(self, homePath, includeRegexFilters, exclusionFilters):
        # list of currently installed files to compare
      	fileList = []
      	
      	# walk through all files within working directory
        for root, dirs, files in os.walk(homePath):

            for f in files:
                fullPath = os.path.join(root,f)
                
                ## Only gather the files we want in the 'include' folders i.e. DA, SA, TA, self.thisAppName
                for i in includeRegexFilters:
                    exclusionsFound = False
                    if re.search(i, fullPath):

                        ## Exclude certain files and folders eventhough they show up in the specific folders
                        for e in exclusionFilters:
                            if e in fullPath:
                                exclusionsFound = True

                        if not exclusionsFound:

                            fileList.append(fullPath)

        logger.info("func:getInstalledFileList()|installedFileList:" + str(fileList))
        return fileList


    '''
    Compare the current installation files with the files delivered in the original/old package
    There are two outputs generated: modified 'default' and 'extensions'
    extensions -> files that currently exist that were not part of the original package
    modified default -> default, appserver and bin files that came with original package but have modifications indicated by different hash values
    return list of extensions and list of modified defaults
    '''
    def handleFileDiff(self, targetFileList, hashPath, outputPath):
    
        # Get the hash values for the files included with original 1.1.2 install
        try:
            origFH = open(hashPath,"r")

            # get all lines without newline characters \n
            origList = origFH.read().splitlines()
            
            # The original files, as specified in the hash list, has filespaths is in POSIX format
            # If the Splunk is installed on Windows, the path separators must be replaced with double backslashes to accomodate
            # Alternatively, we could provide a separate MDS file list specific for Windows, but this is easier.
            if "nt" in os.name:
                for i in range(len(origList)):
                    origList[i] = str(origList[i]).replace("/", os.sep)
            
            # filelist of the currently installed 1.1.2 instance with hash values computed and appended
            currentList =  self.formatFilePaths(self.appendHash(targetFileList))
    
    
            origListSansHash = []
            for line in origList:
                ## Get only the file name part
                origListSansHash.append(line.split("|sha1:")[0])
    
            '''
            To get extensions, we diff the file paths without the Hash
            This compares currently installed files with the files from the original package
            extensions = currentFiles - newFiles
            '''
            currentListSansHash =  self.formatFilePaths(targetFileList)
            extensionSet = set(currentListSansHash) - set(origListSansHash)
            extensionList = list(extensionSet)
            
            '''
            allDiff -> all differences between installed files and original packages
            this includes extensions as well modified files
            '''
            allDiffList = list(set(currentList) - set(origList))
            allDiffSansHash = []
            for line in allDiffList:
                allDiffSansHash.append(line.split("|sha1:")[0])
            
            
            '''
            To get the modified 'default' files subtract the extensions and the allDiff
            modified defaults = allDiff - extensions
            '''
            modifiedDefaultSet = set(allDiffSansHash) - extensionSet
            modifiedDefaultList = list(modifiedDefaultSet)
            
            '''
            Process the extensionsList and modifiedDefaultList for output
            '''
            extensionListStr = ""
            for line in sorted(extensionList):
                extensionListStr += line + "<br>"
                
            modifiedDefaultListStr = ""
            for line in sorted(modifiedDefaultList):
                modifiedDefaultListStr += line + "<br>"

            try:
                ## make the parent directory for outputPath, if it doesn't already exist
                localDir = os.path.dirname(outputPath)
                os.makedirs(localDir)
                
                ## Unix: set the directory permission, core makes the local directory default to 700
                if os.name != "nt":
                    os.chmod(localDir, 0700)
                    
            except OSError as e:
                ##folder already exists
                pass
            except Exception as e:
                logger.error("func:handleFileDiff()|" + str(e))
                raise

            extensionListFH = open(outputPath, "w")

            extensionListFH.write(extensionListStr)
            extensionListFH.close()
    
            logger.info("func:handleFileDiff()|" + "currentList:" + str(self.appendHash(targetFileList)))
            logger.info("func:handleFileDiff()|" + "extensionList:" + str(sorted(extensionList)))
            logger.info("func:handleFileDiff()|" + "modifiedDefaultList:" + str(sorted(modifiedDefaultList)))
            
        except Exception as e:
            logger.error("func:handleFileDiff()|" + str(e))
            raise

        return sorted(extensionList), extensionListStr, modifiedDefaultListStr

    def getHash(self, filePath):
        """
        Utility function to return hash value of a file as string
        @filePath: path to the file to compute hash
        """
        try:
            m = hashlib.new(self.hashAlg)
            f = open(filePath, "rb")
            while True:
                data = f.read(128)
                if len(data) == 0:
                    break
                m.update(data)
            f.close()
            return str(m.hexdigest())
        except:
            raise

    '''
    For given text-based list of filepaths, it returns the same list with computed the Hash and append to each 
    '''
    def appendHash(self, fileList):
        hashedList = []
        for f in fileList:
            hashVal = self.getHash(f)
            hashedList.append(f + "|sha1:" + hashVal)
        return hashedList

    '''
    For given text-based list of filepaths, it returns the same list with filepaths filtered containing only [D|S|T]A foldernames and beyond
    '''
    def formatFilePaths(self, fileList):
      	formattedList = []
      	filenameFilter = re.compile("([D|S|T]A-.*$)|(" + self.thisAppName + ".*$)|(Splunk_[D|S|T]A_.*$)")
        for f in fileList:
            appPath = re.search(filenameFilter, f)
            if appPath:
                formattedList.append(str(appPath.group(0)))
            else:
                pass
        return formattedList

    '''
    Get the appropriate Hash filelist for the version of app installed
    '''
    def getHashFilename(self, appVersion, hashPath):

        hashFiles = []
        result = None
        
        for f in os.listdir(hashPath):
        
            # Look for any Hash filename that contains the app version
            if fnmatch.fnmatch(f, "".join(["*", appVersion, "*"])):
                hashFiles.append(f)

        try:
            result = hashFiles[0]
        except:
            logger.info("func:getHashFilename()|No Hash file found for installed version:" + appVersion)
            
        return result


    def getComparisonFile(self, appVersion, filePath, fileExt=None):
        """
        The installer ships with a collection comparison files - i.e. .hash.txt and .diff files.
        These files, dynamically generated at build time and are use to determine file differences and conflicts at upgrade time.
        These files, by convention, are named according to their respective release version-build.
        Each prior release has an individual file.
        
        @param appVersion: the version of the currently installed app/suite
        @param filePath: path to directory containing the files
        @param fileExt: extension to the file used as an inclusion filter.  Defaults to None
        @return: the file corresponding according to the app version installed
        """
        fileList = []
        result = None
        
        fileNameList = ["*", appVersion, "*"]
        if fileExt:
            fileNameList.append(fileExt)
        
        for f in os.listdir(filePath):
        
            # Look for any filename that contains the app version and extension, if arg present
            if fnmatch.fnmatch(f, "".join(fileNameList)):
                fileList.append(f)

        try:
            result = fileList[0]
        except:
            logger.info("func:getComparisonFile()|No %s file found for installed version: %s" % (fileExt, appVersion))
            
        logger.info("func:getComparisonFile()|diffFile: %s" % (result))
        return result


    def compareDefaultConf(self, compareFilePath, basePath):
        """
        Using the compare/diff file for the given installed app version, determine which local conf files are in conflict with the latest release.
        
        @param compareFilePath: pathname to the compare file that contains comparison information between the installed release and the latest release
        @param basePath: $SPLUNK_HOME/etc/apps path
        @return: list containing the conf file conflicts

        Format: 
        - files_deprecated: []
        - files_modified: []
            - stanzas_deprecated: []
            - settings_deprecated: {}
            - settings_modified: {}
        """
        
        ## Output map of all local conflicts found
        foundConflictsMap = {}
        
        ## containers for intermediate conflicts found
        stanzasDeprecatedList = []
        settingsDeprecatedMap = {}
        settingsModifiedMap = {}
        
        comparisonMap = {}

        try:
            with open(compareFilePath, "r") as fh:
                comparisonMap = json.load(fh)
        except SyntaxError as e:
            try:
                with open(compareFilePath, "r") as fh:
                    comparisonMap = json.load(fh, 'ascii')    
            except SyntaxError as e:
                try:
                    with open(compareFilePath, "r") as fh:
                        comparisonMap = json.load(fh, 'latin-1')
                except SyntaxError as e:
                    logger.info("func:compareDefaultConf() | Error loading file: %s | %s" % (basePath, str(e)))
                    raise # log alert here



        filesDeprecatedList = comparisonMap.get("files_deprecated", [])
        filesModifiedList = comparisonMap.get("files_modified", [])

        ####
        ## Compile deprecated files list
        foundDeprecatedFilesList = []
        for fileDeprecated in filesDeprecatedList:
            
            ## The comparison file contains "default" in the path, we need to look for the file in "local"
            fileDeprecated = fileDeprecated.lstrip("etc/apps/")
            fileDeprecated = fileDeprecated.replace("default", "local")
            
            if os.path.exists(os.path.join(basePath, fileDeprecated)):
                foundDeprecatedFilesList.append(fileDeprecated)

        if foundDeprecatedFilesList:
            foundConflictsMap["files_deprecated"] = foundDeprecatedFilesList
        
        ####
        ## Compile modified files list.
        ## Elements within this list are dictionaries of {files:{dictionary of stanzas}}
        foundModifiedFilesList = []
        for fileModifiedMap in filesModifiedList:

            foundFileModifiedMap = {}
            for fileModified, settingsModifiedMap in fileModifiedMap.items():

                ## The comparison file contains "default" in the path, we need to look for the file in "local"
                fileModified = fileModified.lstrip("etc/apps/")
                fileModified = fileModified.replace("default", "local")
                
                stanzasDeprecatedList = settingsModifiedMap.get("stanzas_deprecated", [])
                settingsDeprecatedMap = settingsModifiedMap.get("settings_deprecated", {})
                settingsModifiedMap = settingsModifiedMap.get("settings_modified", {})

                foundStanzasDeprecatedList = []
                foundSettingsDeprecatedMap = {}
                foundSettingsModifiedMap = {}
                
                ####
                ## Open and read the LOCAL .conf file. Its contents will be compared here to its entry in .diff file
                fileModifiedPath = os.path.join(basePath, fileModified)
                if os.path.exists(fileModifiedPath):
                    
                    ## Let's check if any conflicting settings exist
                    fileModifiedDict = ConfProcessor.read_conf_file(fileModifiedPath)
                    
                    ## Check for existence of deprecated stanzas
                    for stanzaDeprecated in stanzasDeprecatedList:
                        if stanzaDeprecated in fileModifiedDict.keys():
                            foundStanzasDeprecatedList.append(stanzaDeprecated)

                    ## Check for existence of deprecated settings
                    for stanza, settingsList in settingsDeprecatedMap.items():

                        foundSettingsDeprecatedList = [s for s in settingsList if s in fileModifiedDict.get(stanza, [])]

                        if foundSettingsDeprecatedList:
                            foundSettingsDeprecatedMap[stanza] = foundSettingsDeprecatedList
                        
                    ## Check for existence of conflicting settings modifications
                    for stanza, settingsList in settingsModifiedMap.items():

                        foundSettingsModifiedList = [s for s in settingsList if s in fileModifiedDict.get(stanza, [])]
                        
                        if foundSettingsModifiedList:        
                            foundSettingsModifiedMap[stanza] = foundSettingsModifiedList

                foundStanzaSettingsMap = {}
                if foundStanzasDeprecatedList:
                    foundStanzaSettingsMap["stanzas_deprecated"] = foundStanzasDeprecatedList
                if foundSettingsDeprecatedMap:
                    foundStanzaSettingsMap["settings_deprecated"] = foundSettingsDeprecatedMap
                if foundSettingsModifiedMap:
                    foundStanzaSettingsMap["settings_modified"] = foundSettingsModifiedMap
                
                if foundStanzaSettingsMap:
                    foundFileModifiedMap[fileModified] = foundStanzaSettingsMap

            if foundFileModifiedMap:
                foundModifiedFilesList.append(foundFileModifiedMap)


        foundConflictsMap["files_modified"] = foundModifiedFilesList

        logger.info("func:compareDefaultConf()|ConflictsDict: %s" % (foundConflictsMap))
        return foundConflictsMap

    def prettyPrintConfConflicts(self, conflictsDict):
        """
        Given a processed dictionary containing detected conflicts, this function converts it to a formatted string
        @param conflictsDict: dictionary containing detected .conf conflicts
        @return: string representation of .conf dictionary
        """
        outputStr = ""
        filesDeprecatedStr = ""
        stanzasDeprecatedStr = ""
        settingsDeprecatedStr = ""
        settingsModifiedStr = ""
        
        try:
            dfList = conflictsDict["files_deprecated"]
            filesDeprecatedStr += "<ul>"
            for df in dfList:
                filesDeprecatedStr += "<li>file: %s</li>" % df
            filesDeprecatedStr += "</ul>"
        except KeyError:
            ## No deprecated files detected
            pass

        try:
            mfList = conflictsDict["files_modified"]
            for mfMap in mfList:
                for fileName, stanzaSettingsMap in mfMap.items():
                    try:
                        stanzasDepList = stanzaSettingsMap["stanzas_deprecated"]
                        stanzasDeprecatedStr += "<p>removed stanza(s): file: %s<br><ul>" % (fileName)
                        for stanza in stanzasDepList:
                            stanzasDeprecatedStr += "<li>stanza: [%s]</li>" % (stanza)
                        stanzasDeprecatedStr += "</ul></p>"
                    except KeyError:
                        ## there are no deprecated stanzas
                        pass
                    
                    try:
                        settingsDepMap = stanzaSettingsMap["settings_deprecated"]
                        for stanza, settingsList in settingsDepMap.items():
                            settingsDeprecatedStr += "<p>removed attribute(s): file: %s ==> stanza: [%s]<br><ul>" % (fileName, stanza)
                            for setting in settingsList:
                                settingsDeprecatedStr += "<li>attribute: %s</li>" % (setting)
                            settingsDeprecatedStr += "</ul></p>"
                    except KeyError:
                        ## there are no deprecated settings
                        pass
                        
                    try:
                        settingsModMap = stanzaSettingsMap["settings_modified"]
                        for stanza, settingsList in settingsModMap.items():
                            settingsModifiedStr += "<p>different attribute value(s): file: %s ==> stanza: [%s]<br><ul>" % (fileName, stanza)
                            for setting in settingsList:
                                settingsModifiedStr += "<li>attribute: %s</li>" % (setting)
                            settingsModifiedStr += "</ul></p>"
                    except KeyError:
                        ## there are no deprecated settings
                        pass
        except KeyError:
            ## No modified files detected
            pass


        if filesDeprecatedStr:
            outputStr += "<p><u>Local .conf files removed from latest default version</u></p>" + filesDeprecatedStr

        if stanzasDeprecatedStr or settingsDeprecatedStr or settingsModifiedStr:
            outputStr += "<p><u>Local .conf files different from latest default version</u></p>"

        if stanzasDeprecatedStr:
            outputStr += "<p><em>Local .conf stanzas removed from latest default version</em></p>" + stanzasDeprecatedStr

        if settingsDeprecatedStr:
            outputStr += "<p><em>Local .conf attributes removed from latest default version</em></p>" + settingsDeprecatedStr

        if settingsModifiedStr:
            outputStr += "<p><em>Local .conf attributes different from latest default version</em></p>" + settingsModifiedStr

        return outputStr

class UpgradeProcessor():

    '''
    Backup current installation to a folder, in case we need to recover
    basePath - path to start looking for apps to backup
    backupFoldername - the output foldername of the backup directory
    appREList - a list of regexes used to filter/determine which apps should be backed-up
    **The backup folder name should not be part of the appREList otherwise, there will be an infinitely loop**
    '''
    def backupCurrentInstallation(self, basePath, backupFoldername, appREList):

        timeStampStr = datetime.date.strftime(datetime.datetime.utcnow(), "%Y-%m-%d-%H-%M-%S")

        bfn = os.path.join(backupFoldername + "-" + timeStampStr, "apps")
        backupFolderPath = os.path.join(basePath,bfn)
        
        logger.info("func:backupCurrentInstallation()|" + "backupFolderPath:" + str(backupFolderPath))
        try:
            if not os.path.exists(backupFolderPath):
                os.makedirs(backupFolderPath)

            ## $splunk_home/etc/apps is the path to look for current app files
            etcAppsList = os.listdir(basePath)
            appList = []
            backupList = []
            
            for obj in etcAppsList:
                if os.path.isdir(os.path.join(basePath, obj)):
                    appList.append(obj)
            
            for appFolderName in appList:
            
                ## ONLY look for and back up folders that are related as specified in this suite/main-app
                for folderRegex in appREList:
                    if re.search(folderRegex, appFolderName):
                        backupList.append(appFolderName)
            
            ## Perform the backup/move to backup folder
            for appFolderName in backupList:
                shutil.copytree(os.path.join(basePath, appFolderName), os.path.join(backupFolderPath, appFolderName))
                logger.info("func:backupCurrentInstallation()|" + "backing-up App:" + str(appFolderName))

            # Zip up old app folders
            self.zipdir(backupFolderPath, backupFolderPath + ".zip")

            # Important to remove app folder, otherwise consecutive runs of upgrader will detect this back up folder as containing valid files to backup
            shutil.rmtree(backupFolderPath, ignore_errors=True)
        except:
            raise

    '''
    Zip/archive a folder
    This is used to archive the back up folder
    '''
    def zipdir(self, basedir, archivename):
        z = zipfile.ZipFile(archivename, "w", zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(basedir):
            #NOTE: ignore empty directories
            for fileName in files:
                absfileName = os.path.join(root, fileName)
                zfileName = absfileName[len(basedir)+len(os.sep):] #XXX: relative path
                z.write(absfileName, zfileName)
        z.close()


class PackageProcessor():

    '''
    The zip file is delivered with the upgrader within the workspace
    Whenever the upgrader is run, we need to unpack the ES zip into the upgrader workspace $splunk_home/etc/apps/<upgrader-workspace>/
    '''
    def handleZipPackage(self, basePath, packagePath, packageRegex):
        try:
            zipPackageList = glob.glob(os.path.join(basePath, packagePath, packageRegex))
            if len(zipPackageList) == 0:
                raise AssertionError("Cannot find zip package" + ":" + basePath + os.sep + packagePath)
            else:
            
                # Remove zip extractions from previous runs
                shutil.rmtree(os.path.join(basePath, packagePath, "etc"), ignore_errors=True)
                
                # unzip the package
                # Workaround for Issue4710
                # extractall() broken Python <= 2.7
                # Although Splunk 4.3+ ships with Python 2.7, extractall() still does not seem to work - permissions problems
                z = zipfile.ZipFile(zipPackageList[0])

                for f in z.namelist():
                    if f.endswith('/'):
                        f = f[0:-1]
                        try:
                            os.makedirs(os.path.join(basePath, packagePath, str(f)))
                        except Exception as e:
                            raise
                    else:
                        try:
                            z.extract(f, path=(os.path.join(basePath, packagePath)))
                        except Exception as e:
                            raise

        except Exception as e:
            # let caller handle this
            raise

class InstallProcessor():

    '''
    This class handles either installing or upgrading the new DA/SA/TA and main app FROM the installer app TO $splunk_home/etc/apps
    srcDir - the directory containing apps (directory format) to deploy to $splunk_home/etc/apps
    '''
    def installApps(self, srcDir):
        
        installer = bp.BundleInstaller()
        appList = os.listdir(srcDir)
        resultMap = {bp.BundleInstaller.STATUS_UPGRADED:"UPGRADED", bp.BundleInstaller.STATUS_INSTALLED:"INSTALLED"}
        
        try:
            for app in appList:
                if os.path.isdir(os.path.join(srcDir, app)):
                    installResult = installer.install_from_dir(srcDir, app, cleanup=False)
                    logger.info("func:installApps()|" + app + " - " + resultMap[installResult[1]])
        except:
            raise

    def set_app_is_configured(self, basePath, appName, isConfigured="0"):
        '''
        This sets the is_configured flag in local/app.conf.
        This is primarily used re-enable setup UI to run post upgrade.
        
        [install]
        is_configured = 0
        
        @param basePath: path of Splunk apps directory - typically, $SPLUNK_HOME/etc/apps
        @param appName: name of app for which to set the is_configured flag
        @param isConfigured: default = 0, value to set the is_configured flag (0 == false, 1 == true)
        
        Side-effect: local/app.conf > install > is_configured is modified according to the given function arguments.
        '''
        appPath = os.path.join(basePath, appName, "local", "app.conf")
        try:
            appConf = ConfProcessor.read_conf_file(appPath)
            appConf["install"]["is_configured"] = isConfigured
        except IOError:
            ## There's no local/app.conf; create a conf file
            appConf = {"install":{"is_configured":isConfigured}}
        except KeyError:
            ##  There's no 'install' stanza; create an install stanza
            appConf["install"] = {"is_configured":isConfigured}

        logger.info("func:set_app_is_configured()|" + str(appConf))
        ConfProcessor.write_conf_file(appPath, appConf)


class ConfProcessor():

    @staticmethod
    def read_conf_file(path):
        '''
        Wrapper to cli_common -> readConfFile()
        This better handles things like:
            * Newlines in attribute values
            * Escaped characters in attribute names

        @param path: path to the conf file to read
        @return: Dictionary representation of the .conf file
        '''
        return cli_common.readConfFile(path)

    
    @staticmethod
    def write_conf_file(path, newStanzas, append=True):
        '''
        Taken from Unix app > packager.py
        Modified to have append optional OVERWRITE behavior with append=False
        '''

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        
        if append:
            existingStanzas = ConfProcessor.read_conf_file(path)
            stanzas = ConfProcessor.removeDuplicateStanzas(existingStanzas, newStanzas)
        else:
            stanzas = newStanzas
        
        # Write out file.
        with open(path, "w") as f:
            first_stanza = True
            #for stanza_name, stanza_body in stanzas.items():
            keyList = stanzas.keys()
            keyList.sort()
            for key in keyList:
                stanza_name = key
                stanza_body = stanzas[key]
                if first_stanza:
                    first_stanza = False
                else:
                    f.write('\n')
                f.write('\n[%s]\n' % stanza_name)

                for attr in sorted(stanza_body.keys()):
                    f.write('%s = %s\n' % (attr, stanza_body[attr]))
    
        return stanzas
    
    @staticmethod
    def removeDuplicateStanzas(oldStanzas, newStanzas):
        '''
        Helper function for write_conf_file, when writing to an existing conf file we check its contents first
        .conf files cannot have duplicate stanzas, this will removes the duplicates
        In case of name collisions, the newer stanza will be used
        '''
        outputStanzas = {}
        
        for oldKey in oldStanzas:
            if oldKey in newStanzas:
                outputStanzas[oldKey] = newStanzas[oldKey]
                del newStanzas[oldKey]
            else:
                outputStanzas[oldKey] = oldStanzas[oldKey]
                
        for newKey in newStanzas:
            outputStanzas[newKey] = newStanzas[newKey]
        
        return outputStanzas


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
                    
class DeprecateProcessor():

    def getDeprecateJSON(self, depPath):
        '''
        Get the appropriate deprecation filelist
        @param depPath: path to the folder that contains the deprecate file list
        @return: JSON object of the deprecated files
        '''
        depFiles = []
        for f in os.listdir(depPath):
        
            # Look for any Hash filename that contains the app version
            if fnmatch.fnmatch(f, "".join(["*.dep"])):
                depFiles.append(f)

        try:
            fileName = depFiles[0]
            fh = open(os.path.join(depPath, fileName),"rb")
            return json.load(fh)
        except IndexError:
            logger.info("func:getDeprecateFile()|No deprecate file found")
        except Exception:
            raise
        