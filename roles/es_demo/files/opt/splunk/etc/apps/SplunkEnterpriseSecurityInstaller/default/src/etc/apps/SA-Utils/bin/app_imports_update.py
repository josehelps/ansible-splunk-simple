"""
This class provides functions for managing app imports. This is necessary because Splunk doesn't allow wildcard for imports. 

Below is a list of the most relevant functions:

+-----------------------+---------------------------------------------------------------------------------------------------------+
|       Function        |                                                  Notes                                                  |
+-----------------------+---------------------------------------------------------------------------------------------------------+
| getCurrentImports     | Get the current list of imports for a given app                                                         |
| useGlobalImports      | Revert the app to using global imports (not app specific)                                               |
| removeAppFromImports  | Remove the given apps from the list of imports; will not do anything if the app is using global imports |
| setImports            | Set the imports for the given app                                                                       |
| updateMetaDataForApp  | Update the meta-data to include all of the apps that match the filter                                   |
| updateMetaDataForApps | Same as above but works against several apps                                                            |
+-----------------------+---------------------------------------------------------------------------------------------------------+

[Table above made at http://www.sensefulsolutions.com/2010/10/format-text-as-table.html]
"""

import splunk.models.app
import logging
import sys
import splunk.entity as entity
import splunk.rest

#Set up logging suitable for splunkd consumption
logging.root
logging.root.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.modinput import logger
from SolnCommon.modinput import ModularInput
from SolnCommon.modinput.fields import ListField, RegexField


