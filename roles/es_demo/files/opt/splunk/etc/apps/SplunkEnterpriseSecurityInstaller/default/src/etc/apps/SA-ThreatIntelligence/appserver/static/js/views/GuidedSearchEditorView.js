require.config({
    paths: {
        text: "../app/SA-Utils/js/lib/text",
        console: '../app/SA-Utils/js/util/Console',
        search_aggregate_view: '../app/SA-ThreatIntelligence/js/views/SearchAggregateView'
    }
});

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "splunkjs/mvc/utils",
    "splunkjs/mvc/tokenutils",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "text!../app/SA-ThreatIntelligence/js/templates/GuidedSearchEditor.html",
    "search_aggregate_view",
    "splunkjs/mvc/simpleform/formutils",
    "splunkjs/mvc/simpleform/input/dropdown",
    "splunkjs/mvc/simpleform/input/text",
    "splunkjs/mvc/simpleform/input/multiselect",
    "css!../app/SA-ThreatIntelligence/css/GuidedSearchEditor.css",
    "console"
], function(_, Backbone, mvc, utils, TokenUtils, $, SimpleSplunkView, GuidedSearchEditorViewTemplate, SearchAggregateView, FormUtils, DropdownInput, TextInput, MultiSelectInput){
	
    // Define the custom view class
    var GuidedSearchEditorView = SimpleSplunkView.extend({
    	
        className: "GuidedSearchEditorView",

        /**
         * Setup the defaults
         */
        defaults: {
        	search_spec: null
        },
        
        events: {
        	"click .btn-prev": "gotoPrevPage",
        	"click .btn-next": "gotoNextPage",
        	"click .btn-finalize": "finalizeSearch",
        	"click .aggregate-new" : "newAggregate"
        },
        
        initialize: function() {
            this.apps = null;
            
            // Apply the defaults
            this.options = _.extend({}, this.defaults, this.options);
            options = this.options || {};
            
            this.search_spec = options.search_spec;
            
            this.page_state = 0;
            
            // This data structure outlines the page states
            this.page_states = {
            		'string_search_to_be_replaced_page' : {
            			'state_id': 0,
            			'initial_state': true,
            			'element_id': '#string_search_to_be_replaced_page'
            		},
            		'data_model_selection_page' : {
            			'state_id': 1,
            			'element_id': '#data_model_selection_page'
            		},
            		'time_selection_page' : {
            			'state_id': 2,
            			'element_id': '#time_selection_page'
            		},
            		'event_filter_page' : {
            			'state_id': 3,
            			'element_id': '#event_filter_page'
            		},
            		'aggregate_list_page': {
            			'state_id': 4,
            			'element_id': '#aggregate_list_page',
            			'next_state_id' : 6
            		},
            		'aggregate_edit_page': {
            			'state_id': 5,
            			'element_id': '#aggregate_edit_page'
            		},
            		'split_by_selection_page' : {
            			'state_id': 6,
            			'element_id': '#split_by_selection_page'
            		},
            		'split_by_alias_page' : {
            			'state_id': 7,
            			'element_id': '#split_by_alias_page'
            		},
            		'match_logic_selection_page' : {
            			'state_id': 8,
            			'element_id': '#match_logic_selection_page'
            		},
            		'finalize_search_page' : {
            			'state_id': 9,
            			'element_id': '#finalize_search_page',
            			'final_state': true
            		}
            };
            
            this.search_string = null;
            this.search_parses = null;
            
            // The following is where data-models will be stored
            this.data_models = null;
            
            // The following is where time-presets will be stored
            this.time_presets = null;
            
            // A cache of the available fields
            this.available_fields = null;
            
            // The suppression information is stored so that it can be added to the search spec
            this.suppress_fields = null;
            
            // The list of search aggregate views (necessary for editing search aggregates)
            this.search_aggregate_views = {};
            
            // Listen to the event indicating that aggregates are being modified
            this.listenTo(Backbone, "search_aggregate:edit", this.editAggregate.bind(this));
            this.listenTo(Backbone, "search_aggregate:remove", this.removeAggregate.bind(this));
            
            // This indicates which aggregate is being edited
            this.editing_aggregate = null;
            
            // The list of split-by aliases
            this.split_by_aliases = {};
        },
        
        /**
         * Get the value of the given property if it exists.
         */
        getPropertyIfAvailable: function(obj, prop, default_value){
        	if( obj.hasOwnProperty(prop) ){
        		return obj[prop];
        	}
        	else{
        		return default_value;
        	}
        },
        
        /**
         * Apply the given search time.
         */
        applySearchTimes: function(preset_name) {
        	
        	// If we don't have time presets of the preset name is blank, then don't do anything
        	if(this.time_presets === null || preset_name === "" || preset_name === undefined){
        		return;
        	}
        	
        	// Find the earliest and latest times
        	var earliest = null;
            var latest = null;
            
        	for(var c = 0; c < this.time_presets.length; c++ ){
        		if( this.time_presets[c].name == preset_name){
        			
        			earliest = this.time_presets[c].content.earliest_time;
        			latest = this.time_presets[c].content.latest_time;
        			
        			// An empty time is the same as now; explicitly set this as now
        			if( latest === "" || latest === undefined ){
        				latest = "now";
        			}
        			break;
        		}
        	}
            
        	// Set the times
            mvc.Components.get("start_time_input").val(earliest);
        	mvc.Components.get("end_time_input").val(latest);
        },
        
        /**
         * Determines if the version of the search spec is supported by this editor.
         */
        isSearchSpecVersionSupported: function(search_spec){
        	
        	// Make sure the search spec makes sense
        	if(search_spec === null || search_spec === ""){
        		return undefined;
        	}
        	
        	// We currently only support version 1.0
        	if( search_spec.version === undefined || search_spec.version == "1.0" ){
        		return true;
        	}
        	else{
        		return false;
        	}
        	
        },
        
        /**
         * Load the given search spec.
         */
        loadSearchSpec: function(search_spec, start_time, end_time, suppress_fields){
        	
        	// Make sure the search spec makes sense
        	if(search_spec === null || search_spec === "" || !search_spec.hasOwnProperty('searches') ){
        		return false;
        	}
        	
        	// Don't try to load a search spec in the UI if it is not supported
        	if( !this.isSearchSpecVersionSupported(search_spec) ){
        		this.search_spec = search_spec;
        		return true;
        	}
        	
        	// Times
        	if( search_spec.searches[0].hasOwnProperty('inputlookup') ) {
        		
        		// For searches using inputlookup, we need to load the times from the search spec
        		if( search_spec.searches[0].hasOwnProperty('earliest') ) {
        			start_time =  search_spec.searches[0].earliest;
        		}
        		
        		if( search_spec.searches[0].hasOwnProperty('latest') ) {
        			end_time =  search_spec.searches[0].latest;
        		}
        		
        	}
        	else{
        		if( !start_time ){
	        		start_time = "";
	        	}
	        	
	        	if( !end_time ){
	        		end_time = "";
	        	}
        	}
        	
        	mvc.Components.get("start_time_input").val(start_time);
        	mvc.Components.get("end_time_input").val(end_time);
        	
        	// Suppression information
        	this.suppress_fields = suppress_fields;
        	
        	// Data model
        	if( search_spec.searches[0].hasOwnProperty('datamodel') ) {
        		mvc.Components.getInstance("sources_dropdown").val('data_model');
        		mvc.Components.get("models_dropdown").val(search_spec.searches[0].datamodel);
        	}
        	
        	if( search_spec.searches[0].hasOwnProperty('object') ){
        		mvc.Components.get("objects_dropdown").val(search_spec.searches[0].object);
        	}
        	
        	// Input lookup
        	if( search_spec.searches[0].hasOwnProperty('inputlookup') ) {
        		mvc.Components.getInstance("sources_dropdown").val('input_lookup');
        		mvc.Components.get("lookups_dropdown").val(search_spec.searches[0].inputlookup.lookupName);
        		
        		if( search_spec.searches[0].inputlookup.hasOwnProperty('timeField') ) {
        			mvc.Components.getInstance("lookup_time_field_dropdown").val(search_spec.searches[0].inputlookup.timeField);
        		}
        	}
        	
        	// Split by
        	var splitbys = [];
        	this.split_by_aliases = {};
        	
        	for(var i = 0; i < this.getPropertyIfAvailable(search_spec.searches[0], 'splitby', []).length; i++){
        		splitbys.push(search_spec.searches[0].splitby[i].attribute);
        		this.split_by_aliases[search_spec.searches[0].splitby[i].attribute] = search_spec.searches[0].splitby[i].alias;
        	}
        	
        	mvc.Components.get("split_by_dropdown").val(splitbys);
        	
        	// Results filter
        	if( this.getPropertyIfAvailable(search_spec.searches[0], 'resultFilter', null) !== null ){
        		mvc.Components.get("attributes_post_aggregate_dropdown").val(search_spec.searches[0].resultFilter.field);
            	mvc.Components.get("comparator_dropdown").val(search_spec.searches[0].resultFilter.comparator);
            	mvc.Components.get("operand_input").val(search_spec.searches[0].resultFilter.value);
        	}
        	
        	// Aggregates
        	if( this.getPropertyIfAvailable(search_spec.searches[0], 'aggregates', []).length > 0 ){
        		
        		// Render the aggregate list page with the given aggregates
        		this.renderAggregateListPage(search_spec.searches[0].aggregates);
        	}
        	
        	// Event filter
        	mvc.Components.get("event_filter_input").val( this.getPropertyIfAvailable(search_spec.searches[0], 'eventFilter', "") );
        	this.updateEventFilterSearchDescription(); // Update the search description
        	
        	// Return true to indicate that we successfully loaded the search
        	this.search_spec = search_spec;
        	return true;
        },
        
        /**
         * Go to the previous page.
         */
        gotoPrevPage: function(){
        	
        	var current_page_state = this.getPageState();
        	
        	// If the page indicates the next page, then load it
        	if( current_page_state === null ){
        		return;
        	}
        	else if(current_page_state.hasOwnProperty('previous_state_id')){
        		this.changePage(current_page_state.previous_state_id, false);
        	}
        	else if( current_page_state.hasOwnProperty('initial_state') === true || current_page_state.initial_state === true ){
            	return; // This is the first state, no where to go
        	}
        	else{
        		this.changePage(current_page_state.state_id - 1, false);
        	}
        	
        },
        
        /**
         * Show the warning message.
         */
        hideWarning: function(){
        	$('#warning-message', this.$el).hide();
        },
        
        /**
         * Show the warning message.
         */
        showWarning: function(message){
        	$('#warning-message-text', this.$el).text(message);
        	$('#warning-message', this.$el).show();
        },
        
        /**
         * Parse a data model object name and get just the object name (last segment).
         */
        extractDataModelObjectName: function(name){
        	var parse_name_re = /[^.]*[.]([^.]+)/i;
        	
        	var result = parse_name_re.exec(name);
        	
        	if( result === null ){
        		return name;
        	}
        	else{
        		return parse_name_re.exec(name)[1];
        	}
        },
        
        /**
         * Validate the data model selection page.
         */
        validateDataModelSelection: function(){
        	
        	this.hideWarning();
        	
        	var source_selected = mvc.Components.getInstance("sources_dropdown").val();
        	var lookup_selected = mvc.Components.getInstance("lookups_dropdown").val();
        	var model_selected = mvc.Components.get("models_dropdown").val();
        	var object_selected = mvc.Components.get("objects_dropdown").val();
        	
        	// Data model selection validation
        	if( source_selected == "data_model" ){
	        	if( !model_selected ){
	        		this.showWarning("Please select a data model");
	        		return false;
	        	}
	        	
	        	else if( !object_selected ){
	        		this.showWarning("Please select an object");
	        		return false;
	        	}
        	}
        	
        	// Lookup selection validation
	        else if( !lookup_selected ){
        		this.showWarning("Please select a lookup file");
        		return false;
        	}
        	
        	return true;
            
        },
        
        /**
         * Validate the aggregate edit page.
         */
        validateAggregateSelection: function(){
        	
        	this.hideWarning();
        	
        	var fx_selected = mvc.Components.get("functions_dropdown").val();
        	var attribute_selected = mvc.Components.get("attributes_dropdown").val();
        	
        	if( !fx_selected ){
        		this.showWarning("Please select a function");
        		return false;
        	}
        	
        	else if( fx_selected != 'count' && !attribute_selected ){
        		this.showWarning("Please select an attribute");
        		return false;
        	}
        	
        	return true;
            
        },
        
        /**
         * Validate the time-range page.
         */
        validateTimeRangeSelection: function(){
        	
        	this.hideWarning();
        	
        	var start_time = mvc.Components.get("start_time_input").val();
        	var end_time = mvc.Components.get("end_time_input").val();
        	
        	// Don't require a time field for lookups if the time field is empty
        	if( mvc.Components.getInstance("sources_dropdown").val() == "input_lookup" && !mvc.Components.getInstance("lookup_time_field_dropdown").val() ){
        		return true;
        	}
        	
        	if( !start_time ){
        		this.showWarning("Please define a start-time");
        		return false;
        	}
        	
        	else if( !end_time ){
        		this.showWarning("Please define an end-time");
        		return false;
        	}
        	
        	return true;
            
        },
        
        /**
         * Show or hide the aggregates table depending on if we have aggregates.
         */
        showOrHideAggregatesTable: function(){
        	
        	if(this.aggregatesCount() === 0){
        		$("#aggregates-list", this.$el).hide();
        	}
        	else{
        		$("#aggregates-list", this.$el).show();
        	}
        },
        
        /**
         * Validate the filter selection.
         */
        validateFilterSelection: function(){
        	
        	this.hideWarning();
        	
        	var function_selected = mvc.Components.get("functions_dropdown").val();
        	var attribute_selected = mvc.Components.get("attributes_dropdown").val();
        	var value_defined = mvc.Components.get("operand_input").val();
        	
        	if( !attribute_selected == "*" ){
	        	if( !function_selected ){
	        		this.showWarning("Please select a function");
	        		return false;
	        	}
	        	else if( !attribute_selected ){
	        		this.showWarning("Please select an attribute");
	        		return false;
	        	}
	        	else if( !value_defined ){
	        		this.showWarning("Please define a value to filter on");
	        		return false;
	        	}
        	}
        	
        	return true;
            
        },
        
        /**
         * Get a count of the number of aggregates.
         */
        aggregatesCount: function(){
        	
        	var count = 0;
        	
        	for(var a in this.search_aggregate_views) {
        	    if (this.search_aggregate_views.hasOwnProperty(a)) {
        	    	count++;
        	    }
        	}
        	
        	return count;
        	
        },
        
        /**
         * Render the current page.
         */
        changePage: function(new_page_state_id, forward){
        	
        	// Hide the warnings by default
        	this.hideWarning();
        	
        	// Do validation here and return if the page should not be changed:
        	
        	// 	* If on the data model selection page, validate the selection
        	if(this.page_state === this.page_states.data_model_selection_page.state_id && forward){
        		if( !this.validateDataModelSelection() ){
        			return;
        		}
        	}
        	
        	// * If on the match logic page, validate filtering
        	else if(this.page_state === this.page_states.match_logic_selection_page.state_id && forward){
        		if( !this.validateFilterSelection() ){
        			return;
        		}
        	}
        	
        	// * If on the results filter page and going backwards, then skip to the aggregate list page if we have no aggregates (need to skip the split-by page)
        	else if(this.page_state === this.page_states.match_logic_selection_page.state_id && !forward && this.aggregatesCount() === 0){
        		new_page_state_id = this.page_states.aggregate_list_page.state_id;
        	}
        	
        	// * If on the results filter page and going backwards, then skip to the split-by list page if we have no split-bys but we do have aggregates (need to skip the split-by alias page)
        	else if(this.page_state === this.page_states.match_logic_selection_page.state_id && !forward && this.aggregatesCount() !== 0 && mvc.Components.get("split_by_dropdown").val().length === 0){
        		new_page_state_id = this.page_states.split_by_selection_page.state_id;
        	}
        	
        	// * If on the split-by page and going backwards, then skip to the aggregate list (skip the edit page)
        	else if(this.page_state === this.page_states.split_by_selection_page.state_id && !forward){
        		new_page_state_id = this.page_states.aggregate_list_page.state_id;
        	}
        	
        	// * If on the event filter page and the search is invalid, then stop
        	else if(this.page_state === this.page_states.event_filter_page.state_id && forward){
        		
        		// Make sure the search is updated
        		this.updateEventFilterSearchDescription();
        		
        		// Stop if the search is invalid
        		if(!this.search_parses){
        			return;
        		}
        	}
        	
        	// * If on the aggregation edit page, then go back to the list
        	else if(this.page_state === this.page_states.aggregate_edit_page.state_id && forward){
        		
        		if( !this.validateAggregateSelection() ){
        			return;
        		}
        		
        		// Edit or create the aggregate
        		this.updateOrCreateAggregate();
        		
        		// Go back to the list page
        		new_page_state_id = this.page_states.aggregate_list_page.state_id;
        	}
        	
        	// * If on the aggregation list page and we have no aggregates, then skip the split-by
        	else if(this.page_state === this.page_states.aggregate_list_page.state_id && forward && this.aggregatesCount() === 0 && new_page_state_id != this.page_states.aggregate_edit_page.state_id){
        		new_page_state_id = this.page_states.match_logic_selection_page.state_id;
        	}
        	
        	// * If on the split-by list page and we have no split-bys, then skip the split-by alias page
        	else if(this.page_state === this.page_states.split_by_selection_page.state_id && forward && mvc.Components.get("split_by_dropdown").val().length === 0 && new_page_state_id != this.page_states.aggregate_edit_page.state_id){
        		new_page_state_id = this.page_states.match_logic_selection_page.state_id;
        	}
        	
        	// * If on the time-range page, then make sure that times are valid
        	else if(this.page_state === this.page_states.time_selection_page.state_id && forward){
        		if( !this.validateTimeRangeSelection() ){
        			return;
        		}
        	}
        	
        	// Do page specific rendering things here
        	
        	// * If on the final page, render the search string
        	if(new_page_state_id === this.page_states.finalize_search_page.state_id){
        		this.renderSearchDescription('#search-description');
        	}
        	
        	// * If on the aggregate list page, update the attributes in the aggregate edit page so that if the user goes to the editor, it will be pre-populated
        	if(new_page_state_id === this.page_states.aggregate_list_page.state_id){
        		this.updateAvailableFieldsList("attributes_dropdown", false, false);
        	}
        	
        	// * If on the split-by page, then update the attributes and clear the split-bys if they are not in the given source
        	if(new_page_state_id === this.page_states.split_by_selection_page.state_id){
        		this.updateAvailableFieldsList("split_by_dropdown", false, false, false);
        		
        		// Get the current settings for the splits-bys
        		var splitbys = mvc.Components.get("split_by_dropdown").val();
        		
        		// Determine which of the splits-bys are valid for this source and store them
        		var valid_splitbys = [];
        		
        		for( var i = 0; i < splitbys.length; i++){
        			if( $.inArray(splitbys[i], this.available_fields) >= 0 ){
        				valid_splitbys.push(splitbys[i]);
        			}
        		}
        		
        		// Set the values  	
        		mvc.Components.getInstance("split_by_dropdown").val(valid_splitbys);
        		
        	}
        	
        	// * If on the split-by alias page, then render the alias split-by selection page
        	if(new_page_state_id === this.page_states.split_by_alias_page.state_id){
        		this.renderSplitByAliases();
        	}
        	
        	// * If leaving the split-by alias page, then store the aliases
        	if(this.page_state === this.page_states.split_by_alias_page.state_id){
        		this.persistSplitByAliases();
        	}
        	
        	// * If on the match logic page, then update the attributes post-aggregates
        	if(new_page_state_id === this.page_states.match_logic_selection_page.state_id){
        		this.updateAvailableFieldsList("attributes_post_aggregate_dropdown", true, true);
        	}
        	
        	// * If on the events filter page, then update the search description
        	if(new_page_state_id === this.page_states.event_filter_page.state_id){
        		this.updateEventFilterSearchDescription();
        	}
        	
        	// * If on the time selection page, then update the list of fields
        	if(new_page_state_id === this.page_states.time_selection_page.state_id){
        		this.updateAvailableFieldsList("lookup_time_field_dropdown", false, false, false);
        	}
        	
        	// Update the breadcrumbs
        	$(".step", this.$el).addClass("inactive");
        	$(".step-" + new_page_state_id, this.$el).removeClass("inactive");
        	
        	// Hide all pages by default
        	for (var page in this.page_states) {
        		$(this.page_states[page].element_id, this.$el).hide();
        	}
        	
        	// Get the current page
        	var current_page_state = this.getPageState();
        	
        	// Get the next page
        	var next_page_state = this.getPageState(new_page_state_id);
        	
        	// If this is the final state, then swap the "next" button for the "save" button
        	if(next_page_state.hasOwnProperty('final_state') && next_page_state.final_state){
        		$(".btn-finalize", this.$el).show();
        		$(".btn-next", this.$el).hide();
        	}
        	else{
        		$(".btn-finalize", this.$el).hide();
        		$(".btn-next", this.$el).show();
        	}
        	
        	// Toggle the previous button if a state exists to go to
        	if(next_page_state.hasOwnProperty('initial_state') && next_page_state.initial_state){
        		$(".btn-prev", this.$el).prop('disabled', true);
        	}
        	else{
        		$(".btn-prev", this.$el).prop('disabled', false);
        	}
        	
        	// If we are already on the page, do nothing
        	if( current_page_state.state_id === new_page_state_id ){
        		$(next_page_state.element_id, this.$el).show();
        		return;
        	}
        	
        	// Slide in the new panel
        	this.slideInPanel( $(current_page_state.element_id, this.$el), $(next_page_state.element_id, this.$el), forward );
        	
        	// Store the current page state
        	this.page_state = new_page_state_id;
        },
        
        /**
         * Save the list of data-models.
         */
        setDataModelsList: function(data_models){
        	this.data_models = data_models;
        	
        	// Populate the list of models
        	var choices = [];
        	
        	for(var i=0; i < data_models.length; i++){
        		choices.push( { 'label': data_models[i].name, 'value': data_models[i].name } );
        	}
        	
        	mvc.Components.getInstance("models_dropdown").settings.set("choices", choices);
        	
        	// Update the list of objects for the given model
        	this.updateObjectsList();
        },
        
        /**
         * Get the list of available data-models.
         */
        getDataModelsList: function(async){

        	// If the async parameter wasn't provided, then get it
        	if( typeof async == 'undefined' ){
        		async = true;
        	}
        	
        	// Get 'em
            $.ajax( 
                    {
                        url:  Splunk.util.make_url('/custom/SA-ThreatIntelligence/customsearchbuilder/get_data_models'),
                        type: 'GET',
                        async: async,
                        success: function(data, textStatus, jqXHR){
                        	this.setDataModelsList(data);
                        }.bind(this),
                        
                        error: function(jqXHR,textStatus,errorThrown) {
                        	alert("Unable to get the list of data-models");
                        } 
                    }
            );
            
        },
        
        /**
         * Get the list of available time presets.
         */
        getTimePresets: function(){

        	// If the async parameter wasn't provided, then get it
        	if( typeof async == 'undefined' ){
        		async = true;
        	}
        	
        	// Get 'em
            $.ajax( 
                    {
                    	url:  Splunk.util.make_url('/splunkd/__raw/services/data/ui/times?output_mode=json'),
                        type: 'GET',
                        success: function(data, textStatus, jqXHR){
                        	this.setTimePresetsList(data.entry);
                        }.bind(this),
                        
                        error: function(jqXHR,textStatus,errorThrown) {
                        	alert("Unable to get the list of data-models");
                        } 
                    }
            );
            
        },
        
        /**
         * Save the list of time presets.
         */
        setTimePresetsList: function(time_presets){
        	this.time_presets = time_presets;
        	
        	// Populate the list of models
        	var choices = [];
        	
        	for(var i=0; i < time_presets.length; i++){
        		
        		// Some times don't have the earliest time. Don't include these.
        		if( time_presets[i].content.earliest_time ){
        			choices.push( { 'label': time_presets[i].content.label, 'value': time_presets[i].name } );
        		}
        	}
        	
        	mvc.Components.getInstance("time_preset_dropdown").settings.set("choices", choices);
        	
        	// Update the list of objects for the given model
        	this.updateObjectsList();
        },
        
        /**
         * Sync the time preset input with the earliest and latest times
         */
        syncTimePreset: function(earliest_time, latest_time){
        	
        	if( this.time_presets === null ){
        		return;
        	}
        	
        	// Find the existing time preset
        	for(var c = 0; c < this.time_presets.length; c++ ){
        		if( this.time_presets[c].content.earliest_time == earliest_time && this.time_presets[c].content.latest_time == latest_time ){
        			mvc.Components.get("time_preset_dropdown").val(this.time_presets[c].name);
        			return;
        		}
        	}
        	
        	// No matching presets, clear the selection
        	mvc.Components.get("time_preset_dropdown").val("");
        },
        
        /**
         * Get the raw search from the JSON advanced search specification.
         */
        updateAvailableFieldsList: function(instance_id, include_aggregates, include_split_bys, async, search_spec){
        	
        	// If the search spec parameter wasn't provided, then get it
        	if( typeof search_spec == 'undefined' ){
        		search_spec = this.getSearchSpec(include_aggregates, include_split_bys, true, true);
        	}
        	
        	// If the async parameter wasn't provided, then get it
        	if( typeof async == 'undefined' ){
        		async = true;
        	}
        	
        	var params = { 'search_spec' : JSON.stringify(search_spec) };
        	
            // Do it
            $.ajax( 
                    {
                        url:  Splunk.util.make_url('/custom/SA-ThreatIntelligence/customsearchbuilder/get_available_fields'),
                        type: 'GET',
                        data: params,
                        async: async,
                        success: function(data, textStatus, jqXHR){
                        	
                        	if( data.hasOwnProperty('success') && data.success ){
                        		this.setAvailableFields(data.available_fields, instance_id);
                        	}
                        	else{
                        		alert(data.message);
                        		console.error(data.message);
                        	}
                        }.bind(this),
                        
                        error: function(jqXHR,textStatus,errorThrown) {
                        	alert("Unable to retrieve the available fields");
                        } 
                    }
            );
            
        },
        
        /**
         * Populate the list of lookups
         */
        populateLookupsList: function(){
        	
        	var params = {
        					'count' : "-1",
        					'output_mode' : "json"
        				};
        	
            // Determine if the endpoint for making correlation searches is available and if the ability to make correlation searches ought to be presented
            $.ajax( 
                    {
                        url:  Splunk.util.make_url('/splunkd/__raw/services/data/transforms/lookups'),
                        type: 'GET',
                        data: params,
                        async: true,
                        success: function(data, textStatus, jqXHR){
                        	
                        	var choices = [];
                        	
                        	for(var i=0; i < data.entry.length; i++){
                        		choices.push( { 'label': data.entry[i].name, 'value': data.entry[i].name } );
                        	}
                        	
                        	mvc.Components.getInstance("lookups_dropdown").settings.set("choices", choices);
                        	
                        }.bind(this),
                        
                        error: function(jqXHR,textStatus,errorThrown) {
                        	alert("Unable to get the lookups list");
                        } 
                    }
            );
        },
        
        /**
         * Update the list of available fields.
         */
        setAvailableFields: function(available_fields, instance_id){
        	
        	// Store the available fields in case they are needed in the future
        	this.available_fields = available_fields;
        	
        	// Get the instance of the widget to update
        	var attributes_instance = mvc.Components.getInstance(instance_id);
        	
        	// If the fields are null, then just revert to using the fields from the search
        	if( available_fields === null ){
        		attributes_instance.settings.set("choices", undefined);
        		return;
        	}
        	
        	// Set the fields
        	var choices = [];
        	
        	for(var i = 0; i < available_fields.length; i++){
        		choices.push( {"value": available_fields[i], "label": available_fields[i]} );
        	}
        	
        	attributes_instance.settings.set("choices", choices);
        	
        },
        
        /**
         * Get the raw search from the JSON advanced search specification.
         */
        getSearchFromJSON: function(search_spec, include_detailed_info){
        	
        	// Set the default for 'indicate_if_parses'
        	if( typeof include_detailed_info === 'undefined' ){
        		include_detailed_info = false;
        	}
        	
        	var params = { 'search_spec' : JSON.stringify(search_spec) };
        	var search_info = null;
        	
            $.ajax( 
                    {
                        url:  Splunk.util.make_url('/custom/SA-ThreatIntelligence/customsearchbuilder/make_search_from_spec'),
                        type: 'GET',
                        data: params,
                        async: false,
                        success: function(data, textStatus, jqXHR){
                        	
                        	if( data.hasOwnProperty('success') && data.success ){
                        		search_info = {'raw_search' : data.raw_search, "parses" : data.parses };
                        	}
                        	else{
                        		alert(data.message);
                        	}
                        },
                        
                        error: function(jqXHR,textStatus,errorThrown) {
                        	alert("Unable to make a search from the specification");
                        } 
                    }
            );
            
            // Return the result depending on if the caller wanted the parses info
            if( include_detailed_info ){
            	return search_info;
            }
            else if( search_info === null){
            	return null;
            }
            else{
            	return search_info.raw_search;
            }
            
        },
        
        /**
         * Get the page state object for the current state.
         */
        getPageState: function(page_state){
        	
        	if(typeof page_state == "undefined"){
        		page_state = this.page_state;
        	}
        	
        	var current_page_state = null;
        	
        	// Find the current page
        	for (var page in this.page_states) {
        		
        		if( this.page_states[page].state_id === page_state ){
        			current_page_state = this.page_states[page];
        			break;
        		}
        	}
        	
        	return current_page_state;
        },
        
        /**
         * Go the next page.
         */
        gotoNextPage: function(){

        	var current_page_state = this.getPageState();
        	
        	// If the page indicates the next page, then load it
        	if( current_page_state === null ){
        		return;
        	}
        	else if(current_page_state.hasOwnProperty('next_state_id')){
        		this.changePage(current_page_state.next_state_id, true);
        	}
        	else if(current_page_state.hasOwnProperty('final_state') && current_page_state.final_state){
        		return; // This is a final state stop
        	}
        	else{
        		this.changePage(current_page_state.state_id + 1, true);
        	}
        	
        },
        
        /**
         * Update or create the aggregate.
         */
        updateOrCreateAggregate: function(){
        	
        	// Get the data
        	var fx = mvc.Components.get("functions_dropdown").val();
        	var attribute = mvc.Components.get("attributes_dropdown").val();
        	var alias = mvc.Components.get("aggregate_alias").val();
        	
        	if( !fx || (!attribute && fx !== "count") ){
        		// Yikes, not enough information provided
        		console.warn("Not enough information provided to make the aggregate");
        		return;
        	}
        	
        	// Populate the alias name automatically if need be
        	if(alias.length === 0){
        		alias = null;
        	}
        	
        	// Create the new entry if necessary
        	if(this.editing_aggregate === null){
        		this.makeAggregate( this.aggregatesCount(), fx, attribute, alias );
        	}
        	
        	// Edit the existing entry
        	else{
        		this.search_aggregate_views[this.editing_aggregate].fx = fx;
        		this.search_aggregate_views[this.editing_aggregate].attribute = attribute;
        		this.search_aggregate_views[this.editing_aggregate].alias = alias;
        		this.search_aggregate_views[this.editing_aggregate].render();
        	}
        	
        },
        
        /**
         * Make a new aggregate.
         */
        newAggregate: function(){
        	
        	// Set the aggregate we are editing to null, this will cause a new one to be created
        	this.editing_aggregate = null;
        	
        	// Populate the form
        	mvc.Components.get("functions_dropdown").val(undefined);
        	mvc.Components.get("attributes_dropdown").val(undefined);
        	mvc.Components.get("aggregate_alias").val("");
        	
        	// Change the page
        	this.changePage(this.page_states.aggregate_edit_page.state_id, true);
        },
        
        /**
         * Modify the split-by alias
         */
        modifySplitByAlias: function(split_by_identifier, alias){
        	alert("Editing split-by");
        },
        
        /**
         * Render the list of split-by aliases
         */
        renderSplitByAliases: function(){
        	
        	// Clear the existing aliases
        	$("#split-by-alias-list > tbody", this.$el).empty();
        	
        	// Declare the template
        	var template = '<tr><td><%- attribute %></td>'+
			'<td><input class="split-by-alias" name="alias" data-attr="<%- attribute %>" value="<%- alias %>"></input></td></tr>';
        	
        	// Get the split-bys
        	var split_bys = mvc.Components.get("split_by_dropdown").val();
        	var alias = null;
        	
        	// Render each split-by alias
        	for( var c = 0; c < split_bys.length; c++ ){
        		
        		// Find the alias if it exists
        		alias = this.split_by_aliases[split_bys[c]];
        		
        		if( !alias ){
        			alias = "";
        		}
        		
        		// Append the row
        		$(_.template(template, {
        			'alias': alias,
        			'attribute' : split_bys[c],
        			'identifier' : split_bys[c]
        		})).appendTo($("#split-by-alias-list > tbody", this.$el));
        	}
        },
        
        /**
         * Get the split-by aliases
         */
        persistSplitByAliases: function(){
        	
        	var selector = null;
        	
        	for( var c = 0; c < $(".split-by-alias").length; c++){
        		// Store the alias
        		selector = $($(".split-by-alias")[c]);
        		this.split_by_aliases[selector.attr("data-attr")] = selector.val();
        	}
        	
        	return this.split_by_aliases;
        	
        },
        
        /**
         * Show the form for editing the given aggregate.
         */
        editAggregate: function(aggregate_identifier, fx, attribute, alias){
        	
        	// Remember which aggregate we are editing
        	this.editing_aggregate = aggregate_identifier;
        	
        	// Populate the form
        	mvc.Components.get("functions_dropdown").val(fx);
        	mvc.Components.get("attributes_dropdown").val(attribute);
        	mvc.Components.get("aggregate_alias").val(alias);
        	
        	// Change the page
        	this.changePage(this.page_states.aggregate_edit_page.state_id, true);
        },
        
        /**
         * Remove the given aggregate
         */
        removeAggregate: function(aggregate_identifier){
        	this.search_aggregate_views[aggregate_identifier].remove();
        	delete this.search_aggregate_views[aggregate_identifier];
        	this.showOrHideAggregatesTable();
        },
        
        /**
         * Finalize the search and report the results back to the caller.
         */
        finalizeSearch: function(){
        	
        	this.search_spec = this.getSearchSpec(true, true, true, false);
        	this.search_string = this.getSearchFromJSON(this.search_spec, false);
        	
        	Backbone.trigger("guided-mode-search-updated-event", this.search_string, this.search_spec, mvc.Components.get("start_time_input").val(), mvc.Components.get("end_time_input").val());
        },
        
        /**
         * Get the created search string
         */
        getSearchString: function(search_spec, start_time, end_time, suppress_fields){
        	
        	// If the search spec wasn't provided, then get it
        	if( typeof search_spec == 'undefined' ){
        		search_spec = this.getSearchFromJSON(search_spec, false);
        	}
        	
        	// Update the suppression fields
        	if(suppress_fields){
        		search_spec['alert.suppress.fields'] = suppress_fields;
        		search_spec['alert.suppress'] = 1;
        	}
        	else{
        		delete search_spec['alert.suppress.fields'];
        		delete search_spec['alert.suppress'];
        	}
        	
        	// Set the start and end time in the spec
        	search_spec.searches[0].latest = end_time;
        	search_spec.searches[0].earliest = start_time;

        	return this.getSearchFromJSON(search_spec, false);
        },
        
        /**
         * Make a name for an aggregate alias
         */
        getAliasNameForAggregate: function(function_name, field_name){
        	return function_name + "(" + this.getAliasNameForSplitBy(field_name) + ")";
        },
        
        /**
         * Make a name for to alias a split-bny
         */
        getAliasNameForSplitBy: function(field_name){
        	
        	var parse_name_re = r = /([^.]+[.])*([^.]+)/i;
        	
        	var parsed = parse_name_re.exec(field_name);
        	
        	if( parsed ){
        		return parsed[2];
        	}
        	else{
        		return field_name;
        	}
        },
        
        /**
         * Get the search JSON specification
         */
        getSearchSpec: function(include_aggregates, include_split_bys, include_result_filters, single_only){
        	
        	// Set the defaults
        	if(typeof include_aggregates == 'undefined'){
        		include_aggregates = true;
        	}
        	
        	if(typeof include_split_bys == 'undefined'){
        		include_split_bys = true;
        	}
        	
        	if(typeof include_result_filters == 'undefined'){
        		include_result_filters = true;
        	}
        	
        	if(typeof single_only == 'undefined'){
        		single_only = false;
        	}
        	
        	// Get the values
        	var source_selected = mvc.Components.getInstance("sources_dropdown").val();
        	var lookup_selected = mvc.Components.getInstance("lookups_dropdown").val();
        	var obj = mvc.Components.get("objects_dropdown").val();
        	var datamodel = mvc.Components.get("models_dropdown").val();
        	var start_time = mvc.Components.get("start_time_input").val();
        	var end_time = mvc.Components.get("end_time_input").val();
        	var func = mvc.Components.get("functions_dropdown").val();
        	var aggregate = mvc.Components.get("attributes_dropdown").val() ;
        	var aggregate_alias = mvc.Components.get("aggregate_alias").val();
        	var attribute = mvc.Components.get("attributes_post_aggregate_dropdown").val() ;
        	var split_by = mvc.Components.get("split_by_dropdown").val();
        	var operand = mvc.Components.get("operand_input").val();
        	var comparator = mvc.Components.get("comparator_dropdown").val();
        	var event_filter = mvc.Components.get("event_filter_input").val();
        	
        	var time_field = mvc.Components.getInstance("lookup_time_field_dropdown").val();
        	
        	// Make the JSON
        	var advanced_search = {};
        	
        	// Get the data model information
        	if( source_selected == "data_model" ){
	        	advanced_search.datamodel = datamodel;
	        	advanced_search.object = obj;
        	}
        	
        	// Get the input lookup information
        	else{
        		advanced_search.inputlookup = {
        				'lookupName':  lookup_selected
        		};
        		
        		if( time_field ){
        			advanced_search.inputlookup.timeField = time_field;
        		}
        	}
        	
        	// Specify times if the search is for a data_model or if the time field is included for an input lookup 
        	if( source_selected == "data_model" || time_field ){
	        	if( start_time && start_time.length > 0){
	        		advanced_search.earliest = start_time;
	        	}
	        	
	        	if( end_time && end_time.length > 0){
	        		advanced_search.latest = end_time;
	        	}
        	}
        	
        	// Add the suppression information
        	if( this.suppress_fields ){
	        	advanced_search['alert.suppress.fields'] = this.suppress_fields;
	        	advanced_search['alert.suppress'] = 1;
        	}
        	else{
        		advanced_search['alert.suppress'] = 0;
        	}
        	
        	// Add the aggregates
        	if( include_aggregates === true && this.aggregatesCount() > 0 ){
        		
        		advanced_search.aggregates = [];
        		var alias_info = {};
        		
        		for(var a in this.search_aggregate_views) {
        			
        			alias_info = {'function' : this.search_aggregate_views[a].fx, 'attribute': this.search_aggregate_views[a].attribute };
        			
        			// If an alias was defined, then include it
        			if( this.search_aggregate_views[a].alias ){
        				alias_info['alias'] = this.search_aggregate_views[a].alias;
        			}
        			
        			// Add the alias to the list
        			advanced_search.aggregates.push(alias_info);
        		}
        	}
        	
        	// get the events filter
        	if(event_filter){
        		advanced_search.eventFilter = event_filter;
        	}
        	
        	// Get the results filter info
        	if( include_result_filters && attribute && operand && comparator ){
	        	advanced_search.resultFilter = {
	        			'field':  attribute,
	        			'comparator': comparator,
	        			'value': operand
	        	};
        	}
        	
        	// Add the split-by info
        	if( this.aggregatesCount() > 0 && include_split_bys && split_by.length > 0 ){
        		var split_bys = [];
        		var alias = "";
        		
        		for(var i = 0; i < split_by.length; i++){
        			
        			// Determine what the alias is (if one is defined)
        			alias = this.split_by_aliases[split_by[i]];
        			
        			// If empty, then define an alias for the user
        			if( alias === "" || alias === undefined ){
        				alias = this.getAliasNameForSplitBy(split_by[i]);
        			}
        			
        			split_bys.push({
        				'attribute' : split_by[i],
        				'alias'     : alias
        			});
        		}
        		
        		advanced_search.splitby = split_bys;
        	}
        	
        	// Return the type of response necessary
        	if( single_only ){
        		return advanced_search;
        	}
        	else{
        		return { "searches" : [advanced_search], "version" : "1.0" };
        	}
        	
        },
        
        /**
         * Render the search description on the form.
         */
        renderSearchDescription: function(id, search_spec){
        	
        	if( typeof search_spec === 'undefined' ){
	        	search_spec = this.getSearchSpec(true, true, true, false);
        	}
        	
        	var search_info = this.getSearchFromJSON(search_spec, true);
        	
        	if( search_info ){
	        	this.search_string = search_info.raw_search;
	        	this.search_parses = search_info.parses;
        	}
        	else{
        		return;
        	}
        	
        	$(id, this.$el).html( this.getSearchDescription(search_spec, this.search_string, this.search_parses) );
        },
        
        /**
         * Slide in a panel and slide out the old one.
         */
        slideInPanel: function(cur_el, next_el, forward){
        	
        	// This is the speed of the animation. This should be a sane default.
        	var speed = 200;
        	
        	//Define the CSS for the difference between the height and position
        	var cur = {
        		height: cur_el.height()+'px'
        	};

        	var next = {
        		height: next_el.height() +'px',
        		left: '0px',
        		position: 'relative'
        	};
        	
        	// Go ahead and hide the current item and show the next one that we will be pulling into the screen
        	cur_el.hide();
        	next_el.show();
        	
        	// Setup the position of the next div before we start the animation
        	if(forward){
	        	next_el.css({
	        		left: cur_el.width()+'px',
	        		position: 'relative'
	        	});
        	}
        	else{
	        	next_el.css({
	        		left: (-1 * cur_el.width()) +'px',
	        		position: 'relative'
	        	});
        	}
        	
        	// Animate it
        	next_el.css(cur).animate(next, speed);
        	
        },
        
        /**
         * Get an HTML representation that describes this search.
         */
        getSearchDescription: function(search_spec, string_string, search_parses){
        	
        	// Make the meta-data to describe the search
        	var search_meta = this.clone(search_spec);
        	search_meta.search_string = string_string;
        	search_meta.parses = search_parses;
        	
            // Get the template
            var search_description_template = $("#search-description-template", this.$el).text();
            
            // Render the table
            return _.template(search_description_template, search_meta);
        	
        },
        
        /**
         * Render the page for indicating the search logic.
         */
        renderAggregateEditPage: function(){
        	
            // Make the input for the list of functions
            var functions_dropdown = new DropdownInput({
                "id": "functions_dropdown",
                "choices": [
                    {"value": "avg", "label": "avg"},
                    {"value": "count", "label": "count"},
                    {"value": "dc", "label": "dc"},
                    {"value": "min", "label": "min"},
                    {"value": "median", "label": "median"},
                    {"value": "max", "label": "max"},
                    {"value": "stdev", "label": "stdev"},
                    {"value": "sum", "label": "sum"},
                    {"value": "values", "label": "values"},
                    {"value": "earliest", "label": "earliest"},
                    {"value": "latest", "label": "latest"},
                    {"value": "estdc", "label": "estdc"},
                    {"value": "estdc_error", "label": "estdc_error"},
                    {"value": "first", "label": "first"},
                    {"value": "last", "label": "last"},
                    {"value": "list", "label": "list"},
                    {"value": "mean", "label": "mean"},
                    {"value": "mode", "label": "mode"},
                    {"value": "per_day", "label": "per_day"},
                    {"value": "per_hour", "label": "per_hour"},
                    {"value": "per_minute", "label": "per_minute"},
                    {"value": "per_second", "label": "per_second"},
                    {"value": "range", "label": "range"},
                    {"value": "stdevp", "label": "stdevp"},
                    {"value": "sumsq", "label": "sumsq"},
                    {"value": "var", "label": "var"},
                    {"value": "varp", "label": "varp"}
                ],
                "selectFirstChoice": false,
                "showClearButton": true,
                "el": $('#functions-dropdown')
            }, {tokens: true}).render();
        	
            // Make the input for the list of attributes
        	var attributes_dropdown = new DropdownInput({
                "id": "attributes_dropdown",
                "choices": [
                    //{"value": "*", "label": "None"}
                ],
                "selectFirstChoice": false,
                "default": "",
                "valueField": "attribute_id",
                "labelField": "attribute",
                "showClearButton": true,
                "el": $('#attributes-dropdown')
			}, {tokens: true}).render();
        	
        	// The input for the aggregate alias
        	var aggregate_alias_input = new TextInput({
                "id": "aggregate_alias",
                "searchWhenChanged": false,
                "el": $('#aggregate-alias-input')
            }, {tokens: true}).render();

        	aggregate_alias_input.on("change", function(newValue) {
                FormUtils.handleValueChange(aggregate_alias_input);
            });
        	
        	
        },
        
        /**
         * Render the page for indicating the search logic.
         */
        renderMatchLogicSelectionPage: function(){
        	
        	var attributes_post_aggregate_dropdown = new DropdownInput({
                "id": "attributes_post_aggregate_dropdown",
                "choices": [],
                "selectFirstChoice": false,
                "default": "",
                "valueField": "attribute_id",
                "labelField": "attribute",
                "value": "$form.attribute_post_aggregate$",
                "showClearButton": true,
                "el": $('#attributes-post-aggregate-dropdown')
			}, {tokens: true}).render();
        	
            // Make the input for the list of comparators
            var comparator_dropdown = new DropdownInput({
                "id": "comparator_dropdown",
                "choices": [
                    {"value": ">", "label": "Greater than"},
                    {"value": ">=", "label": "Greater than or equal to"},
                    {"value": "<", "label": "Less than"},
                    {"value": "<=", "label": "Less than or equal to"},
                    {"value": "=", "label": "Equal to"},
                    {"value": "!=", "label": "Not equal to"}
                ],
                "selectFirstChoice": false,
                "value": "$form.comparator$",
                "showClearButton": true,
                "el": $('#comparator-dropdown')
            }, {tokens: true}).render();
        	
        	// The input for the operand
        	var operand_input = new TextInput({
                "id": "operand_input",
                "searchWhenChanged": false,
                "value": "$form.operand$",
                "el": $('#operand-input')
            }, {tokens: true}).render();

        	operand_input.on("change", function(newValue) {
                FormUtils.handleValueChange(operand_input);
            });
        	
        },
        
        /**
         * Clone the provided object.
         */
        clone: function(obj) {
            if (null === obj || "object" != typeof obj){
            	return obj;
            }
            var copy = obj.constructor();
            for (var attr in obj) {
                if (obj.hasOwnProperty(attr)){
                	copy[attr] = this.clone(obj[attr]);
                }
            }
            return copy;
        },
        
        /**
         * Render the page for selecting the split-by
         */
        renderGroupBySelectionPage: function(){
        	
            // Make the input for the list of attributes to split by
            var split_by_dropdown = new MultiSelectInput({
                "id": "split_by_dropdown",
                "valueField": "attribute_id",
                "labelField": "attribute",
                "value": "$form.split_by$",
                "el": $('#split-by-dropdown')
            }, {tokens: true}).render();
            
            split_by_dropdown.on("change", function(newValue) {
                FormUtils.handleValueChange(split_by_dropdown);
            });
        	
        },
        
        /**
         * Update the event filter search description.
         */
        updateEventFilterSearchDescription: function(){
        	this.renderSearchDescription('#search-description-event-filter', this.getSearchSpec(false, false, false, false));
        },
        
        /**
         * Render the page dedicated to selecting a data model
         */
        renderEventFilterPage: function(){
        	
        	// The input for the operand
        	var operand_input = new TextInput({
                "id": "event_filter_input",
                "searchWhenChanged": false,
                "value": "$form.eventfilter$",
                "el": $('#event-filter-input')
            }, {tokens: true}).render();
        	
        	// Force updating of the search description after key presses. The built-in change event is not aggressive enough so we are going to trigger change manually.
        	$('#event-filter-input input').keyup(_.debounce( function(){
        		$('#event-filter-input input').change();
        	}.bind(this), 300) );
        	
        	// Register a handler that ensures that the search description is updated
        	operand_input.on("change", function(newValue) {
                FormUtils.handleValueChange(operand_input);
                
                // Update the event filter description if we have the source information available
                if( (mvc.Components.getInstance("sources_dropdown").val() == 'data_model' && mvc.Components.get("models_dropdown").val() && mvc.Components.get("objects_dropdown").val() ) || (mvc.Components.getInstance("sources_dropdown").val() == 'input_lookup' && mvc.Components.get("lookups_dropdown").val() ) ){
                	this.updateEventFilterSearchDescription();
                }
            }.bind(this));
        	
        },
        
        /**
         * Toggle the visibility of the time inputs depending on if they apply.
         */
        toggleTimeInputs: function(){
        	
            // Hide the earliest and latest time fields if no time field is set
            if( mvc.Components.getInstance("sources_dropdown").val() == 'input_lookup' && ! mvc.Components.getInstance("lookup_time_field_dropdown").val() ){
            	$('#start-time-input').hide();
            	$('#end-time-input').hide();
            }
        	else{
        		$('#start-time-input').show();
            	$('#end-time-input').show();
        	}
        },
        
        /**
         * Render the time-range selection page.
         */
        renderTimeRangeSelectionPage: function(){
        	
        	// The input for the time field
        	var time_field_input = new DropdownInput({
                "id": "lookup_time_field_dropdown",
                "searchWhenChanged": false,
                "selectFirstChoice": false,
                "value": "$form.timeField$",
                "showClearButton": true,
                "el": $('#lookup-time-field-dropdown')
            }, {tokens: true}).render();
        	
        	time_field_input.on("change", function(newValue) {
                FormUtils.handleValueChange(time_field_input);
                this.toggleTimeInputs();
            }.bind(this));
        	
        	// The input for the start time
        	var start_time_input = new TextInput({
                "id": "start_time_input",
                "searchWhenChanged": false,
                "value": "$form.startTime$",
                "el": $('#start-time-input')
            }, {tokens: true}).render();
        	
        	start_time_input.on("change", function(newValue) {
                FormUtils.handleValueChange(start_time_input);
                this.syncTimePreset(newValue, mvc.Components.get("end_time_input").val());
            }.bind(this));
        	
        	// The input for the start time
        	var end_time_input = new TextInput({
                "id": "end_time_input",
                "searchWhenChanged": false,
                "value": "$form.endTime$",
                "el": $('#end-time-input')
            }, {tokens: true}).render();
        	
        	end_time_input.on("change", function(newValue) {
                FormUtils.handleValueChange(end_time_input);
                this.syncTimePreset(mvc.Components.get("start_time_input").val(), newValue);
            }.bind(this));
        	
        	// The input for the time presets
        	var time_preset_input = new DropdownInput({
                "id": "time_preset_dropdown",
                "searchWhenChanged": false,
                "selectFirstChoice": false,
                "value": "$form.timePreset$",
                "showClearButton": true,
                "el": $('#time-preset-dropdown')
            }, {tokens: true}).render();
        	
        	time_preset_input.on("change", function(newValue) {
                FormUtils.handleValueChange(time_preset_input);
                this.applySearchTimes(newValue);
            }.bind(this));
        	
        	this.getTimePresets();
        	
        },
        
        /**
         * Update the list of objects for the selected data-model.
         */
        updateObjectsList: function(){
        	
        	// If we don't have the data-models yet, then just wait
        	if( this.data_models === null ){
        		return;
        	}
        	
        	// Determine which model is selected
        	var model_selected = mvc.Components.get("models_dropdown").val();
        	var data_model = null;
        	
        	if(!model_selected){
        		mvc.Components.getInstance("objects_dropdown").settings.set("choices", []);
        		return;
        	}
        	
        	// Find the model
        	for(var i = 0; i < this.data_models.length; i++){
        		if( this.data_models[i].name == model_selected ){
        			data_model = this.data_models[i];
        			break;
        		}
        	}
        	
        	// Set the list of objects
        	var choices = [];
        	
        	for(i=0; i < data_model.objects.length; i++){
        		choices.push( { 'label': data_model.objects[i], 'value': data_model.objects[i] } );
        	}
        	
        	mvc.Components.getInstance("objects_dropdown").settings.set("choices", choices);
        },
        
        /**
         * Make an aggregate view.
         */
        makeAggregate: function(identifier, fx, attribute, alias){
        	
    		// Make the new place to put the aggregate view
        	var append_to = append_to = $('#aggregates-list > tbody', this.$el);
        	
        	append_to.append('<tr id="aggregate-' + String(identifier) + '"></tr>');
        	var new_el = $('#aggregate-' + String(identifier), this.$el);
    		
    		// Make an aggregate view for this aggregate instance
    		var new_aggregate_view = new SearchAggregateView({
        		'el'         : new_el,
        		'identifier' : identifier,
        		'fx'         : fx,
        		'attribute'  : attribute,
        		'alias'      : alias
        	});
    		
    		// Add it to the list of aggregates
			this.search_aggregate_views[identifier] = new_aggregate_view;
			
			// Render the item in the list
			new_aggregate_view.render();
			
			// Show the table
			this.showOrHideAggregatesTable();
        },
        
        /**
         * Render the page listing the aggregates
         */
        renderAggregateListPage: function( aggregates ){
        	
        	// Clear any existing content
        	$('#aggregates-list > tbody', this.$el).html("");
        	this.search_aggregate_views = {};
        	
        	// Make each aggregate view
        	for(var i = 0; i < aggregates.length; i++){
        		this.makeAggregate(i, aggregates[i]['function'], aggregates[i]['attribute'], this.getPropertyIfAvailable(aggregates[i], 'alias', null) );
        	}
        	
        	this.showOrHideAggregatesTable();
        },
        
        /**
         * Render the page dedicated to selecting a data model
         */
        renderDataModelSelectionPage: function(){
        	
        	// Selection of the data sources
            var sources_dropdown = new DropdownInput({
                "id": "sources_dropdown",
                "choices": ["Data model", "Lookup file"],
                "selectFirstChoice": false,
                "value": "$form.source",
                "showClearButton": false,
                "el": $('#data-source-dropdown')
            }, {tokens: true}).render();
            
            sources_dropdown.on("change", function(newValue) {
                FormUtils.handleValueChange(sources_dropdown);
                
                this.toggleTimeInputs();
                
                var show_data_model_selection = (sources_dropdown.val() == "data_model");
                
                $('#lookup-name-dropdown', this.$el).toggle(!show_data_model_selection);
                $('#lookup-time-field-dropdown', this.$el).toggle(!show_data_model_selection);
                
                $('#models-dropdown', this.$el).toggle(show_data_model_selection);
                $('#objects-dropdown', this.$el).toggle(show_data_model_selection);
                
            }.bind(this));
            
            sources_dropdown.settings.set("choices", [
                                                      {"value": "data_model", "label": "Data model"},
                                                      {"value": "input_lookup", "label": "Lookup file"}
            ]);
            
            sources_dropdown.val("data_model");
            
        	// Lookup files
            var lookups_dropdown = new DropdownInput({
                "id": "lookups_dropdown",
                "choices": [],
                "selectFirstChoice": false,
                "value": "$form.lookup_name$",
                "showClearButton": false,
                "el": $('#lookup-name-dropdown')
            }, {tokens: true}).render();
            
            lookups_dropdown.on("change", function(newValue) {
                FormUtils.handleValueChange(lookups_dropdown);
            });
            
            var models_dropdown = new DropdownInput({
                "id": "models_dropdown",
                "choices": [],
                "selectFirstChoice": false,
                "valueField": "model_id",
                "labelField": "model",
                "value": "$form.dm$",
                "showClearButton": false,
                "el": $('#models-dropdown')
            }, {tokens: true}).render();

            models_dropdown.on("change", function(newValue) {
                FormUtils.handleValueChange(models_dropdown);
                this.updateObjectsList();
            }.bind(this));
            
            // Make the input for the list of objects
            var objects_dropdown = new DropdownInput({
                "id": "objects_dropdown",
                "choices": [],
                "selectFirstChoice": false,
                "valueField": "object",
                "labelField": "object",
                "value": "$form.object$",
                "managerid": "objects_search",
                "showClearButton": false,
                "el": $('#objects-dropdown')
            }, {tokens: true}).render();

            objects_dropdown.on("change", function(newValue) {
                FormUtils.handleValueChange(objects_dropdown);
            });
            
            // Render the list of lookups
            this.populateLookupsList();
            
        },
        
        /**
         * Render the view yo!
         */
        render: function(){
        	
        	// Update the HTML with the modal
        	//this.$el.html(_.template(GuidedSearchEditorViewTemplate, {}));
        	this.$el.html(GuidedSearchEditorViewTemplate);
        	
        	// Render each page
        	this.renderDataModelSelectionPage();
        	this.renderEventFilterPage();
        	this.renderGroupBySelectionPage();
        	this.renderMatchLogicSelectionPage();
        	this.renderAggregateEditPage();
        	this.renderTimeRangeSelectionPage();
        	
        	// Get the data-models info, we are going to need them later
        	this.getDataModelsList();
        	
        	this.showOrHideAggregatesTable();
        },
        
        /**
         * Show the dialog.
         */
        show: function(){
        	
        	// If the search spec isn't supported, then don't let the user continue
        	if( this.search_spec !== null && !this.isSearchSpecVersionSupported(this.search_spec) ){
        		$('#searchSpecNotSupportedModal', this.$el).modal();
        		return;
        	}
        	
        	var next_page_state = this.page_states['string_search_to_be_replaced_page']['state_id'];
        	
        	// Render the appropriate page
        	this.changePage(next_page_state, false);
        	
        	// Show the dialog
        	$('#guidedSearchModal', this.$el).modal();
        }
        
	});

    return GuidedSearchEditorView;
});