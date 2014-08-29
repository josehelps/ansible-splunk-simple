from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.clilib.bundle_paths as bp
import logging
import logging.handlers
import os
import re
import sys

sys.path.append( os.path.join("..","..","..", "bin") )

from installer_utils import *
from nav_utils import *
import ess_202_conversion

#logger = logging.getLogger('splunk.appserver.mrsparkle.controllers.es_installer')
BASE_PATH = os.path.join(bp.get_base_path())

#name of this app
APP_NAME = "SplunkEnterpriseSecurityInstaller"

APP_NAME_LOWER_PREFIX = "es"
LOGGER_NAME = APP_NAME_LOWER_PREFIX + '_installer_controller'

#name of app deployed by this app/installer
SRC_APP_NAME = "SplunkEnterpriseSecuritySuite"

# List of versions regexes for unsupported versions.  Including alpha-numeric in case of ex: 1.0.beta OR "^1(\.[a-zA-Z0-9]+)*$"
UNSUPPORTED_VERSIONS = ["^1\..*"]

MIN_SPLUNK_VERSION = "6.1.2.1"

# List of paths that are used during app install and upgrade process
UPGRADE_WORKSPACE_SUBPATH = os.path.join(APP_NAME, "default", "src","etc","apps")
PACKAGE_SUBPATH = os.path.join(APP_NAME, "default", "src")
HASH_PATH = os.path.join(BASE_PATH, APP_NAME, "default", "hash")
DIFF_PATH = os.path.join(BASE_PATH, APP_NAME, "default", "diff")
RELEASE_APP_CONF_PATH = os.path.join(BASE_PATH, APP_NAME,"default","app.conf")
EXTENSIONS_OUTPUT_FILE = os.path.join(BASE_PATH, APP_NAME,"local","extensions_filelist.txt")
DEP_PATH = os.path.join(BASE_PATH, APP_NAME, "default", "deprecate")

# Shell-style filename - No tilde expansion is done, but *, ?, and character ranges expressed with [] will be correctly matched
PACKAGE_SHELL_FILENAME = "splunk_app_es*.zip"

## List of Apps filters that contain savedsearches which need to be disabled prior to upgrade
## include only SRC_APP_NAME not the installer app which maybe likely match thus we use "^SRC_APP_NAME$"
SAVEDSEARCH_COMPONENTS_RE = ["SA-[a-zA-Z0-9-_]+", "DA-ESS-[a-zA-Z0-9-_]+", "".join(["^",SRC_APP_NAME,"$"]), "Splunk_[D|S|T]A_[a-zA-Z0-9-_]+", "TA-[a-zA-Z0-9-_]+"]


## **IMPORTANT** This folder should not be named the same as the parent ES app.  If it is, it must be included as an "ignoreFilter".
## Otherwise the backup step will loop infinitely if it contains the same name as the original app - it will copy itself as a sub-directory into itself and continue
BACKUP_FOLDER_NAME = APP_NAME_LOWER_PREFIX + "_backup"

## The hash algorithm to use to detect modifications to default files
HASH_ALG = "sha1"