class AppImportMetaDataUpdater(object):
    """
    This class will update the meta-data for applications such that they import other applications that match a particular naming scheme.
    
    This is necessary because app imports in Splunk does not currently support wildcards. Thus, you cannot import something like "TA-*". This
    class will update splunk to include all apps that match a regular expression which provides functionality similar to importing apps with a
    wildcard.
    """
    
    META_ENTRY_GLOBALS = "__globals__"
    
    @staticmethod
    def getApps( session_key = None ):
        return splunk.models.app.App.all(sessionKey=session_key)  
    
    @staticmethod
    def getListOfMatchingApps( app_regex, session_key = None, apps = None ):
        """
        Return a list of apps that match the given regex on the host.
        
        Arguments:
        app_regex -- A regular expression used to determine which apps to include in the imports.
        session_key -- The session key to use
        apps -- The list of apps (if you want to use an existing list); will be populated if none
        """
        
        if apps is None:
            apps = AppImportMetaDataUpdater.getApps( session_key )
        
        return [ app.name for app in apps if app_regex.match(app.name) ]    
    
    @staticmethod
    def removeMatchingApps( app_regex, apps ):
        """
        Remove the apps from the list that match the regex.
        
        Arguments:
        app_regex -- A regular expression that matches the apps to remove. If none, the apps are returned without modification.
        apps -- The apps to prune
        """
        
        if app_regex is None:
            return apps
        
        return [ app for app in apps if not app_regex.match(app) ] 
    
    @staticmethod
    def getImportRESTPath( app ):
        """
        Get the path for obtaining or modifying the list of apps imported by a given app.
        
        Arguments:
        app -- The app to get the list of imports from.
        """
        
        # https://127.0.0.1:8089/services/apps/local/DA-PCI-Requirement1/import
        return "/apps/local/%s/import" % (app)
    
    @staticmethod
    def getCurrentImports( app, session_key=None, exclude_globals_entry=False ):
        """
        Get the list of apps that are currently imported for a given app.
        
        Arguments:
        app -- The app to get the list of imports from.
        session_key -- The session key to use
        exclude_globals_entry -- Exclude the __globals__ entry
        """
        
        en = entity.getEntity('/apps/local/', app, uri=AppImportMetaDataUpdater.getImportRESTPath(app), sessionKey=session_key)
        
        # Don't include the __globals
        if exclude_globals_entry:
            return [ app for app in en['import'] if app != "__globals__" ]
        else:
            return en['import']
        
    @staticmethod
    def useGlobalImports( app, session_key=None ):
        """
        Revert imports back to the default imports.
        
        Arguments:
        app -- The app to update the meta-data for
        session_key -- The session key to use
        """
        
        response, content = splunk.rest.simpleRequest( AppImportMetaDataUpdater.getImportRESTPath(app), method='DELETE', raiseAllErrors=True, sessionKey=session_key)
        
        if response.status == 200:
            return True
        else:
            return False
        
    @staticmethod
    def removeAppFromImports( app, apps_to_remove, force=False, session_key=None ):
        """
        Remove the provided apps from the imports.
        
        Note that this will not have an effect for an app that is importing globally. 
        
        Arguments:
        app -- The app to update the meta-data for
        apps_to_remove -- An array of apps that ought to be remove from imports
        force -- Perform the update even if the meta-data doesn't need to be modified
        session_key -- The session key to use
        """
        
        imported_apps = AppImportMetaDataUpdater.getCurrentImports(app, session_key, exclude_globals_entry=True )
        
        new_list = []
        apps_removed = 0
        
        # Make a new list of the apps that ought to be imported
        for imported_app in imported_apps:
            
            if imported_app not in apps_to_remove:
                new_list.append(app)
            else:
                apps_removed = apps_removed + 1
        
        # Determine if any action is necessary
        if force or apps_removed > 0:
            logger.info("Removing %i apps from imports", apps_removed)
            
            # Perform the update
            if AppImportMetaDataUpdater.setImports(app, new_list, session_key):
                return apps_removed
            else:
                return False
            
        else:
            logger.info("No updates to since the apps to remove were not being imported")
            return apps_removed
        
        
    @staticmethod
    def setImports( app, app_imports, session_key=None):
        """
        Set the imports for the given app.
        
        Arguments:
        app -- The app to update the meta-data for
        app_imports -- An array of apps that ought to be imported
        session_key -- The session key to use
        """
        
        postargs = { 'import' : app_imports }
        logger.info("Setting imports, app=%s, import=%s", app, ", import=".join(app_imports))
        response, content = splunk.rest.simpleRequest( AppImportMetaDataUpdater.getImportRESTPath(app), postargs=postargs, method='POST', raiseAllErrors=True, sessionKey=session_key)
        
        if response.status == 200:
            return True
        else:
            return False
        
    @staticmethod
    def updateMetaDataForApp( app_regex, app, app_exclude_regex=None, session_key=None, force=False, apps=None ):
        """
        Update meta-data for the given app. Returns a boolean indicating if the action was successful.
        
        Arguments:
        app_regex -- A regular expression used to determine which apps to include in the imports
        app -- The app to update the meta-data for
        app_exclude_regex -- A regular expression used to determine which apps to exclude from the imports
        session_key -- The session key to use
        force -- Perform the update even if no resulting app import configuration would be no different
        apps -- The list of existing apps; will be populated automatically if none
        """
        
        # Get the apps if they were not provided
        if apps is None:
            apps = AppImportMetaDataUpdater.getApps( session_key=session_key )
        
        # Get a list of the apps by the app name
        installed_apps_by_name = [ tmp_app.name for tmp_app in apps ]
        
        # If the app isn't installed, then skip it
        if app not in installed_apps_by_name:
            logger.warning("App doesn't exist, thus the imports will not be adjusted, app=%s" % (app))
            return False
        
        # Get the apps that match the regex
        matching_apps = AppImportMetaDataUpdater.getListOfMatchingApps( app_regex, session_key=session_key, apps=apps )
        
        # Get the apps currently being imported by the app (but exclude the __globals__ meta entry)
        current_imports = AppImportMetaDataUpdater.getCurrentImports( app, session_key, exclude_globals_entry=True )
        
        # Build a list of all of the apps that we will need to be importing
        app_imports = []
        app_imports.extend(matching_apps)
        
        # Remove apps that match the exclude regex
        app_imports = AppImportMetaDataUpdater.removeMatchingApps(app_exclude_regex, app_imports)
        
        # By default, don't update the imports unless we find the need to do so
        imports_need_updating = False
        
        # Add the apps that are currently imported but not in our list that match the regex (in other words, carry over the existing imports too)
        for imported_app in current_imports:
            
            # If an imported app matches the exclusion filter, then prune it
            if app_exclude_regex is not None and app_exclude_regex.match(imported_app):
                imports_need_updating = True
            
            # Add the app to the list of imports if it was not already included and if it exists.
            # Don't add it to the list if it doesn't exist (we want to prune those that no longer exist)
            elif imported_app not in matching_apps and imported_app in installed_apps_by_name:
                app_imports.append(imported_app)
                
            # If the imported app was not in the list of apps (that is, it isn't installed anymore), then it is being pruned. We will need to update the imports.
            if imported_app not in installed_apps_by_name:
                imports_need_updating = True
        
        # Log the lists of apps we are looking to update or are already listed in the import list
        logger.debug("imports_need_updating=%s, matching_apps=%s, current_imports=%s", str(imports_need_updating), ",".join(matching_apps), ",".join(current_imports) )
        
        # Make sure we are actually making a change and do nothing if we are not.
        # We don't want to post an update to the imports unnecessarily since this may cause Splunk to request a restart in the UI.
        if not force and not imports_need_updating:
            
            # Determine if we have apps that we need to add. That is, do an update when an app matches the regex but was not in the current imports.
            for matching_app in matching_apps:
                if matching_app not in current_imports:
                    
                    imports_need_updating = True
                    break
                    
            # If the lists already match, then don't do anything
            if not imports_need_updating:
                logger.info("No updates to the meta-data were necessary since the list is already up-to-date")
                return False
        
        # Ok, let's save the changes
        return AppImportMetaDataUpdater.setImports(app, app_imports, session_key=session_key)
    
    @staticmethod
    def updateMetaDataForApps( app_regex, apps, app_exclude_regex=None, session_key = None, force=False ):
        """
        Update meta-data for the given apps.
        
        Arguments:
        app_regex -- A regular expression used to determine which apps to include in the imports.
        apps -- A list of apps to update the meta-data for.
        app_exclude_regex -- A regular expression used to determine which apps to always exclude from the imports.
        session_key -- The session key to use
        force -- Force an update even if it is not required
        """
        
        updated = 0
        
        # Get the list of existing apps and pass them in so that we don't have to keep reloading them
        existing_apps = AppImportMetaDataUpdater.getApps( session_key=session_key )
        
        # Update each app
        for app in apps:
            
            # Perform the updates
            if AppImportMetaDataUpdater.updateMetaDataForApp(app_regex, app, session_key=session_key, apps=existing_apps, force=force, app_exclude_regex=app_exclude_regex):
                updated = updated + 1
                
        return updated
            

