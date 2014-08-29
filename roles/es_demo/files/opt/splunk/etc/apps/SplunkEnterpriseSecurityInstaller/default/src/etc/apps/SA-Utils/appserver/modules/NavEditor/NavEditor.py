import logging
import controllers.module as module
import cherrypy

import lxml.etree as et
from splunk.appserver.mrsparkle.lib import viewconf
import splunk.entity as entity
import splunk.auth as auth
import splunk.rest as rest
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

import os
import re
import json
import traceback

logger = logging.getLogger('splunk.appserver.SA-Utils.modules.NavEditor')

from splunk.models.field import Field
from splunk.models.base import SplunkAppObjModel

class Navigation(SplunkAppObjModel):
    '''
    Represents the navigation for an app.
    '''
    
    resource = 'data/ui/nav'
    
    data     = Field(api_name='eai:data')

class NavEditor(module.ModuleHandler):

    # Shortcuts to the REST APIs
    REST_NAV = "data/ui/nav"
    REST_VIEWS = "data/ui/views"

    view_names = None

    # The list below defines the capabilities that will be checked for particular applications.
    # Hard-coding these is necessary because the permissions defined cannot be defined as 
    # arguments to the module in the view since these are only communicated to the python
    # code through the browser; this means that the users could manipulate them to change
    # which permissions are checked.
    CAPABILITIES_TO_CHECK = {
                                'SplunkEnterpriseSecuritySuite' : ['edit_es_navigation'],
                                'SplunkPCIComplianceSuite' : ['edit_pci_navigation']
                             }
    
    # By default, the following capabilities will be checked
    DEFAULT_CAPABILITIES_TO_CHECK = ['edit_navigation']

    def generateResults(self, views_in_scope, app, views_enabled=[], **args):
        
        # Make sure that the views_in_scope and views_enabled parameters are not a single item (convert it to a list if so)
        if isinstance(views_in_scope, basestring):
            views_in_scope = [ views_in_scope ]
            
        if isinstance(views_enabled, basestring):
            views_enabled = [ views_enabled ]
        
        # Prepare a response
        response = {}
        
        # Make sure the app argument was provided
        if app is None or len(app.strip()) == 0:
            response["message"] = "A valid app was not provided"
            response["success"] = False
            
            return json.dumps(response)
        
        # Get the things we need to check the capabilities
        user = auth.getCurrentUser()['name']
        session_key  = cherrypy.session['sessionKey']
            
        # Stop if the user does not have the require capabilities
        if NavEditor.hasCapabilitiesByApp( user, session_key, app) == False:
            response["message"] = "You do not have permission to edit the navigation"
            response["success"] = False
            
            return json.dumps(response)
        
        # Perform the changes
        try:
            
            # Update the navigation
            views_disabled = self.updateNav(views_enabled, views_in_scope, app)
            
            response["message"] = "Navigation successfully updated"
            response["views_set_disabled"] = str( views_disabled )
            response["success"] = True

        except Exception, e :
            
            tb = traceback.format_exc()
            
            response["message"] = str(e)
            response["trace"] = tb
            response["success"] = False

        # Return 
        return json.dumps(response)
    
    @staticmethod
    def getQualifiedIdentifier( element, parent_element, prefix = None ):
        """
        Produces an identifier for the given element that includes the elements full path in the XML tree.
        
        Arguments:
        element -- The element to get the identifier for
        parent_element -- The parent element of the one we are getting the identifier for
        prefix -- The qualified path of the parent as a string
        """
        
        # This array will be used to make the child identifier
        child_element_id = []
        
        # Add the prefix to the identifier
        if prefix is not None:
            child_element_id.append(prefix)
        
        # Add the parent tag to the identifier
        elif parent_element is not None and parent_element.tag in ["view", "collection", "a", "divider"]:
            child_element_id.append(NavEditor.getIdentifier(parent_element, normalize=False))
        #elif parent_element is not None:
        #    return None
        
        # Add the child identifier
        if element.tag in ["view", "collection", "a", "divider"]:
            child_element_id.append(NavEditor.getIdentifier(element, normalize=False))
        
        # Return none if the list is empty
        if len(child_element_id) == 0:
            return None
        
        # Get the child element identifier as a string, separated by slashes
        child_element_id_str = "/".join(child_element_id)
        
        # Return the resulting element
        return child_element_id_str
    
    @staticmethod
    def convertWildcardToRE( wildcard ):
        """
        Converts a wildcard string into a regex.
        
        Arguments:
        wildcard -- A wildcard string to convert to a regex
        """
        
        # Replace the *'s
        wildcard_tmp = re.sub("[*]", ".*", wildcard)
        
        # Replace the *'s
        wildcard_tmp = re.sub("[/]", "/", wildcard_tmp)
        
        # Compile and return the regex
        return re.compile(wildcard_tmp, re.I)
    
    @staticmethod
    def convertWildcardArrayToRE( wildcards ):
        """
        Converts a dictionary of tuples containing a wildcard string and a value into a array . Returns an array of tuples containing the 
        regex and the value (being the same value as was provided from the original).
        dictionary argument.
        
        Arguments:
        wildcards -- An array of tuples containing a wildcard string and the associated value; e.g. [ ("Access/*", True), ("flashtimeline", False) ] 
        """
        
        regexs = []
        
        # Iterate through each item and convert it
        
        for wildcard in wildcards:
            
            # Get the entries from the tuple
            w, v = wildcard
            
            # Convert the wildcard string to a regex
            regexs.append( ( NavEditor.convertWildcardToRE(w), v) )
            
        # Return the resulting dictionary
        return regexs
    
    @staticmethod
    def getStatus( qualified_identifier, filtering_rules, default=False):
        """
        Returns the status field associated with the given identifier.
        
        Arguments:
        qualified_identifier -- The fully qualified identifier for the element that we are doing a lookup on 
        filtering_rules -- A list of filtering rules the indicate whether a given item is to be included
        default -- The default value to be returned if the identifier does not match any filtering rules
        """
        
        # Convert the filtering rules to regexes
        filtering_rules_regex = NavEditor.convertWildcardArrayToRE(filtering_rules)
        
        for rule in filtering_rules_regex:
            
            r, v = rule
            
            if qualified_identifier is not None and r.match(qualified_identifier):
                return v
        
        # We didn't match any of the entries, return the default
        return default
    
    @staticmethod
    def getContentCount( element ):
        """
        Return the number of view items that actually provide content (i.e. href or view notes)
        
        Arguments:
        element -- The node to start counting the number of nodes
        """
        
        content_count = 0
        
        if element.tag in ["view", "a"]:
            content_count = content_count + 1
            
        for child in element:
            content_count = content_count + NavEditor.getContentCount(child)
        
        return content_count
    
    @staticmethod
    def convertViewToEditDict( d ):
        
        a = []
        
        for k, v in d.items():
            if v.strip().lower() in ["true", "1"]:
                a.append( (k, True) )
            else:
                a.append( (k, False) )
            
        return a
    
    @staticmethod
    def flattenViewToEditDictArray( array ):
        
        a = []
        
        for d in array:
            a.extend( NavEditor.convertViewToEditDict(d) )
            
        return a
    
    @staticmethod
    def pruneUnecessaryElements( child_element, parent_element = None ):
        """
        Removes items from the XML tree if it is unnecessary. Items will be considered unnecessary if:
        
         1) The item is a collection with no children
         2) If the item only has dividers as children
         
        Arguments:
        child_element -- The element to check to determine if it is unnecessary
        parent_element -- The parent where the remove() call is to be made to remove the item
        """
        
        # Indicates the number of items removed
        items_removed = 0
        
        # Only try to remove items if the parent is not none (since we cannot remove it otherwise)
        if parent_element is not None:
            
            # Determine if the element has no children and remove it if it has none
            if child_element.tag == "collection" and len(list(child_element)) == 0:
                parent_element.remove(child_element)
                items_removed = items_removed + 1
            elif child_element.tag == "collection":
                
                # Determine how many of the children have nodes with content
                content_count = NavEditor.getContentCount(child_element)
                
                # If none of the children have content (just dividers or empty collections, then prune it_
                if content_count == 0:
                    parent_element.remove(child_element)
                    items_removed = items_removed + 1
            
        # Recurse on the children
        else:
            
            for grandchild_element in child_element:
                items_removed = items_removed + NavEditor.pruneUnecessaryElements(grandchild_element, child_element)
        
        # Return the number of items removed
        return items_removed
    
    @staticmethod
    def filterNavXML( child_element, parent_element, filtering_rules, prefix = None, default=False ):
        """
        Apply the given filters to the XML and remove items as appropriate.
        
        Arguments:
        child_element -- The element to get the identifier for
        parent_element -- The parent element of the one we are getting the identifier for
        filtering_rules -- A list of filtering rules the indicate whether a given item is to be included
        prefix -- The qualified path of the parent as a string
        default -- The default value to return if the item could not be found
        """
        
        # The following indicates the number of items removed; note that the number of sub-elements removed will not be included. This means
        # that the removal of an element containing children will only be considered as one.
        items_removed = 0 
        
        # Get the full identifier for the given item
        qualified_id = NavEditor.getQualifiedIdentifier(child_element, parent_element, prefix)
        
        # Determine if the given element ought to be removed and remove it as appropriate
        if parent_element is not None and NavEditor.getStatus( qualified_id, filtering_rules, default ) == False:
            
            parent_element.remove(child_element)
            items_removed = items_removed + 1
            
            # IF we removed the child element then we do not need to continue examining the child's children since they would already be removed
            return items_removed
            
        # Recurse on the children elements
        for grandchild_element in child_element:
            items_removed = items_removed + NavEditor.filterNavXML( grandchild_element, child_element, filtering_rules, qualified_id, default)
            
        # Prune unnecessary items
        items_removed = items_removed + NavEditor.pruneUnecessaryElements(child_element, parent_element)
            
        # Return the number of items removed
        return items_removed
    
    @staticmethod
    def getViewNameFromData(data, key):
        """
        Get the name of the view from the data associated with the view.
        
        Arguments:
        data -- The text from eai:data
        key -- The name of entry for which the eai:data was pulled from (will be used if no title can be found)
        """
        
        # Try to get the name by parsing the view (works for advanced XML views)
        try:
            viewObj = viewconf.loads(data, key)
            return viewObj.get('label', key)
        except et.XMLSyntaxError:
            
            # If that fails, try getting the name from the title tag
            name = NavEditor.getViewNameFromTitleTag(data)
            
            # If that still didn't work, then just use the key
            if name is not None:
                return name
            else:
                return key
            
    @staticmethod
    def getViewNameFromTitleTag(data):
        """
        Gets the view name from the title tag. This is useful for obtaining the title from Splunk JS views.
        
        Arguments:
        data -- The text from eai:data
        """
        
        regex = re.compile("<title>([^<]*)</title>")
        r = regex.search(data)
        
        if len(r.groups()) > 0:
            return r.groups()[0]
    
    @staticmethod
    def getViewNames(session_key, app, user, force_refresh=False):
        """
        Gets the label for a given view.
        
        Arguments:
        session_key -- The session key to use for obtaining the list of views
        user -- The user to use when looking up the view names
        app -- The namespace to use when doing a lookup
        force_refresh -- Force a reload of the items from the REST endpoints; otherwise, cached entries will be used it available
        """
        
        # Return the cached entry if they exist
        if NavEditor.view_names is None or force_refresh == False:
            # Load the view names
            view_names_temp = {}
            
            # Get the view information from SplunkD
            views = entity.getEntities(NavEditor.REST_VIEWS, namespace=app, owner=user, sessionKey=session_key, count=-1)
            
            # Load each view
            for k, v in views.items():
                try:
                    viewObj = viewconf.loads(v.get('eai:data'), k)
                    view_names_temp[k] = viewObj.get('label', k)
                except et.XMLSyntaxError:
                    # This is likely an HTML page, just use the key
                    view_names_temp[k] = k
                    logger.warn("Unable to parse view, thus we could not get the label view_name=%s", k)
                    
            # Cache the results
            NavEditor.view_names = view_names_temp
            
        # Return the view name
        return NavEditor.view_names
            
    @staticmethod
    def getViewName(view, session_key, app, user, force_refresh=False, default=None):
        """
        Gets the label for a given view.
        
        Arguments:
        view -- The name of the view to look up
        session_key -- The session key to use for obtaining the list of views
        app -- The namespace to use when doing a lookup
        user -- The user to use when looking up the view names
        force_refresh -- Force a reload of the items from the REST endpoints; otherwise, cached entries will be used it available
        default -- The default value to return if the item could not be found
        """
        
        # Return the cached entry if they exist
        view_names = NavEditor.getViewNames(session_key, app, user, force_refresh)
            
        # Return the view name
        return view_names.get(view, default)
    
    @staticmethod
    def getViewLabelFromViewXML( xml_string ):
        """
        Obtains the view label from the provided XML document.
        
        Arguments:
        xml_string -- A string containing the view XML
        """
        
        view = et.XML(xml_string)
        
        # Find the label and get the 
        for label_element in view.xpath('//label'):
            return label_element.text
    
    @staticmethod
    def returnIfTrue( boolean, output_true, output_false="" ):
        """
        Returns the value corresponding to the provided boolean value. This is a helper function to simplify the view templates.
        """
        
        if boolean:
            return output_true
        else:
            return output_false
    
    @staticmethod
    def getIdentifier(element, normalize=True):
        """
        Returns a string which uniquely identifies the view element.
        
        Arguments:
        element -- An XML element from the navigation XML
        normalize -- Include the tag type (view, collection) in the identifier and normalize the characters ("Search Activity" will become "search_activity")
        """
        
        type = None
        value = None
        
        # Load the element into a NavElement object
        if element.tag == "view":
            value = element.attrib["name"]

        elif element.tag == "collection":
            value = element.attrib["label"]

        elif element.tag == "a":
            
            if element.text is not None and len(element.text) != 0:
                value = element.text
            else:
                value = element.attrib["href"]

        elif element.tag == "divider":
            return element.tag
        else:
            return element.tag
        
        if normalize:
            return element.tag + "_" + re.sub("[^a-zA-Z0-9_]{1,3}", "_", value).lower()
        else:
            return value #re.sub("[^a-zA-Z0-9_]{1,3}", "_", value).lower()
    
    @staticmethod
    def isViewEnabled(element, status_dict, default=False):
        """
        This is a helper function that will indicate if the given element
        
        Arguments:
        element -- The XML element that represents a view item
        status_dict -- A dictionary indicating which views are enabled (consisting keys with the identifier and value with a boolean); can be obtained from NavEditor.compareXML()
        default -- The default value that should be returned if the item was not found in the status_dict
        """
        
        id = NavEditor.getIdentifier(element)
        
        if id in status_dict:
            return status_dict[id]
        else:
            return default
    
    @staticmethod
    def getDescription(element, view_names=None):
        """
        Returns a user friendly string description of the item.
        
        Arguments:
        element -- The XML element that represents a view item
        view_names -- A dictionary including the names/labels mapped to the view identifier
        """
        
        # Load the element into a NavElement object
        if element.tag == "view":
            
            # Get the view name
            name = element.attrib["name"]
            
            # Try to get the view label
            if view_names is not None and name in view_names:
                return view_names[name]
            
            # Return the name of the view if we could not get the label
            return name

        elif element.tag == "collection":
            return element.attrib["label"]

        elif element.tag == "a":
            
            if element.text is not None and len(element.text) != 0:
                return element.text
            else:
                return element.attrib["href"]

        elif element.tag == "divider":
            return ""
        else:
            return element.tag
    
    @staticmethod
    def getCombinedNavDocXML(app, filtering_rules=None) :
        """
        Get navigation XML containing the default XML plus custom views that exist only in the local XML.
        
        Argument:
        app -- The app with the nav file to load
        filtering_rules -- A list of filtering rules the indicate whether a given item is to be included
        """
        
        default_xml = NavEditor.getDefaultNavDocXML(app, filtering_rules)
        
        local_xml = NavEditor.getLocalNavDocXML(app, filtering_rules)
        
        if local_xml is not None:
            NavEditor.integrateCustomViews(default_xml, local_xml)
        
        return default_xml
        
    @staticmethod
    def getDefaultNavDocXML(app, filtering_rules=None) :
        """
        Get the default nav XML file in an XML document.
        
        Argument:
        app -- The app with the nav file to load
        filtering_rules -- A list of filtering rules the indicate whether a given item is to be included
        """
        
        return NavEditor.getNavDocXML(app, False, filtering_rules)
    
    @staticmethod
    def getLocalNavDocXML(app, filtering_rules=None) :
        """
        Get the local nav XML file in an XML document.
        
        Argument:
        app -- The app with the nav file to load
        filtering_rules -- A list of filtering rules the indicate whether a given item is to be included
        """
        
        return NavEditor.getNavDocXML(app, True, filtering_rules)
    
    @staticmethod
    def getNavDocXML(app, local=True, filtering_rules=None) :
        """
        Get the default nav XML file in an XML document.
        
        Argument:
        app -- The app with the nav file to load
        local -- Get the local version of nav file; otherwise, get the default nav file
        filtering_rules -- A list of filtering rules the indicate whether a given item is to be included
        """
        
        # Determine which version of the nav to load
        if local:
            nav_type = "local"
        else:
            nav_type = "default"
        
        # Get the path to the nav.xml file
        navPath = make_splunkhome_path(['etc', 'apps', app, nav_type, 'data', 'ui', 'nav', 'default.xml'])
        
        # Get the xml file and parse it into a document
        try:
            navStr = open(navPath, 'rb').read()
        except IOError:
            return None
        
        # Convert the string to an XML document
        xml = et.XML(navStr)
        
        # Apply the filtering rules if provided
        if filtering_rules is not None:
            NavEditor.filterNavXML(xml, None, filtering_rules)
            
        # Return the XML document
        return xml
          
    @staticmethod
    def compareElements(a, b):
        """
        Compare two XML Elements to determine if they are equivalent.
        
        Arguments:
        a -- The first item to compare
        b -- The second item to compare
        """
        if NavEditor.getIdentifier(a) == NavEditor.getIdentifier(b):
            return True
        else:
            return False
    
    @staticmethod
    def hasCapabilitiesByApp( user, session_key, app ):
        """
        Determine if the user has the capabilities. Which capabilities are to be checked will be checked is 
        determined based on what app is requesting the check. See NavEditor.CAPABILITIES_TO_CHECK
        
        Arguments:
        user -- The user to be checked
        session_key -- The session to use when checking permissions
        app -- The app whose navigation is to be updated
        """
        
        required_capabilities = NavEditor.DEFAULT_CAPABILITIES_TO_CHECK
        
        # Get the app specific capabilities to check
        if app in NavEditor.CAPABILITIES_TO_CHECK:
            required_capabilities = NavEditor.CAPABILITIES_TO_CHECK[app]
            
        # Check the capabilities
        return NavEditor.hasCapabilities( user, session_key, required_capabilities)
    
    @staticmethod
    def hasCapabilities( user, session_key, required_capabilities ):
        """
        Determine if the user has the capabilities.
        
        Arguments:
        user -- The user to be checked
        session_key -- The session to use when checking permissions
        required_capabilities -- The list of capabilities that that user must have
        """
        
        roles = []
        capabilities = []
        
        # Default to 'admin_all_objects'
        if required_capabilities is None:
            required_capabilities = ["admin_all_objects"]
        
        # Get the user entity info
        user_entity = entity.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
    
        # Find the user information
        for stanza, settings in user_entity.items():
            
            if stanza == user:
                
                # Find the roles information
                for key, val in settings.items():
                    if key == 'roles':
                        roles = val
             
        # Get capabilities
        for role in roles:
            
            role_entity = entity.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
            
            # Get the imported capabilities
            for stanza, settings in role_entity.items():
                
                # Populate the list of capabilities
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            capabilities.extend(val)
                            
            
        # Make sure the user has the required_capabilities
        for capability in required_capabilities:
            
            # Indicate that the user does not have permission if they do not have a given capability
            if capability not in capabilities:
                return False
            
        # All capabilities matched, return true indicating that they have permission
        return True
    
    @staticmethod
    def getNavDifferences( app ):
        """
        Compares the default and local navigation XML documents and returns a dictionary indicating which
        views are not present in the local navigation file (which indicates that they are disabled).
        
        Arguments:
        app -- The application containing the views to be compared
        """
        
        # Get the default nav document
        default_nav = NavEditor.getDefaultNavDocXML(app)
        
         # Get the local nav document
        local_nav = NavEditor.getLocalNavDocXML(app)
        
        # If the local navigation file does not exist, then just return an array with all of the values set to enabled
        if local_nav is None:
            local_nav = default_nav
        
         # Compare the documents
        return NavEditor.compareXML(default_nav, local_nav)
    
    @staticmethod
    def areElementsEquivalent( a, b ):
        """
        Determines if the given elements are equivalent.
        
        Arguments:
        a -- The first item to compare
        b -- The second item to compare
        """
        
        return NavEditor.getIdentifier(a) == NavEditor.getIdentifier(b)
    
    @staticmethod
    def integrateCustomViews( element_standard, element_custom ):
        """
        Takes items that exist in the elements in the second argument back into the first. This is useful in cases where
        additional views exist and need to be re-added.
        
        Arguments:
        element_standard -- The element to incorporate differences into
        element_custom -- The element to get the custom views from
        """
        
        views_added = 0
        pointer_standard = -1 # Represents the last place where the two nodes matched up
        pointer_custom = 0 # Represents where in the custom XML we currently are
        
        for custom_child in element_custom:
            
            # This is the element that we matched as being in both views
            standard_child_matched = None
            
            # Found out if and where the two elements and match
            for standard_child in element_standard:
                
                # Do the elements match? If so remember this as the last place we found a match
                if NavEditor.areElementsEquivalent(standard_child, custom_child):
                    pointer_standard = pointer_custom
                    standard_child_matched = standard_child
                    break
            
            # Add the element if it is new
            if standard_child_matched is None:
                
                # If we have not seen any matches yet, then add the item to the beginning; otherwise add it after the last matching location
                if pointer_standard < 0:
                    insert_at = 0
                else:
                    insert_at = pointer_standard + 1
                
                # Add the item
                element_standard.insert(insert_at, custom_child)
                
                # Increment the number of views added
                views_added = views_added + 1
            else:
                # If these are matching, then continuing integrating down the tree
                views_added = views_added + NavEditor.integrateCustomViews( standard_child_matched, custom_child)
            
            # Increment the count offset
            pointer_custom = pointer_custom + 1
                
        return views_added
    
    @staticmethod
    def compareXML(default_nav, local_nav):
        """
        Compare two XML documents corresponding to the default and local navigation XML documents and return
        a dictionary indicating which views are not present in the local navigation file (which indicates that
        they are disabled).
        
        Arguments:
        default_nav -- An XML document representing the default navigation file
        local_nav -- An XML document representing the local navigation file
        """
        
        # This dictionary will contain a series of identifiers that can be used to determine if the given item was not in the local version of the nav
        status_dict = {}
        
        # Iterate through each entry see if the local nav excludes it
        for d in default_nav.getiterator():
            
            # Ignore the root nav node
            if d.tag == "nav":
                continue
            
            # Assume that a match was not found unless we prove otherwise
            match_found = False
            
            # Iterate through the local nav and see if we can find the given view
            for l in local_nav.getiterator():
                if NavEditor.compareElements( d, l ):
                    
                    # Note that we found a match
                    match_found = True
                    status_dict[ NavEditor.getIdentifier(d) ] = True
                    break
                
            # If we didn't found a match, then denote the item accordingly
            if not match_found:
                status_dict[ NavEditor.getIdentifier(d) ] = False
        
        # Return the status dictionary
        return status_dict
    
    @staticmethod
    def removeElements( element, views_to_remove ):
        """
        Removes the navigation elements that correspond to the ones that match those in the views_to_remove list.
        Returns an integer indicating how many XML nodes were removed.
        
        Arguments:
        element -- An XML element corresponding to that found in navigation XML
        views_to_remove -- A list of views to remove (identified by a string that was created by NavEditor.getIdentifier)
        """
        
        # The following will record how many entries we deleted
        deleted = 0
        
        # Iterate through the list and remove the disabled items
        for child in element:
            
            # Remove the item if it matches one of the items that we are supposed to disable
            id = NavEditor.getIdentifier(child)
            
            if id in views_to_remove:
                element.remove(child)
                deleted = deleted + 1
            else:
                deleted = deleted + NavEditor.removeElements( child, views_to_remove)
                
        # Return the number of entries removed
        return deleted
    
    def updateNav(self, views_enabled, views_in_scope, app):
        """
        Update the XML such that the views that have selected as disabled are removed from the local version of the navigation file.
        
        Arguments:
        views_enabled -- A list of views that are to be enabled (identified by a string that was created by NavEditor.getIdentifier)
        views_in_scope -- A list of the views that are considered "in-scope"; views that are not in the given list will be ignored
        app -- The app context to apply the changes to
        """
        
        # Obtain a list of the views that are to be in a disabled state
        views_disabled = list(set(views_in_scope) - set(views_enabled))
        
        # Get the XML so that we can remove the disabled elements 
        nav = NavEditor.getCombinedNavDocXML(app)
        
        NavEditor.removeElements(nav, views_disabled)
        NavEditor.pruneUnecessaryElements(nav, None)
         
        # Save the changes to disk
        self.saveNavDocXML(app, nav)
        
        # Return the views to be disabled
        return views_disabled
        
        
    def saveNavDocXML(self, app, nav_xml) :
        """
        Save the given XML version of the nav file to the local nav file. Returns a boolean indicating whether the save was successful.
        
        Arguments:
        app -- The app/namespace where the updated nav will be written to
        nav_xml -- An XML string representing the new navigation
        """
        
        # Get the username and session key
        currentUser = auth.getCurrentUser()['name']
        sessionKey  = cherrypy.session['sessionKey']
        
        # Save the XML to the REST endpoint
        nav = Navigation.get( Navigation.build_id( "default", app, currentUser) )
        nav.data = et.tostring(nav_xml)
        return nav.save()
    