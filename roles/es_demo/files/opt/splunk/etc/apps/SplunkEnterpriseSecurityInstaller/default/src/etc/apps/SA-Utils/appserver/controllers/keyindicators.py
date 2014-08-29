import logging
import os
import sys
import json
import shutil
import csv
import cherrypy
import re
import operator

from splunk import AuthorizationFailed as AuthorizationFailed
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
import splunk.bundle as bundle
import splunk.entity as entity
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import splunk.clilib.bundle_paths as bundle_paths
from splunk.util import normalizeBoolean as normBool
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.models.saved_search import SavedSearch, ActionField
from splunk.models.field import Field, BoolField, StructuredField, IntField


import splunk.search

"""
The model are not yet used because no one in engineering can tell me how to use them to save custom alert actions.
"""
class ActionFieldEx(ActionField):
    
    class KeyIndicatorActionField(StructuredField):
        '''
        Represents the summary indexing configuration
        '''
        
        enabled = BoolField('action.keyindicator')
        delta   = Field()

class SavedSearchEx(SavedSearch):
    action = ActionFieldEx()
    
    def _calc_actions_list(self):
        actions_list = super(SavedSearch, self)._calc_actions_list()
        
        # Added support for the key indicators alert action here:
        if self.action.keyindicator.enabled:
            actions_list.append('keyindicator')
        
        return actions_list

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('splunk.appserver.SA-Utils.controllers.KeyIndicators')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'key_indicators_controller.log']), maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.DEBUG)

class PermissionDeniedException(Exception):
    pass
    
class KeyIndicator():
    '''
    Represents a particular key indicator.
    '''
    
    def __init__(self, order=None, search=None, threshold=None):
        self.order = order
        self.search = search
        self.threshold = threshold
        
    def __str__(self):
        return self.search + "@" + str(self.order)
    