class AppImportsUpdateInput(ModularInput):
    
    def __init__(self):

        scheme_args = {'title': "App Imports Update",
                       'description': "Updates the app imports with all apps matching a given regular expression.",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "false"}
        
        args = [
                ListField("apps_to_update", "Apps to Update", "A comma separated list of apps that ought to be updated", required_on_create=True, required_on_edit=True),
                RegexField("app_regex", "Application Regular Expression", "A regular expression that matches the apps you want included", required_on_create=True, required_on_edit=True),
                RegexField("app_exclude_regex", "Application Exclusion Regular Expression", "A regular expression that matches the apps you never want included", required_on_create=False, required_on_edit=False)
                ]
        
        ModularInput.__init__( self, scheme_args, args )
        
    def run(self, stanza):
        
        apps_to_update = stanza["apps_to_update"]
        app_regex = stanza["app_regex"]
        
        if "app_exclude_regex" in stanza:
            app_exclude_regex = stanza["app_exclude_regex"]
        else:
            app_exclude_regex = None
        
        apps_updated = AppImportMetaDataUpdater.updateMetaDataForApps(app_regex, apps_to_update, session_key=self._input_config.session_key, app_exclude_regex=app_exclude_regex)
        
        if app_exclude_regex is None:
            app_exclude_regex_str = ""
        else:
            app_exclude_regex_str = app_exclude_regex.pattern
        
        logger.info("Meta-data updated, apps_updated=%i, regex='%s', input='%s', exclude_regex='%s')" % ( apps_updated, ", ".join(apps_to_update), stanza, app_exclude_regex_str ) )
        
            
if __name__ == '__main__':
    import_update = AppImportsUpdateInput()
    import_update.execute()
    sys.exit(0)