def setup_logger(level):
    """
    Setup a logger for the controller
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var','log','splunk',LOGGER_NAME + '.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

# Setup the handler
logger = setup_logger(logging.INFO)
logger.info("init_logger")

class ESInstaller(controllers.BaseController):
    '''ES installer controller'''

    # List of regexes that will be used to identify ES specific app folders; as they exist within $splunk_home/etc/apps
    DOMAIN_APP_FOLDERS = ["DA-ESS-[a-zA-Z0-9-_]+", "SA-[a-zA-Z0-9-_]+", "TA-[a-zA-Z0-9-_]+", "Splunk_[D|S|T]A_.+", SRC_APP_NAME]
    
    # There are the folder regexes that we'll be looking inside for user modified files, so we can report any found
    DEFAULT_APP_SUBFOLDERS = ["bin", "appserver", "default"]
    
    # Files and folders to ignore.  "default.old" folders are created from previous runs of upgrade 
    IGNORE_FILES = [".pyc", ".pyo", ".csv.default", "default.meta", "readme", "app.conf"]
    IGNORE_FOLDERS = [APP_NAME, "deployment-apps", "Eventgen", "default.old"]
    
    # List of apps that are deprecated
    DEPRECATED_FOLDERS = ["TA-cisco", "TA-deployment-apps", "TA-nix", "TA-checkpoint", "SA-CommonInformationModel", "TA-nessus", "TA-ip2location", "TA-flowd", "TA-mcafee"]

    DEPRECATED_FOLDERS_KEEP_ENABLED = ["TA-checkpoint", "TA-flowd"]

    def __init__(self):
        
        try:
            self.INSTALLED_VERSION = None
            
            # init helper classes that process the install or upgrade
            self.preReqProc = PreReqProcessor()
            self.packageProc = PackageProcessor()
            self.fileDiffProc = FileDiffProcessor(SRC_APP_NAME, HASH_ALG)
            self.upgradeProc = UpgradeProcessor()
            self.installProc = InstallProcessor()
            self.confProc = ConfProcessor()
            self.csvProc = CsvUpgradeProcessor(BASE_PATH, UPGRADE_WORKSPACE_SUBPATH)
            self.ccp = ess_202_conversion.CustomConfProcessor()
            self.cxp = ess_202_conversion.CustomXMLProcessor()
            self.navProc = NavUpgradeProcessor(SRC_APP_NAME)
            self.depProc = DeprecateProcessor()

            # Construct the include/exclude regex filters from the pre-defined folder declarations
            # These regexes will be used heavily to compare file differences
            self.defaultRegexFilters = []
            self.customRegexFilters = []
            self.ignoreFilters = []
            isWindows = "nt" in os.name
    
            for app in ESInstaller.DOMAIN_APP_FOLDERS:
                for sub in ESInstaller.DEFAULT_APP_SUBFOLDERS:
                    defaultPath = os.path.join(".",app,sub)
                    
                    ## The regex paths will have double backslashes (os.sep), if it's Windows, they'll need quadruple backslashes
                    if isWindows:
                        defaultPath = defaultPath.replace(os.sep, os.sep + os.sep)
                    
                    self.defaultRegexFilters.append(re.compile(defaultPath, re.IGNORECASE))
                
            self.ignoreFilters = ESInstaller.IGNORE_FILES + ESInstaller.IGNORE_FOLDERS + ESInstaller.DEPRECATED_FOLDERS

            super(ESInstaller, self).__init__()

        except Exception as e:
            logger.error(str(e))


    '''
    This is the main controller function that interacts with the module/view.
    Various steps presented within the view correspond to a "step" within this controller.
    Each step performs a separate process of the install or upgrade procedure
    '''
    @route("/:show=show")
    @expose_page(must_login=True, methods=['POST']) 
    def show(self, **kwargs):
    
        # Get a Splunk Web session key that will be used to get app state and other information via REST/Entity
        sessionKey = self.preReqProc.getSessionKey()

        logger.info("sk:" + sessionKey)
        
        output = jsonresponse.JsonResponse()
        output.data = []
        step = kwargs.get("step")
        
        ## On view initialization we check to see if the current app install is present or qualifies for upgrade
        ## JS will handle workflow control if any errors are encountered on this check
        if step == "check":
            try:

                #Get current Splunk server version
                currentServerVersion = self.preReqProc.getServerVersion(sessionKey)
                serverCompareResult = self.preReqProc.compareServerVersions(currentServerVersion, MIN_SPLUNK_VERSION)
                
                ## Get current and release app versions
                releaseVersion = self.preReqProc.getAppVersion(APP_NAME, sessionKey)
                installedVersion = self.preReqProc.getAppVersion(SRC_APP_NAME, sessionKey)
                self.INSTALLED_VERSION = installedVersion
        
                ## Get current and release app builds
                releaseBuild = self.preReqProc.getAppBuild(APP_NAME)
                installedBuild = self.preReqProc.getAppBuild(SRC_APP_NAME)
        
                installedAppList = self.preReqProc.getInstalledApps(SAVEDSEARCH_COMPONENTS_RE, sessionKey)
                isSuiteDisabled = self.preReqProc.checkAppsDisabled(installedAppList, sessionKey)

                # Compare this release version to the version currently installed and return an appropriate installation action
                # The module/view uses the installation action to present an appropriate workflow to the user
                [installAction, installedVersionBuild] = self.preReqProc.handleInstallationAction(releaseVersion, installedVersion, releaseBuild, installedBuild, UNSUPPORTED_VERSIONS, isSuiteDisabled, currentServerVersion, serverCompareResult)
                logger.info("step:check|" + "result:" + str([installAction, installedVersionBuild]))
                output.data.append(installAction)
                output.data.append(installedVersionBuild)

            except Exception as e:
                logger.error("step:check|" + str(e))            
                return self.render_error(_("step:check|" + str(e)))

        elif step == "package":
            try:
                
                # This step simply unpackages the source package within the workspace.
                # If needed, this really could be eliminated and folded into another step.
                self.packageProc.handleZipPackage(BASE_PATH, PACKAGE_SUBPATH, PACKAGE_SHELL_FILENAME)
                logger.info("step:package|" + "result:" + "Package found and unzipped")
                output.data.append("Package found and unzipped")

            except AssertionError as e:
                errMsg = "Package not found"
                logger.error("step:package|" + errMsg + "|" + str(e))
                return self.render_error(_("step:package|" + errMsg + "|" + str(e)))

            except Exception as e:
                logger.error("step:package|" + str(e))
                return self.render_error(_("step:package|" + str(e)))
        
        ## On view diff, display the files that are different between installed files vs originally shipped files
        elif step == "diff":
            try:
                # Create a map to contain the results of the diff - 'diff' files, 'extension' files, deprecated apps
                result = {}

                # check for existence of local navigation file that may override new default navigation
                localNav = self.navProc.getNav("local")
                result["localNav"] = localNav

                if (self.INSTALLED_VERSION.startswith("2.")):

                    invalidSuppressionSettingsDict, modifiedSearchesDict = ess_202_conversion.convertAggregateSettings(self.confProc.read_conf_file, self.confProc.write_conf_file, BASE_PATH, UPGRADE_WORKSPACE_SUBPATH, analyzeOnly=True)
                    result["aggregateSettingsIssues"] = invalidSuppressionSettingsDict
                    result["aggregateSearchIssues"] = modifiedSearchesDict

                ##### CUSTOMIZATION CONFLICT DETECTION
                confAppRE = re.compile("(DA-ESS-[a-zA-Z0-9-_]+)|(SA-[a-zA-Z0-9-_]+)|(SplunkEnterpriseSecuritySuite)")
                confFileRE = re.compile("savedsearches.conf$")
                confParamNameRE = re.compile("search")
                confParamValueRE = re.compile("\|\s*aggregate")
                
                #exclusions for $SPLUNK_HOME/etc/apps
                existingInstallPathExclusionsRE = re.compile("SplunkEnterpriseSecurityInstaller")
                
                #exclusions for $SPLUNK_HOME/etc/apps/SplunkEnterpriseSecurityInstaller/
                newPackagePathExclusionsRE = re.compile("local")
                
                ###====local====
                
                localConfPaths = self.ccp.getFilePaths(self.ccp.getBasePath(), confAppRE, confFileRE, existingInstallPathExclusionsRE, isLocal=True)
                
                localConfDict = self.ccp.getConfDicts(self.confProc.read_conf_file,localConfPaths)
                filteredlocalConfDict = self.ccp.filterStanzas(localConfDict, "(([^-]+)\s+-\s+([^-]+)\s+-\s+(Summary|Lookup)\s+Gen)")
                filteredlocalConfDictCorrSearch = self.ccp.filterStanzas(localConfDict, "(([^-]+)\s+-\s+([^-]+)\s+-\s+(Rule))")

                
                ###====default====
                
                defaultConfPaths = self.ccp.getFilePaths(os.path.join(self.ccp.getBasePath(),"SplunkEnterpriseSecurityInstaller","default","src","etc","apps"), confAppRE, confFileRE, newPackagePathExclusionsRE, isLocal=False)
                
                defaultConfDict = self.ccp.getConfDicts(self.confProc.read_conf_file,defaultConfPaths)
                
                filtereddefaultConfDict = self.ccp.filterStanzas(defaultConfDict, "(([^-]+)\s+-\s+([^-]+)\s+-\s+(TSIDX)\s+Gen)")
                
                defaultStanzaList = self.ccp.extractStanzaNamesFromDict(filtereddefaultConfDict)
                
                ###====compare====
                
                tsidxCompare = self.ccp.compareStanzaNames(filteredlocalConfDict,defaultStanzaList)
                
                ###====Navigation Lite View====
                
                navPath = os.path.join(bp.get_base_path(), "SplunkEnterpriseSecuritySuite", self.cxp.LOCAL_NAV_PATH)
                navLiteViews = self.cxp.checkCustomLiteNavXML(navPath, self.cxp.VIEW_TAG, self.cxp.NAME_ATT)
                
                ###====GLOBAL DEFAULT CONF CONFLICTS CHECK====
                installedVersion = self.preReqProc.getAppVersion(SRC_APP_NAME, sessionKey)
                diffComparisonFile = self.fileDiffProc.getComparisonFile(installedVersion, DIFF_PATH, fileExt="diff")
                
                if diffComparisonFile:
                    comparisonDict = self.fileDiffProc.compareDefaultConf(os.path.join(DIFF_PATH, diffComparisonFile), BASE_PATH)
                    comparisonResults = self.fileDiffProc.prettyPrintConfConflicts(comparisonDict)

                else:
                    comparisonResults = "Cannot locate conflict comparison file for version installed."

                result["conflicts"] = {"tsidx":tsidxCompare, "liteViews":navLiteViews, "globalConfConflicts":comparisonResults}

                ##### VERSION FILE COMPARISON
                
                # get the version of the currently installed app
                appVersion = self.preReqProc.getAppVersion(SRC_APP_NAME, sessionKey)
                
                # For the version installed, try to locate any hash filelist that is packaged with this installer
                # The hash filelist serves as the baseline to compare and determine any user customizations
                hashFilename = self.fileDiffProc.getHashFilename(appVersion, HASH_PATH)
                
                # Deprecated Apps
                deprecatedAppsFound = []
                for app in ESInstaller.DEPRECATED_FOLDERS:
                    if self.preReqProc.getAppVersion(app, sessionKey) is not None:
                        deprecatedAppsFound.append(app)

                result["deprecatedApps"] = deprecatedAppsFound
                result["deprecatedFiles"] = self.depProc.getDeprecateJSON(DEP_PATH)

                
                if hashFilename is None:
                    # set to None to indicate that a file diff is not available
                    result["diff"] = None
                    
                else:
                    
                    # set to something random, file diff is available
                    result["diff"] = "success"
                    
                    ## Get File diffs!!!
                    defaultFileList = self.fileDiffProc.getInstalledFileList(BASE_PATH, self.defaultRegexFilters, self.ignoreFilters)
                    defaultFileDiffOutput = self.fileDiffProc.handleFileDiff(defaultFileList, os.path.join(HASH_PATH, hashFilename), EXTENSIONS_OUTPUT_FILE)
    
                    ## This is a legacy output, but used in other installers.  We'll need to refactor handleFileDiff() to elminate.
                    extensionList = defaultFileDiffOutput[0]
                    
                    ## Strings used for response back to status view 
                    extensionListStr = defaultFileDiffOutput[1]
                    defaultListStr = defaultFileDiffOutput[2]
                    
                    result["defaultFiles"] = defaultListStr
                    result["extensionFiles"] = extensionListStr

                result["message"] = "File comparison complete"
                
                output.data.append(result)

                logger.info("step:diff|" + "result:" + "File comparison complete")
                
            except Exception as e:
                logger.error("step:diff|" + str(e))
                return self.render_error(_("step:diff|" + str(e)))


        ## - Copy UPGRADE_WORKSPACE_SUBPATH contents to etc/apps
        ## - Backup/archive current installation
        ## - Deploy and enable new installation
        elif step == "upgrade":
            try:
                result = {}

                # Back the current installation i.e. DA, SA, TA and main app to backup directory
                self.upgradeProc.backupCurrentInstallation(BASE_PATH, BACKUP_FOLDER_NAME, ESInstaller.DOMAIN_APP_FOLDERS)

                # remove any old navigators that would prevent new updates in default.xml
                localNav = self.navProc.getNav("local")
                self.navProc.deprecateNav(localNav)

                if (self.INSTALLED_VERSION.startswith("2.")):
                    ess_202_conversion.convertGovernanceControls(self.confProc.read_conf_file, self.confProc.write_conf_file, BASE_PATH, UPGRADE_WORKSPACE_SUBPATH)
                    invalidSuppressionSettingsDict, modifiedSearchesDict = ess_202_conversion.convertAggregateSettings(self.confProc.read_conf_file, self.confProc.write_conf_file, BASE_PATH, UPGRADE_WORKSPACE_SUBPATH, analyzeOnly=False)
                    #result["convertSettingsIssues"] = invalidSuppressionSettingsDict
                    #result["convertSearchIssues"] = modifiedSearchesDict

                """
                # Convert CSVs
                # If there are any changes to the column headers of the original filename.csv.default in the new package,
                # this updates the existing, already deployed CSV.  New columns will be filled with an empty string
                #
                # Add to this dictionary for additional CSVs to update
                # Format: {<APP_NAME_1> : [<LIST_OF_CSV_1>], <APP_NAME_2> : [<LIST_OF_CSV_2>] ...}
                """
                appCSVDict = {"SA-ThreatIntelligence": ["incident_review.csv"]}
                for app, csvList in appCSVDict.items():
                    for csvFile in csvList:
                        self.csvProc.handleUpgradeCSV(app, csvFile)

                # toggle SETUP for ESS
                self.installProc.set_app_is_configured(BASE_PATH, SRC_APP_NAME, isConfigured="0")
                
                # Deploy the new apps from the workspace
                self.installProc.installApps(os.path.join(BASE_PATH, UPGRADE_WORKSPACE_SUBPATH))
                
                # get list of relevant apps for following re-enable step
                installedAppList = self.preReqProc.getInstalledApps(SAVEDSEARCH_COMPONENTS_RE, sessionKey)
                
                #re-enable the apps after upgrade
                self.preReqProc.controlApps(installedAppList, sessionKey, control="enable")

                # get list of deprecated apps
                deprecatedAppList = self.preReqProc.getInstalledApps(ESInstaller.DEPRECATED_FOLDERS, sessionKey)
                # get list of apps to keep enabled post upgrade
                deprecatedKeepEnabledAppList = self.preReqProc.getInstalledApps(ESInstaller.DEPRECATED_FOLDERS_KEEP_ENABLED, sessionKey)
                # list of apps to disable post upgrade
                appDisableList = list(set(deprecatedAppList) - set(deprecatedKeepEnabledAppList))
                
                #disable deprecated apps
                self.preReqProc.controlApps(appDisableList, sessionKey, control="disable")
                
                result["upgradeMessage"] = "ES upgrade successful"
                
                #Append status message to response
                output.data.append(result)
                logger.info("step:upgrade|" + "result:" + "Files Migrated")
            except Exception as e:
                logger.error("step:upgrade|" + str(e))
                return self.render_error(_("step:upgrade|" + str(e)))

        elif step == "install":
            try:
                # Unpack the source zip file to the workspace
                self.packageProc.handleZipPackage(BASE_PATH, PACKAGE_SUBPATH, PACKAGE_SHELL_FILENAME)
                
                # Deploy the new apps
                self.installProc.installApps(os.path.join(BASE_PATH, UPGRADE_WORKSPACE_SUBPATH))
                
                # Trigger a Splunk restart via re-enabling this installer app
                self.preReqProc.controlApps([APP_NAME], sessionKey)
                
                #Append status message to response
                output.data.append("ES Installed")
                logger.info("step:install|" + "result:" + "ES Installed")
                
            except AssertionError as e:
                errMsg = "Package not found"
                logger.error("step:install|" + errMsg + "|" + str(e))
                return self.render_error(_("step:install|" + errMsg + "|" + str(e)))
                
            except Exception as e:
                logger.error("step:install|" + str(e))
                return self.render_error(_("step:install|" + str(e)))

        elif step == "disable":
            try:
                # get list of relevant apps
                installedAppList = self.preReqProc.getInstalledApps(SAVEDSEARCH_COMPONENTS_RE, sessionKey)
                
                # disable the apps
                self.preReqProc.controlApps(installedAppList, sessionKey, control="disable")
                
                #Append status message to response
                output.data.append("Apps Disabled")
                logger.info("step:disable|" + "result:" + "Apps Disabled")
            except Exception as e:
                logger.error("step:disable|" + str(e))
                return self.render_error(_("step:disable|" + str(e)))


        else:
        
            logger.error("step:unknown|" + str(e))
            return self.render_error(_("step:unknown|" + str(e)))

        return self.render_json(output)
    
    @route('/:save=save')
    @expose_page(must_login=True, methods=['POST']) 
    def save(self, **kwargs):
        pass

    # Return error response to the view if an exception is encountered        
    def render_error(self, msg):
        output = jsonresponse.JsonResponse()
        output.data = []
        output.success = False
        output.addError(msg)
        return self.render_json(output)        

if __name__ == "__main__":
    print "TEST-MAIN"
