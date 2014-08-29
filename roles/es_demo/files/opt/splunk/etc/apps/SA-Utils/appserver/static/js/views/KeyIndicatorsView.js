require.config({
    paths: {
        key_indicator_view: '../app/SA-Utils/js/views/KeyIndicatorView',
        text: '../app/SA-Utils/js/lib/text',
        console: '../app/SA-Utils/js/util/Console'
    }
});

define(['underscore', 'splunkjs/mvc', 'jquery', 'splunkjs/mvc/simplesplunkview', 'key_indicator_view', 'text!../app/SA-Utils/js/templates/KeyIndicators.html', "css!../app/SA-Utils/css/KeyIndicators.css", 'console'],
function(_, mvc, $, SimpleSplunkView, KeyIndicatorView, KeyIndicatorsTemplate) {
    
    // Define the custom view class
    var KeyIndicatorsView = SimpleSplunkView.extend({
        className: "KeyIndicatorsView",
        
        /**
         * Setup the defaults
         */
        defaults: {
            concurrent_searches: 2,
            editable: true
        },
        
        events: {
            "click #save": "save",
            "click #edit": "enterEditMode",
            "click #cancel": "exitEditMode",
            "click #add": "openSelectIndicatorsPopup",
            "click #add-indicators": "addSelectedIndicators",
            "click .add-indicator-link": "openSelectIndicatorsPopup"
        },
        
        /**
         * Initialize the key indicators view
         */
        initialize: function() {
            
            // Apply the defaults
            this.options = _.extend({}, this.defaults, this.options);
            
            // Get the arguments
            this.concurrent_searches = this.options.concurrent_searches;
            this.group_name = this.options.group_name;
            this.editable = this.options.editable;
        },
        
        /**
         * Autodiscover divs that are intended to be key indicators and load the arguments
         */
        autodiscover: function() {
            
            $('.key-indicators[data-group-name]').each(function() {
                
                args = {};
                
                args['group_name'] = this.getAttribute("data-group-name");
                args['el'] = $(this);
                
                // Handle the concurrent_searches argument
                concurrent_searches = this.getAttribute("data-concurrent-searches");
                
                if( concurrent_searches !== null ){
                    args['concurrent_searches'] = parseInt(concurrent_searches, 10);
                }
                
                // Handle the editable argument
                editable = this.getAttribute("data-editable");
                
                if( editable !== null ){
                    args['editable'] = (editable == 'true');
                }
                
                // Make the key indicators if the group name was defined
                if( args['group_name'] !== null ){
                    
                    // Make a key indicators view for that obtains the items in security posture
                    var keyIndicatorsView = new KeyIndicatorsView(args);
    
                    keyIndicatorsView.render();
                }
            });
        },
        
        /**
         * Render the base content where the indicators will be added to.
         */
        renderBaseContent: function(){
            // Get the base content
            this.$el.html( _.template(KeyIndicatorsTemplate,{
                group_name: this.group_name,
                concurrent_searches: this.concurrent_searches,
                editable: this.editable
            }) );
        },
        
        /**
         * Render the view
         */
        render: function() {
            
            // Get the base content
            this.renderBaseContent();
            
            // Get the indicators
            this.getIndicators(this.group_name);
            
            // Kick off the searches
            var searches_dispatched = 0;
            
            for( i = 0; i < this.key_indicators.length && searches_dispatched < this.concurrent_searches; i++ ){
            	
            	// Get a reference to the current panel
                key_indicator = this.key_indicators[i];
            	
            	// If the search is scheduled, tell it to begin getting results
            	if( key_indicator.search.content.is_scheduled ){
            		key_indicator.startGettingResults();
            	}
            	
            	// If we are not at the limit, then kick off another non-scheduled search
            	else if( searches_dispatched >= this.concurrent_searches ){
            		key_indicator.startGettingResults();
            		searches_dispatched = searches_dispatched + 1;
            	}
            }
            
            // Start the refreshing of results
            this.refreshResults();
            
            // Populate the list of key indicators
            this.populateIndicatorsList();
            
            // Render the key indicators
            if( this.key_indicators !== undefined ){
                for( var i=0; i < this.key_indicators.length; i++){
                    this.key_indicators[i].render();
                }
            }
            
            return this;
        },

        
        /**
         * Get the key indicators for the given group and start the searches to obtain the results.
         */
        getIndicators: function( group_name ){
            
            // Make sure that a variable exists to store the panel information in
            if (typeof(this.key_indicators) === "undefined"){
                this.key_indicators = [];
            }
            
            // Get the searches related to this key indicator group
            searches = this.getKeyIndicatorSearches( group_name );
            
            // Sort the key indicators by order
            search_sort_fx = function( search_a, search_b ) {
                return KeyIndicatorsView.prototype.compareSearches( search_a, search_b, group_name );
            };
            
            searches.sort( search_sort_fx );
            
            // Make the key indicators to render the data
            for( var i = 0; i < searches.length; i++ ){
                this.addKeyIndicator(searches[i]);
            }
            
        },
        

        /**
         * Refresh the key indicators based on the contents of the results.
         */
        refreshResults: function(){
            console.info("Refreshing the results for the key indicators");
            
            // This will be used to determine if we need to continue polling for updates
            var resultsStillPending = false;
            
            // This indicates the numbers of searches that are currently executing (necessary so that we can throttle the number of searches)
            var searchesRunning = 0;
            
            // Refresh the key indicators if we got new results
            for( var i = 0; i < this.key_indicators.length; i++ ){
                
                // Get a reference to the current panel
                key_indicator = this.key_indicators[i];
                
                // If the search doesn't have an SID, then it hasn't been dispatched yet. Thus, we are still waiting on results.
                if( !key_indicator.gettingResults() ){   
                    resultsStillPending = true;
                }
                
                // The search has been kicked off; lets get the results and see if the search is complete yet.
                else if(!key_indicator.doneRendering() && key_indicator.gettingResults()){
                    
                    key_indicator.updateWithResults();
                    
                    // If the panel is not done being rendered then treat the panel as still needing to do work
                    if( !key_indicator.doneRendering() ){
                        resultsStillPending = true;
                        searchesRunning = searchesRunning + 1;
                    }
                }
            }
            
            // Dispatch another search if we have more to execute
            if( searchesRunning < this.concurrent_searches && resultsStillPending ){
                for( i = 0; i < this.key_indicators.length && searchesRunning < this.concurrent_searches; i++ ){
                    
                    // If we find a search that needs dispatching, then dispatch it and note that another search is running by incrementing the variable noting how many searches are running
                    if( !this.key_indicators[i].gettingResults() ){
                        this.key_indicators[i].startGettingResults();
                        
                        // Keep a list of the searches that are running. Only count it if the search is not scheduled since we won't need to run the searches for these (most likely), we'll just need to grab the results.
                        if( !this.key_indicators[i].search.content.is_scheduled ){
                        	searchesRunning = searchesRunning + 1;
                        }
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
            if( this.key_indicators.length === 0 ){
                $(".KP-indicators-empty").fadeIn();
            }
            else{
                
                var isEmpty = true;
                
                for( i = 0; i < this.key_indicators.length; i++ ){
                    if( this.key_indicators[i].isDeleted === false ){
                        isEmpty = false;
                    }
                }
                
                if( isEmpty ){
                    $(".KP-indicators-empty").fadeIn();
                }
                else{
                    $(".KP-indicators-empty").fadeOut();
                }
            }
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
                        // This search is a key indicator and it is for the given group
                        return true;
                    }
                }
                
                // This search is a key indicator but it is _not_ for the given group
                return false;
            }
        },
        
        /**
         * Get the intended order of the search for a particular group.
         */
        getSearchOrder: function( group_name, search ){
            group_number = KeyIndicatorsView.prototype.getGroupNumber( group_name, search);
            
            return parseInt( search.content["action.keyindicator.group." + group_number.toString() + ".order"], 10 );
        },
        
        /**
         * Compare the two searches so that they can be sorted.
         */
        compareSearches: function( search_a, search_b, group_name ){
            
            var search_a_priority = KeyIndicatorsView.prototype.getSearchOrder(group_name, search_a);
            var search_b_priority = KeyIndicatorsView.prototype.getSearchOrder(group_name, search_b);
            
            return search_a_priority - search_b_priority;
        },
        
        /**
         * Filter down a list of searches to those that are key-indicators (and match the given group-name if provided)
         */
        filterKeyIndicatorSearches: function(searches, group_name){
        	
        	// If no group name was provided, then group_name to null so that we just filter out non-key-indicator searches 
        	if(group_name === undefined){
        		group_name = null;
        	}
        	
        	group_searches = [];
        	
            for( i = 0; i < searches.length; i++){
                if( ( group_name === null && searches[i].content["action.keyindicator"] !== undefined ) || this.isSearchInKeyIndicatorGroup( searches[i], group_name ) ){
                    group_searches.push(searches[i]);
                }
            }
            
            return group_searches;
        },
        
        /**
         * Get all of the key indicator searches for the given group name. 
         */
        getKeyIndicatorSearches: function(group_name){
            
            if( group_name === undefined ){
                group_name = null;
            }
            
            
            if( this.key_indicator_searches !== undefined ){
            	return this.filterKeyIndicatorSearches(this.key_indicator_searches, group_name).slice();
            }
            
            // Load all of the saved searches and look for those with a key indicators action with a group name that matches
            
            // Start by getting a list of all of the searches
            var params = new Object();
            params.output_mode = 'json';
            params.count = '-1';
            params.search = 'action.keyindicator=1 AND is_visible=1 AND disabled=0';
            
            var uri = Splunk.util.make_url('/splunkd/__raw/services/saved/searches/');
            uri += '?' + Splunk.util.propToQueryString(params);

            var searches = null;
            
            jQuery.ajax({
                url:     uri,
                type:    'GET',
                success: function(result) {
                     if(result !== undefined && result.isOk === false){
                         console.error("Could not obtain the list of searches: " + result.message);
                     }
                     else if(result !== undefined){
                    	 searches = result.entry;
                     }
                },
                async:   false
            });
            
            // Cache the key indicator searches
            this.key_indicator_searches = this.filterKeyIndicatorSearches(searches).slice();
            
            // Now filter down the searches to those with a key indicators alert action and a matching group name
            if( group_name !== null){
            	return this.filterKeyIndicatorSearches(searches, group_name).slice();
            }
            else{
            	return this.key_indicator_searches;
            }
            
        },
        
        /*
         * Everything below this is for editing of key indicators
         */
        
        /**
         * Enter (or exit) editing mode and expose or hide the controls for modifying the panels.
         */
        editMode: function( start_edit ){
            
            if( start_edit ){
                $(".KP-main", this.$el).addClass("editing");
                
                // If sortable was already setup, then just enable it
                if( this.configuredSortable != undefined ){
                    $(".KP-indicators", this.$el).sortable("enable");
                }
                
                // Otherwise, setup a sortable
                else{
                    $(".KP-indicators", this.$el ).sortable({ containment: "parent", axis: "x" });
                    this.configuredSortable = true;
                }
                
                //$(".KP-indicators" ).disableSelection();
            }
            else{
                $(".KP-main", this.$el).removeClass("editing");
                $(".KP-indicators", this.$el).sortable("disable");
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
            $('.saving', this.$el).fadeOut();
        },
        
        /**
         * Populate the list of indicators in the selection form.
         */
        populateIndicatorsList: function (){
            
            // Clear the existing list
            $("#indicators-available", this.$el).html("");
            
            // Insert the indicators
            var available_searches = this.getKeyIndicatorSearches();
            
            var indicators_available = 0;
            
            for( var c = 0; c < available_searches.length; c++){
                
                search_already_included = false;
                
                // Make sure the search isn't already present
                for( var i = 0; i < this.key_indicators.length && search_already_included === false; i++){
                    
                    if( this.key_indicators[i].isDeleted === false && this.key_indicators[i].search.name === available_searches[c].name ){
                        search_already_included = true;
                    }
                }
                
                if( !search_already_included ){
                    indicators_available++;
                    $("#indicators-available", this.$el).append('<label><input type="checkbox" name="' + available_searches[c].name + '" />' + available_searches[c].name + '<br /></label>');
                }
            }
            
            // Return the number of indicators that are still available for adding (that are not already displayed)
            return indicators_available;
        },
        
        /**
         * Open the dialog to select indicators
         */
        openSelectIndicatorsPopup: function(){
            if( this.populateIndicatorsList() === 0){
                $('#all-indicators-displayed-dialog', this.$el).modal();
            }
            else{
                $('#select-indicators-dialog', this.$el).modal();
            }
        },
        
        /**
         * Get the key indicator search with the given name. 
         */
        getKeyIndicatorSearch: function(search_name){
            
            var available_searches = this.getKeyIndicatorSearches();
            
            for( var c = 0; c < available_searches.length; c++){
                if( available_searches[c].name === search_name){
                    return available_searches[c];
                }
            }
            
            return null;
        },
        
        /**
         * Add the indicators that have selected in the editor.
         */
        addSelectedIndicators: function(){
            
            //Get the list of selected indicators
            indicators_selector = $("#indicators-available > label > input:checked", this.$el);
            
            for( var c = 0; c < indicators_selector.length; c++){
                
                // Get the search that we are going to add to the list
                search_name = indicators_selector[c].attributes['name'].value;
                search = this.getKeyIndicatorSearch( search_name );
                
                // Add the search
                if( search ){
                    
                    search_already_included = false;
                    
                    // Make sure the search isn't already present
                    for( var i = 0; i < this.key_indicators.length && search_already_included === false; i++){
                        
                        if( this.key_indicators[i].isDeleted === false && this.key_indicators[i].search.name === search_name ){
                            search_already_included = true;
                            console.info("Skipping the addition of the search since it is already on the panel: " + search_name);
                            continue; // Panel was already included, skip it
                        }
                    
                    }
                    
                    // Add the panel if it was not already included
                    if( search && !search_already_included ){
                        this.addKeyIndicator(search);
                    }
                }    
            }
            
            // Close the dialog
            $('#select-indicators-dialog').modal('hide');
            
            return true;
        },
        
        /**
         * Get the key indicator information as arguments that can be sent to the REST endpoint.
         */
        addKeyIndicator: function(search){
            
            // Add the placeholder
            key_indicator_el = $('<div class="indicator" data-search="' + search.name + '"></div>').appendTo( $(".KP-indicators", this.$el) );
            
            // Instantiate the class
            var keyIndicatorView = new KeyIndicatorView({
                search: search,
                el: key_indicator_el
            });
            
            // Add the indicator to the list
            this.key_indicators.push(keyIndicatorView);
            
            keyIndicatorView.bind('remove', function() { alert('Removing!'); });
            keyIndicatorView.render(); // Kick the indicator so that the pending panel gets shown
            
            console.info("Successfully added new indicator (" + search.name + ")");
            
        },
        
        /**
         * Get the key indicator information as arguments that can be sent to the REST endpoint.
         */
        getKeyIndicatorState: function(){
            
            indicators_json = {};
            indicators_json.group_name = this.group_name;
            
            // This is used for determining the next order number for the key indicators
            indicators_total = 0;
            
            // Add the key indicator information to the named array
            for(var i = 0; i < this.key_indicators.length; i++){
                
                key_indicator = this.key_indicators[i];
                
                // Only add the indicator if it wasn't deleted
                if( key_indicator.isDeleted === false ){
                    indicators_json["indicator." + i.toString() + ".search"] = key_indicator.search.name;
                    indicators_json["indicator." + i.toString() + ".order"] = indicators_total;
                    
                    // Set the threshold
                    if(key_indicator.threshold !== null){
                    	indicators_json["indicator." + i.toString() + ".threshold"] = key_indicator.threshold;
                    }
                    
                    indicators_total++;
                }
            }
            
            return indicators_json;
            
        },
        
        /**
         * Indicates if the key indicators are in a state that they can be saved.
         */
        readyToBeSaved: function(){
        	
        	// Check each indicator and stop if none of them can be saved.
            for(var i = 0; i < this.key_indicators.length; i++){
                
                if(!this.key_indicators[i].readyToBeSaved()){
                	return false;
                }
            }
            
            // If we didn't return false already, then the status checked out
            return true;
        	
        },
        
        /**
         * Save the key indicator information to Splunk.
         */
        save: function(){
        	
        	// Make sure the key indicators are ready to be saved; stop if they are not
        	if( !this.readyToBeSaved() ){
        		alert("The key indicators cannot be saved; please correct the error and try again.");
        		return;
        	}
        	
            data = this.getKeyIndicatorState();
            
            $('.saving', this.$el).show();
            $.ajax( 
                    {
                        url:  Splunk.util.make_url('/custom/SA-Utils/keyindicators/update'),
                        type: 'POST',
                        data: data,
                        
                        success: function(object){ 
                            return function(){
                                object.saveSuccess();
                            };
                        }(this),
                        
                        error: function(jqXHR,textStatus,errorThrown) {
                            console.warn("Key indicators were not saved");
                            alert("The Key indicators could not be saved");
                            $('.saving', this.$el).fadeOut();
                        } 
                    }
            );
            
            this.exitEditMode();
            
        }
        
    });
    
    
    return KeyIndicatorsView;
});