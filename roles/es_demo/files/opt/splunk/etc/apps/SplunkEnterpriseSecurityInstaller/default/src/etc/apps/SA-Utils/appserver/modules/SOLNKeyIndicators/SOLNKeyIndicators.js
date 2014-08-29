/**
 * Copyright (C) 2009-2013 Splunk Inc. All Rights Reserved.
 */

Splunk.Module.SOLNKeyIndicators = $.klass(Splunk.Module, {
    
    /**
     * Initialize the class. Get the arguments from the data nodes attached to the container class that indicates the number of 
     * searches to run concurrently and the group name.
     */
    initialize: function($super, container) {
        var retVal = $super(container);
        this.next_panel_offset = 0;
        var group_name = $(".KP-main", this.container).attr("data-group-name");
        this.concurrent_searches_limit = $(".KP-main", this.container).attr("data-concurrent-searches");
        
        // If we got a group name, then get the list of searches and kick them off
        if( group_name !== undefined ){
            this.getPanels( group_name );
        }
        
        return retVal;
    },
    
    /**
     * Dispatch the search with the name provided so that it can begin obtaining results.
     */
    dispatchSearch: function(savedsearch_name){
        
        var params = new Object();
        params.output_mode = 'json';
        
        var uri = Splunk.util.make_url('/splunkd/__raw/services/saved/searches/', encodeURIComponent(savedsearch_name), '/dispatch');
        uri += '?' + Splunk.util.propToQueryString(params);

        var sid = null;
        
        jQuery.ajax({
            url:     uri,
            type:    'POST',
            cache:   false,
            success: function(result) {
                 if(result.isOk === false){
                     alert(result.message);
                 }
                 else{
                     sid = result.sid; 
                 }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                 sid = null;
                 console.error("Unable to dispatch search: " + savedsearch_name);
            },
            async:   false
        });
        
        return sid;
        
    },
    
    /**
     * Returns true if the provided string starts with the given sub-string.
     */
    stringStartsWith: function(str, startsWith){
        return str.slice(0, startsWith.length) == startsWith;
    },
    
    /**
     * Returns true if the provided string ends with the given sub-string.
     */
    stringEndsWith: function(str, endsWith){
        return str.slice(-endsWith.length) == endsWith;
    },
    
    /**
     * Get the group number for the alert action statements in the search provided if the group name matches. If the search is not for this group, then no number will be returned. 
     */
    getGroupNumber: function( group_name, search ){
        
        var re = new RegExp("action[.]keyindicator[.]group[.]([0-9]+)[.]name");
        
        // Look for the name attribute
        for( attribute in search.content ){
            
            var match = re.exec(attribute);
            
            // Get the group number
            if( match && search.content[attribute] == group_name ){
                return parseInt(match[1], 10);
            }
        }
        
        return null;
    },
    
    /**
     * Indicates if the given search provides key indicator formatted results (that is, includes the key indicator alert action).
     */
    isSearchInKeyIndicatorGroup: function( search, group_name ){
        if( search.content["action.keyindicator"] == undefined){
            // This search is not a key indicator
            return false;
        }
        else{
            
            var re = new RegExp("action[.]keyindicator[.]group[.]([0-9]+)[.]name");
            
            // Look for the name attribute
            for( attribute in search.content ){
                if( attribute.match(re) && search.content[attribute] == group_name ){
                    return true;
                }
            }
            
            return false;
        }
    },
    
    /**
     * Get the intended order of the search for a particular group.
     */
    getSearchOrder: function( group_name, search ){
        group_number = Splunk.Module.SOLNKeyIndicators.prototype.getGroupNumber( group_name, search);
        
        return parseInt( search.content["action.keyindicator.group." + group_number.toString() + ".order"], 10 );
    },
    
    /**
     * Compare the two searches so that they can be sorted.
     */
    compareSearches: function( search_a, search_b, group_name ){
        
        var search_a_priority = Splunk.Module.SOLNKeyIndicators.prototype.getSearchOrder(group_name, search_a);
        var search_b_priority = Splunk.Module.SOLNKeyIndicators.prototype.getSearchOrder(group_name, search_b);
        
        return search_a_priority - search_b_priority;
    },
    
    /**
     * Get the key indicator search with the given name. 
     */
    getKeyIndicatorSearch: function(search_name){
        
        // Start by getting a list of all of the searches
        var params = new Object();
        params.output_mode = 'json';
        params.count = '-1';
        
        var uri = Splunk.util.make_url('/splunkd/__raw/services/saved/searches/', encodeURIComponent(search_name));
        uri += '?' + Splunk.util.propToQueryString(params);

        var search = null;
        
        jQuery.ajax({
            url:     uri,
            type:    'GET',
            success: function(result) {
                 if(result.isOk === false){
                      console.error("Could not retrieve the search: " + result.message);
                 }
                 
                 search = result.entry;
            },
            async:   false
        });
        
        return search;
    },
    
    /**
     * Get all of the key indicator searches for the given group name. 
     */
    getKeyIndicatorSearches: function(group_name){
        
        if( group_name === undefined ){
            group_name = null;
        }
        
        // Load all of the saved searches and look for those with a key indicators action with a group name that matches
        if(group_name === null && this.key_indicators !== undefined ){
            return this.key_indicators;
        }
        
        // Start by getting a list of all of the searches
        var params = new Object();
        params.output_mode = 'json';
        params.count = '-1';
        
        var uri = Splunk.util.make_url('/splunkd/__raw/services/saved/searches/');
        uri += '?' + Splunk.util.propToQueryString(params);

        var searches = null;
        
        jQuery.ajax({
            url:     uri,
            type:    'GET',
            success: function(result) {
                 if(result.isOk === false){
                     console.error("Could not obtain the list of searches: " + result.message);
                 }
                 
                 searches = result.entry;
            },
            async:   false
        });
        
        // Now filter down the searches to those with a key indicators alert action and a matching group name
        group_searches = [];
        
        for( i = 0; i < searches.length; i++){
            if( ( group_name === null && searches[i].content["action.keyindicator"] !== undefined ) || this.isSearchInKeyIndicatorGroup( searches[i], group_name ) ){
                group_searches.push(searches[i]);
            }
        }
        
        // Cache the indicators if we got a list of all of them
        if( group_name === null ){
            this.key_indicators = group_searches.slice();
        }
        
        // Return the list of searches that are key indicators related to this item
        return group_searches;
        
    },
    
    /**
     * Populate the list of indicators in the selection form.
     */
    populateIndicatorsList: function (){
        
        // Clear the existing list
        $("#indicators-available", this.container).html("");
        
        // Insert the indicators
        var group_searches = this.getKeyIndicatorSearches();
        var indicators_available = 0;
        
        for( var c = 0; c < group_searches.length; c++){
            
            search_already_included = false;
            
            // Make sure the search isn't already present
            for( var i = 0; i < this.panels.length && search_already_included === false; i++){
                
                if( this.panels[i].name === group_searches[c].name ){
                    search_already_included = true;
                }
            }
            
            if( !search_already_included ){
                indicators_available++;
                $("#indicators-available", this.container).append('<label><input type="checkbox" name="' + group_searches[c].name + '" />' + group_searches[c].content["action.keyindicator.title"] + '<br /></label>');
            }
        }
        
        // Show or hide the message indicating that no indicators exist
        if( indicators_available > 0 ){
            $('.no-indicators-exist').hide();
            $('.indicators-exist').show();
        }
        else{
            $('.no-indicators-exist').show();
            $('.indicators-exist').hide();
        }
        
        // Return the number of indicators that are still available for adding (that are not already displayed)
        return indicators_available;
    },
    
    /**
     * Add the indicators that have selected in the editor.
     */
    addSelectedIndicators: function(){
        
        //Get the list of selected indicators
        indicators_selector = $("#indicators-available > label > input:checked");
        
        for( var c = 0; c < indicators_selector.length; c++){
            
            // Get the search that we are going to add to the list
            search_name = indicators_selector[c].attributes['name'].value;
            search = this.getKeyIndicatorSearch( search_name );
            
            // Add the search
            if( search ){
                
                search_already_included = false;
                
                // Make sure the search isn't already present
                for( var i = 0; i < this.panels.length && search_already_included === false; i++){
                    
                    if( this.panels[i].name === search_name ){
                        search_already_included = true;
                        console.info("Skipping the addition of the search since it is already on the panel: " + search_name);
                        continue; // Panel was already included, skip it
                    }
                
                }
                
                // Add the panel if it was not already included
                if( !search_already_included ){
                    id = this.panels.push(search[0]);
                    this.addPendingPanel(id-1);
                }
            }   
        }
        
        return true;
    },
    
    /**
     * Open the indicators popup form.
     */
    openSelectIndicatorsPopup: function(){
        
        // Update the list of indicators
        var indicators_available = this.populateIndicatorsList();
        
        // Get the form we are going to clone
        var formToClone = $("form.indicators-list", this.container)[0];
        
        if( indicators_available > 0 ){
            
            // Show the form with the list of key indicators that can be added
            this.popup = new Splunk.Popup(formToClone, {
                title: _('Add Key Indicators'),
                buttons: [
                    {
                        label: _('Close'),
                        type: 'secondary',
                        callback: function(){
                            return true;
                        }
                    },
                    {
                        label: _('Add'),
                        type: 'primary',
                        callback: this.addSelectedIndicators.bind(this)
                    }
                ]
            });
        }
        else{
            
            // Show a form noting that no key indicators exist to add
            
            this.popup = new Splunk.Popup(formToClone, {
                title: _('Add Key Indicators'),
                buttons: [
                    {
                        label: _('Close'),
                        type: 'secondary',
                        callback: function(){
                            return true;
                        }
                    }
                ]
            });
        }
        
        popupReference = this.popup.getPopup();
        
    },
    
    /**
     * Make an ID for a panel.
     */
    getPanelID: function( offset){
        return 'panel_' + offset.toString();
    },
    
    /**
     * Add a place to put the panel (once the results come back) and set the panel's ID so that the results can be matched up with the panel.
     */
    addPendingPanel: function( i ){
        this.panels[i].id = this.getPanelID( this.next_panel_offset );
        this.next_panel_offset++; // Increment the next offset so that we don't use the same one again (we need them to be unique so that panel IDs are unique)
        $(".KP-indicators", this.container).append('<div class="indicator" data-search="' + this.panels[i].name + '" id="' + this.panels[i].id + '"><div class="KP-holder pending">Pending...</div></div>');
    },
    
    /**
     * Get the panels for the given group and start the searches to obtain the results.
     */
    getPanels: function( group_name ){
        
        // Make sure that a variable exists to store the panel information in
        if (typeof(this.panels) === "undefined"){
            this.panels = [];
        }
        
        // Get the searches related to this key indicator group
        searches = this.getKeyIndicatorSearches( group_name );
        
        // Sort the panels by order
        search_sort_fx = function( search_a, search_b ) {
            return Splunk.Module.SOLNKeyIndicators.prototype.compareSearches( search_a, search_b, group_name );
        };
        
        searches.sort( search_sort_fx );
        this.panels = searches;
        
        // Make the panels to put the data
        for( var i = 0; i < searches.length; i++ ){
            this.addPendingPanel( i );
        }
        
        // Add the edit button handler
        $("#edit", this.container).click( function(object){ 
            return function(){
                object.enterEditMode();
            };
        }(this) );
        
        // Add the save button handler
        $("#save", this.container).click( function(object){ 
            return function(){
                object.savePanels();
                object.exitEditMode();
            };
        }(this) );
        
        // Add the cancel button handler
        $("#cancel", this.container).click( function(object){ 
            return function(){
                object.exitEditMode();
            };
        }(this) );
        
        // Add the add button handler
        $("#add", this.container).click( function(object){ 
            return function(){
                object.openSelectIndicatorsPopup();
            };
        }(this) );
        
        // Kick off the searches
        var searches_dispatched = 0;
        for( i = 0; i < this.panels.length && searches_dispatched < this.concurrent_searches_limit; i++ ){
            this.panels[i].sid = this.dispatchSearch(this.panels[i].name);
            $( "#" + this.getPanelID( i ), this.container ).html( '<div class="KP-holder loading">Loading...</div>' );
            searches_dispatched = searches_dispatched + 1;
        }
        
        // Start the refreshing of results
        this.refreshResults();
        
        // Populate the list of key indicators
        this.populateIndicatorsList();
        
    },

    /**
     * Get the panel information as arguments that can be sent to the REST endpoint.
     */
    getPanelArgs: function(){
        
        panels_json = this.deserializePanels();
        
        args = {};
        
        args.group_name = panels_json.group_name;
        
        for( var i = 0; i < panels_json.panels.length; i++ ){
            args["indicator." + i.toString() + ".search"] = panels_json.panels[i].search;
            args["indicator." + i.toString() + ".order"] = i + 1;
        }
        
        return args;
        
    },
    
    /**
     * Enter (or exit) editing mode and expose or hide the controls for modifying the panels.
     */
    editMode: function( start_edit ){
        
        if( start_edit ){
            $(".KP-main", this.container).addClass("editing");
            $(".KP-indicators", this.container ).sortable({ containment: "parent", axis: "x" });
            $(".KP-indicators" ).disableSelection();
        }
        else{
            $(".KP-main", this.container).removeClass("editing");
            $(".KP-indicators", this.container).sortable("destroy");
        }
    },
    
    /**
     * Enter editing mode and show the controls for modifying the panels. 
     */
    enterEditMode: function( ){
        this.editMode( true );
    },
    
    /**
     * Exit editing mode and hide the controls for modifying the panels. 
     */
    exitEditMode: function( ){
        this.editMode( false );
    },
    
    /**
     * Called when key indicators are saved correctly.
     */
    saveSuccess: function(){
        $('.saving', this.container).fadeOut();
    },
    
    /**
     * Save the panel information to Splunk.
     */
    savePanels: function(){
        data = this.getPanelArgs();
        
        $('.saving', this.container).show();
        $.ajax( 
                {
                    url:  Splunk.util.make_url('/custom/SA-Utils/keyindicators/update'),
                    type: 'POST',
                    data: data,
                    
                    success: function(object){ return function(){ object.saveSuccess(); }; }(this),
                    
                    error: function(jqXHR,textStatus,errorThrown) {
                        console.warn("Key indicators were not saved");
                        alert("The Key indicators could not be saved");
                        $('.saving', this.container).fadeOut();
                    } 
                }
        );
        
    },
    
    /**
     * Convert the panels back to a JSON representation.
     */
    deserializePanels: function(){
        
        var panels = $(".indicator", this.container);
        var panels_list_json = [];
        
        // Go through each panel and de-serialize it
        for( var i = 0; i < panels.length; i++){
            
            // Get the information from the panel
            panel_json = {};
            panel_json.search = panels[i].attributes["data-search"].nodeValue;
            
            // Add the panel information to the list
            panels_list_json.push(panel_json);
            
        }
        
        // Get the group name
        var group_name = $(".KP-main", this.container).attr("data-group-name");
        
        // Assemble the final list
        panels_json = {};
        panels_json.group_name = group_name;
        panels_json.panels = panels_list_json;
        
        return panels_json;
        
    },
    
    /**
     * Return the the value if it is defined; otherwise, return the default value.
     */
    getValueOrDefault: function( value, default_value){
        
        if( value == undefined ){
            return default_value;
        }
        else{
            return value;
        }
        
    },
    
    /**
     * Return the the value if it is defined; otherwise, return the default value. Also, convert the value to a float.
     */
    getFloatValueOrDefault : function( value, default_value){
        value = this.getValueOrDefault( value, default_value);
        
        return parseFloat( value, 10 );
    },
    
    /**
     * Return the the value if it is defined; otherwise, return the default value. Also, convert the value to a boolean.
     */
    getBooleanValueOrDefault : function( value, default_value){
        value = this.getValueOrDefault( value, default_value);
        
        if( value === true || value === false ){
            return value;
        }
        else if( value === undefined || value === null ){
            return false;
        }
        else if( value > 0 || value.toLowerCase() == "true" || value.toLowerCase() == "t"){
            return true;
        }
        else{
            return false;
        }
        
    },
    
    /**
     * Return the value of the field from either (in order):
     *  1) the key indicator alert action associated with the saved search
     *  2) the field in the results
     *  3) the default value
     */
    getFromActionOrResult : function ( field_name, action_field_name, search, fields, default_value ){
        
        if( search.content[action_field_name] !== undefined ){
            return search.content[action_field_name];
        }
        else if( fields[field_name] !== undefined ){
            return fields[field_name];
        }
        else{
            return default_value;
        }
        
    },
    
    /**
     * Same as getFromActionOrResult except that this converts the the returned value to a boolean.
     */
    getBooleanFromActionOrResult : function( field_name, action_field_name, search, fields, default_value ){
        this.getBooleanValueOrDefault( this.getFromActionOrResult( field_name, action_field_name, search, fields, default_value ), default_value );
    },
    
    /**
     * Same as getFromActionOrResult except that this converts the the returned value to a float.
     */
    getFloatFromActionOrResult : function( field_name, action_field_name, search, fields, default_value ){
        this.getFloatValueOrDefault( this.getFromActionOrResult( field_name, action_field_name, search, fields, default_value ), default_value );
    },
    
    /**
     * Make an HTML panel from the provided results and search.
     */
    getPanelHTMLFromSearch: function ( search, search_name, fields ){
        
        var value_field_name = this.getFromActionOrResult("value", "action.keyindicator.value", search, fields, "value");
        var delta_field_name = this.getFromActionOrResult("delta", "action.keyindicator.delta", search, fields, "delta");
        var drilldown_uri = this.getFromActionOrResult("drilldown_uri", "action.keyindicator.drilldown_uri", search, fields, undefined);
        
        var invert = this.getBooleanFromActionOrResult("invert", "action.keyindicator.invert", search, fields, false);
        var threshold = this.getFloatFromActionOrResult("threshold", "action.keyindicator.threshold", search, fields, false);
        var title = this.getFromActionOrResult("title", "action.keyindicator.title", search, fields, "");
        var subtitle = this.getFromActionOrResult("subtitle", "action.keyindicator.subtitle", search, fields, "");
        
        var value_suffix = this.getFromActionOrResult("value_suffix", "action.keyindicator.value_suffix", search, fields, "");
        
        var value = "";
        var delta = "";
        
        if( fields != undefined ){
            value = this.getFloatValueOrDefault(fields[value_field_name], "Unknown");
            delta = this.getValueOrDefault(fields[delta_field_name], "");
        }
        
        // Get the description of the delta operator
        var delta_operator = "";
        
        if( delta >= 0 ){
            delta_operator = "+";
        }

        // Get the CSS class for the delta description
        var delta_description;
        
        if( parseFloat(delta, 10) > 0 ){
            delta_description = "up";
        }
        else if( parseFloat(delta, 10) < 0 ){
            delta_description = "down";
        }
        else{
            delta_description = "no-change";
        }
        
        // Determine the invert CSS class
        var invert_class = "non-inverted";
        
        if (invert){
            invert_class = "inverted";
        }
        
        // Determine threshold class
        var threshold_class;
        
        if( threshold === null || isNaN(threshold)  ){
            threshold_class = "no-threshold";
        }
        else if( value > threshold && invert === false ){
            threshold_class = "over-threshold";
        }
        else if( value < threshold && invert === true ){
            threshold_class = "under-threshold";
        }
        else{
            threshold_class = "within-threshold";
        }
        
        // Make the drilldown URI
        var href_before = "";
        var href_after = "";
        
        if( drilldown_uri !== null &&  drilldown_uri !== undefined ){
            href_before = '<a href="' + drilldown_uri + '">';
            href_after = "</a>";
        }
        
        html_data = '<div class="KP-holder ' + delta_description + ' ' + invert_class + ' ' + threshold_class + '">' + 
            '<div class="KP-value-description">' + title + '</div>' +
            '<div class="KP-main-value ">' + 
               '<div class="KP-subtitle">' + subtitle + '</div>' +
               '<div class="KP-value">' + href_before + value + href_after + 
                   '<span class="KP-value-suffix">' + value_suffix + '</span>' +
               '</div>' +
               '<div class="KP-details">' +
                   '<div class="KP-delta icon"></div>' +
                   '<div class="KP-delta">' + delta_operator + delta + '</div>' +
               '</div>' +
            '</div>' +
            '<div class="delete"><a href="#"></a></div>' +
        '</div>';
        
        return html_data;
        
    },
    
    /**
     * Remove the indicator at the given ID.
     */
    deleteIndicator: function( id ){
        
        // Get the name of the search that is going to be deleted
        search_name_to_delete = $( "#" + id, this.container ).attr("data-search");
        
        // Remove the UI element
        $( "#" + id, this.container ).remove();
        
        // Find the panel in the internal data structure to delete
        for( var c = 0; c < this.panels.length; c++ ){
            
            // Found the item, splice it away...
            if( this.panels[c].name === search_name_to_delete ){
                this.panels.splice(c, 1); //Remove the item
            }
        }
        
        // Show the panel noting that all of the indicators have been deleted (if this is so)
        if( this.panels.length === 0 ){
            $(".KP-indicators-empty").show();
        }
        else{
            $(".KP-indicators-empty").hide();
        }
        
    },
    
    /**
     * Render the panel with the given ID (which refers to an item in this.panels) with the provided result.
     */
    renderPanel: function ( result, id ) {
        
        // Stop if we didn't get results yet.
        if( result === "" || result.results === undefined ){
            return;
        }
        
        // Find the panel
        for( var c = 0; c < this.panels.length; c++ ){
            
            if( this.panels[c].id == id ){
                panel = this.panels[c];
                break;
            }
        }
        
        if( panel === undefined ){
            return;
        }
        
        // Make the HTML
        var html_data;
        
        if( result.results[0] !== undefined){
            html_data = this.getPanelHTMLFromSearch( panel, panel.name, result.results[0]);
        }
        else{
            html_data = '<div class="KP-holder KP-indicators-no-results">No results found<div class="delete"><a href="#"></a></div></div>';
        }
        
        // If we are not previewing results, then mark this one as done
        if( !result.preview ){
            panel.doneRendering = true;
        }
        
        // Append the html
        $( "#" + id, this.container ).html( html_data );
        
        // Setup the delete button
        $( "#" + id + " .delete", this.container ).click( function(object, id){ 
            return function() {
                object.deleteIndicator(id);
            };
        }(this, id) );
        
    },
    
    /**
     * Refresh the panels based on the contents of the results.
     */
    refreshResults: function(){
        console.info("Refreshing the results for the key indicators");
        
        // This will be used to determine if we need to continue polling for updates
        var resultsStillPending = false;
        
        // This indicates the numbers of searches that are currently executing (necessary so that we can throttle the number of searches)
        var searchesRunning = 0;
        
        // Refresh the panels if we got new results
        for( var i = 0; i < this.panels.length; i++ ){
            
            // Get a reference to the current panel
            panel = this.panels[i];
            
            // If the search doesn't have an SID, then it hasn't been dispatched yet. Thus, we are still waiting on results.
            if( panel.sid == undefined ){   
                resultsStillPending = true;
            }
            
            // The search has been kicked off; lets get the results and see if the search is complete yet.
            else if(!panel.doneRendering && panel.sid !== null){
                
                var params = new Object();
                params.output_mode = 'json';
                var uri = Splunk.util.make_url('/splunkd/__raw/services/search/jobs/', panel.sid, '/results');
                uri += '?' + Splunk.util.propToQueryString(params);
                
                jQuery.ajax({
                    url:     uri,
                    type:    'GET',
                    cache:    false,
                    success: function(id, instance){
                        return function(result) {
                            
                            if(result.isOk === false){
                                alert(result.message);
                            }
                            else{
                                instance.renderPanel(result, id);
                            }
                        };
                    }(panel.id, this), // This call is being done so that the inner function call remembers which panel ID is being used and what the instance was,
                    error: function(panel, instance){
                        return function(jqXHR,textStatus,errorThrown) {
                            console.warn("Unable to get the search results");
                            $( "#" + panel.id, instance.container ).html( '<div class="KP-holder KP-indicators-no-results">Unable to load results</div>' );
                            panel.doneRendering = true;
                        };
                    }(panel, this),
                    async:   true
                });
                
                // If the panel is not done being rendered then treat the panel as still needing to do work
                if( !panel.doneRendering ){
                    resultsStillPending = true;
                    searchesRunning = searchesRunning + 1;
                }
            }
            else if(panel.sid === null){
                panel.doneRendering = true;
            }
        }
        
        // Dispatch another search if we have more to execute
        if( searchesRunning < this.concurrent_searches_limit && resultsStillPending ){
            for( i = 0; i < this.panels.length && searchesRunning < this.concurrent_searches_limit; i++ ){
                
                // If we find a search that needs dispatching, then dispatch it and note that another search is running by incrementing the variable noting how many searches are running
                if( this.panels[i].sid === undefined ){
                    this.panels[i].sid = this.dispatchSearch( this.panels[i].name );
                    $( "#" + this.panels[i].id, this.container ).html( '<div class="KP-holder loading">Loading...</div>' );
                    searchesRunning = searchesRunning + 1;
                }
            }
        }
        
        // Set up the next refresh call
        //
        // Note that we could avoid scheduling another refresh if resultsStillPending is false since this variable
        // indicates that all of the panels are done being updated. The problem is that we need refreshResults to
        // be called if the user adds a new panel. Thus, we will just schedule another refresh.
        setTimeout( function(){ this.refreshResults(); }.bind(this), 800 );
        
        // Show the panel noting that no indicators exist (if this is so)
        if( this.panels.length === 0 ){
            $(".KP-indicators-empty").show();
        }
        else{
            $(".KP-indicators-empty").hide();
        }
    }
    
});