class KeyIndicators(controllers.BaseController):
    '''Key Indicators Controller'''
 
    KEY_INDICATOR_GROUP_NUMBER_RE = re.compile("action[.]keyindicator[.]group[.]([0-9]+)[.](.*)")
    KEY_INDICATOR_GROUP_NAME_RE   = re.compile("action[.]keyindicator[.]group[.]([0-9]+)[.]name")
    SAVED_SEARCHES_REST_URL       = '/saved/searches/'
    DEFAULT_OWNER                 = 'nobody'
    DEFAULT_NAMESPACE             = 'SA-ThreatIntelligence'
      
    def render_error_json(self, msg):
        """
        Render an error such that it can be returned to the client as JSON.
        
        Arguments:
        msg -- A message describing the problem (a string)
        """
        
        output = jsonresponse.JsonResponse()
        output.data = []
        output.success = False
        output.addError(msg)
        return self.render_json(output, set_mime='text/plain')
    
    def update_indicators_order_value(self, indicators):
        """
        Assigns the key indicators' order value according to order that they are in the array.
        
        Arguments:
        indicators -- An array of KeyIndicator instances
        """
        
        n = 0
        
        for indicator in indicators:
            indicator.order = n
            n = n + 1
            
        return indicators
    
    @staticmethod
    def sort_key(x):
        """
        Provides the integer that should be used for sorting indicators (based on the order attribute or the position in the array).
        
        Arguments:
        x -- A tuple containing the index of the indicator followed by a KeyIndicator instance
        """
        
        if x[1].order is not None:
            return x[1].order
        else:
            return x[0]
    
    def get_indicators_list(self, args):
        """
        Get a list of the indicators being specified by the arguments. These arguments are those that come from a browser and represent what key indicators ought to be shown.
        
        The arguments should look like:
        group_name: the key indicators group
        indicator.<x>.search: the search that provides the results for the indicator
        indicator.<x>.order: the order of the indicator (i.e. the order that it is represented on the dashboard)
        indicator.<x>.threshold: the threshold value to set
        
        Note that <x> will be an integer (e.g. "indicator.0.search")
        
        Arguments:
        args -- List of arguments from a POST that represent key indicator settings.
        """
        
        regex = re.compile("indicator[.]([0-9]+)[.](.*)")
        indicators = {}
        
        for k, v in args.items():
            m = regex.match(k)
            
            # If the argument appears to be for an indicator, then handle it
            if m:
                results = m.groups()
            
                # Get the ID (for the order) and the parameter being set
                id = int(results[0])
                param = results[1]
                
                # Make an indicator to represent the item
                if id not in indicators:
                    indicators[id] = KeyIndicator()
                    
                # Get the parameters
                if param == "search":
                    indicators[id].search = v
                elif param == "threshold":
                    if len(v) == 0:
                        indicators[id].threshold = ""
                    else:
                        indicators[id].threshold = v
                elif param == "order":
                    indicators[id].order = int(v)
        
        # Make a sorted array of the IDs
        indicators_sorted = sorted(indicators.items(), key=KeyIndicators.sort_key)
        
        return [x[1] for x in indicators_sorted]
    
    @staticmethod
    def get_group_number(search, group_name):
        """
        Get the group number associated with the group name within the given search. Returns None if no key indicator group is associated with the search.
        
        Arguments:
        search -- An entity object representing a search.
        group_name -- the key indicator group name that is used to group key indicators together on a single panel; dashboards use the group name to find the indicators they are to display.
        """
        
        for k, v in search.items():
            m = KeyIndicators.KEY_INDICATOR_GROUP_NUMBER_RE.match(k)
            
            if m:
                
                field_name = m.groups()[1]
                number = int(m.groups()[0])
                
                if field_name == "name" and v == group_name:
                    return number
            
        return None
    
    @staticmethod
    def highest_group_number(search):
        """
        Get the highest key indicator group number within the given search. Returns -1 if no key indicator group was found.
        
        Arguments:
        search -- An entity object representing a search.
        """
        
        highest_group_number_thus_far = -1
        
        for k, v in search.items():
            m = KeyIndicators.KEY_INDICATOR_GROUP_NUMBER_RE.match(k)
            
            if m:
                number = int(m.groups()[0])
                
                if number > highest_group_number_thus_far:
                    highest_group_number_thus_far = number
            
        return highest_group_number_thus_far
    
    @staticmethod
    def is_in_group(search, group_name):
        """
        Determine if a key indicator exists within the given search for the key indicator group.
        
        Arguments:
        search -- An entity object representing a search.
        group_name -- the key indicator group name that is used to group key indicators together on a single panel; dashboards use the group name to find the indicators they are to display.
        """
        
        number = KeyIndicators.get_group_number(search, group_name)
        
        if number is not None:
            return True
        else:
            return False
    
    @staticmethod
    def get_existing_indicators(group_name):
        """
        Get the existing key indicator searches that use the given group name.
        
        Arguments:
        group_name -- the key indicator group name that is used to group key indicators together on a single panel; dashboards use the group name to find the indicators they are to display.
        """
        
        #saved_searches = splunk.search.listSavedSearches(count=-1)        
        saved_searches = entity.getEntities(KeyIndicators.SAVED_SEARCHES_REST_URL,
                                      namespace  = KeyIndicators.DEFAULT_NAMESPACE,
                                      owner      = KeyIndicators.DEFAULT_OWNER,
                                      #sessionKey = cherrypy.session.get('sessionKey'),
                                      count      = -1)
        
        key_indicator_searches = {}
        
        for search_name in saved_searches:
            search = saved_searches[search_name]
            
            if "action.keyindicator" in search and KeyIndicators.is_in_group(search, group_name):
                key_indicator_searches[search_name] = search
        
        return key_indicator_searches
    
    def assign_params(self, search, group_number, indicator, group_name ):
        """
        Modify the given search to correspond to the indicator provided.
        
        Arguments:
        search -- An entity object representing a search.
        group_number -- The integer indicating which indicator group is being referred to. The stanza "action.keyindicator.group.0.name" is key indicator is 0.
        indicator -- A KeyIndicator instance.
        group_name -- the key indicator group name that is used to group key indicators together on a single panel; dashboards use the group name to find the indicators they are to display.
        """
        
        search["action.keyindicator.group." + str(group_number) + ".name"] = group_name
        search["action.keyindicator.group." + str(group_number) + ".order"] = indicator.order
        
        if indicator.threshold is not None:
            search["action.keyindicator.threshold"] = indicator.threshold
        
        logger.debug("Setting params for group %s and group number %i to order %i", group_name, group_number, indicator.order)
    
    def save_search_entity(self, search):
        """
        Update the given search and remove the display parameters which Splunk chokes on.
        
        Arguments:
        search -- An entity object representing a search.
        """
        
        # Remove the pesky display params that never save correctly anyways
        for k in search:
            if k.startswith("display."):
                search[k] = None # Remove this attribute because Splunk doesn't like it :(
                
        entity.setEntity(search)
    
    def update_search(self, search, search_name, indicator, group_name, save=True):
        """
        Update the given search to include the given indicator. Returns a boolean indicating if a new key indicators entry had to be created (as opposed to editing an existing entry).
        
        Arguments:
        search -- An entity object representing a search.
        search_name -- The name of the search
        indicator -- A KeyIndicator instance.
        group_name -- the key indicator group name that is used to group key indicators together on a single panel; dashboards use the group name to find the indicators they are to display.
        save -- indicates whether the updated search should be saved. If false, then the search objects will be updated but will not be persisted in conf files.
        """
        
        # See if the search has a key indicator action entry
        existing_group_number = KeyIndicators.get_group_number(search, group_name)
        
        if existing_group_number is not None:
            # We are updating an existing entry
            self.assign_params(search, existing_group_number, indicator, group_name)
        else:
            # We are adding a new entry
            group_number = KeyIndicators.highest_group_number(search) + 1
            
            self.assign_params(search, group_number, indicator, group_name)
        
        # Save the entry if necessary
        if save:
            self.save_search_entity(search)
            
        # Return a boolean indicated if we created a new entry
        if existing_group_number is None:
            return False
        else:
            return True
    
    def get_indicators_to_remove(self, existing_indicator_searches, indicators_to_save):
        """
        Determines and returns a list of search names that are no longer associated with the key indicator group.
        
        Arguments:
        existing_indicator_searches -- A list of saved search instances
        indicators_to_save -- an array of KeyIndicator instances the represents the items we are saving
        """
        
        indicators_to_remove = []
        
        for search_name in existing_indicator_searches:
            
            found = False
            
            for indicator in indicators_to_save:
                if search_name == indicator.search:
                    found = True
                    break
            
            if not found:
                indicators_to_remove.append(search_name)
                    
        return indicators_to_remove
    
    def remove_unneeded_indicators(self, existing_indicator_searches, indicators_to_save, group_name, save=True):
        """
        Find indicators that ought not to be linked to the group anymore and disassociate them.
        
        Arguments:
        existing_indicator_searches -- A list of saved search instances
        indicators_to_save -- an array of KeyIndicator instances the represents the items we are saving
        group_name -- the key indicator group name that is used to group key indicators together on a single panel; dashboards use the group name to find the indicators they are to display.
        save -- indicates whether the updated search should be saved. If false, then the search objects will be updated but will not be persisted in conf files.
        """
        
        indicators_removed = 0
        
        # Get the list of indicators that need to be removed
        indicators_to_remove = self.get_indicators_to_remove(existing_indicator_searches, indicators_to_save)
        
        # Go through the list and update the relevant searches
        for indicator_to_remove in indicators_to_remove:
            
            # Get the search
            search_to_update = existing_indicator_searches[indicator_to_remove]
                
            # Find the indicator group and clear the group name
            for k, v in search_to_update.items():
                
                # Determine if this is a group name stanza
                m = KeyIndicators.KEY_INDICATOR_GROUP_NAME_RE.match(k)
                
                # If this is an entry for this group, then lets clear it
                if m and v == group_name:
                    search_to_update[k] = ""
                    indicators_removed = indicators_removed + 1
                    
                    # Save it
                    if save:
                        self.save_search_entity(search_to_update)
                    
        return indicators_removed 
    
    def save_indicators(self, indicators_to_save, group_name, save=True):
        """
        Save the indicators provided.
        
        Arguments:
        indicators_to_save -- an array of KeyIndicator instances the represents the items we are saving
        group_name -- the key indicator group name that is used to group key indicators together on a single panel; dashboards use the group name to find the indicators they are to display.
        save -- indicates whether the updated search should be saved. If false, then the search objects will be updated but will not be persisted in conf files.
        """
        
        # Get a list of the existing indicators so that we can determine which must be removed
        existing_indicator_searches = KeyIndicators.get_existing_indicators(group_name)
        
        # For each indicator, create or modify the associated alert action
        for indicator in indicators_to_save:
            
            existing_search = None
            search_name = None
            
            # Find the existing indicator search
            for search_name in existing_indicator_searches:
                
                if search_name == indicator.search:
                    existing_search = existing_indicator_searches[search_name]
                    break
            
            # Update the search
            if existing_search is not None:
                if self.update_search(existing_search, search_name, indicator, group_name, save=save):
                    logger.info("Updated search %s", search_name)
                else:
                    logger.info("Failed to update search %s", search_name)
            
            # Associate a new search  
            else:
                search = entity.getEntity(KeyIndicators.SAVED_SEARCHES_REST_URL,
                                          indicator.search,
                                          namespace = KeyIndicators.DEFAULT_NAMESPACE,
                                          owner = KeyIndicators.DEFAULT_OWNER )
                
                # Note that we edited this entry by adding it to the list
                existing_indicator_searches[indicator.search] = search
                
                if self.update_search(search, indicator.search, indicator, group_name, save=save):
                    logger.info("Updated search to add new group association %s", indicator.search)
                else:
                    logger.info("Failed to update search with new group association %s", indicator.search)
        
        # Remove the items that were eliminated
        self.remove_unneeded_indicators(existing_indicator_searches, indicators_to_save, group_name, save=save)
        
        return existing_indicator_searches
    
    @expose_page(must_login=True, methods=['POST']) 
    def update(self, group_name, **kwargs):
        """
        This is the main entry point for updating key indicators.
        
        Arguments:
        group_name -- the key indicator group name that is used to group key indicators together on a single panel; dashboards use the group name to find the indicators they are to display.
        kwargs -- Other arguments that should represent indicators
        """
        
        indicators_to_save = self.get_indicators_list(kwargs)
        
        logger.info("About to set the configuration for group_name=%s; indicators=i%", group_name, len(indicators_to_save))
        
        updated_indicator_searches = self.save_indicators(indicators_to_save, group_name)
        
        return self.render_json( {
                                  'indicators_to_save' : len(indicators_to_save),
                                  'updated_indicator_searches' : len(updated_indicator_searches)
                                  } )
        