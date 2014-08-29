require.config({
    paths: {
        datatables: "../app/SA-Utils/js/lib/DataTables/js/jquery.dataTables",
        bootstrapDataTables: "../app/SA-Utils/js/lib/DataTables/js/dataTables.bootstrap",
        text: "../app/SA-Utils/js/lib/text",
        console: '../app/SA-Utils/js/util/Console'
    },
    shim: {
        'bootstrapDataTables': {
            deps: ['datatables']
        }
    }
});

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "datatables",
    "text!../app/SplunkEnterpriseSecuritySuite/js/templates/CustomSearchesList.html",
    "bootstrapDataTables",
    "css!../app/SplunkEnterpriseSecuritySuite/css/CustomSearchesList.css",
    "css!../app/SA-Utils/js/lib/DataTables/css/jquery.dataTables.css",
    "css!../app/SA-Utils/js/lib/DataTables/css/dataTables.bootstrap.css",
    "css!../app/SA-Utils/css/SplunkDataTables.css",
    "console"
], function( _, Backbone, mvc, $, SimpleSplunkView, dataTable, CustomSearchesListTemplate ){
    // Define the custom view class
    var CustomSearchListView = SimpleSplunkView.extend({
        className: "CustomSearchListView",

        initialize: function() {
            this.searches = null;
            
            options = this.options || {};
            
            // This will contain a list of searches that need to be processed in some way
            this.search_processing_queue = [];
            this.initial_processing_queue_size = 0;
            this.cancel_operation = false;
            
            this.capabilities = null;
            this.correlation_searches = null;
            this.key_indicator_searches = null;
            this.swimlane_searches = null;
            this.show_message_on_complete = true;
        },
        
        events: {
        	"click .key-indicator.accelerate": "showAccelerateKeyIndicatorDialog",
        	"click #accelerate-check-box": "showHideAccelerateTime",
        	"click #save-key-indicator-acceleration": "saveAcceleration",
        	"click #checkall": "checkOrUncheckAll",
        	"click .change_to_enabled": "enableSearch",
        	"click .change_to_disabled": "disableSearch",
        	"click .change_to_scheduled": "convertSearchToScheduled",
        	"click .change_to_realtime": "convertSearchToRealtime",
        	"click #enable-selected-searches" : "enableSearches",
        	"click #disable-selected-searches" : "disableSearches",
        	"click #cancel-operation" : "cancelOperation",
        	"click #close-operation" : "closeOperationDialog",
        	"click #new-search" : "openNewSearchDialog"
        },
        
        /**
         * Open the dialog to select the type of search you want to create.
         */
        openNewSearchDialog: function(){
        	$("#new-search-modal", this.$el).modal();
        },
        
        /**
         * Determine if the user has the given capability.
         */
        hasCapability: function(capability){
        	
        	var uri = Splunk.util.make_url("/splunkd/__raw/services/authentication/current-context?output_mode=json");
        	
        	if( this.capabilities === null ){
        		
	            // Fire off the request
	            jQuery.ajax({
	            	url:     uri,
	                type:    'GET',
	                async:   false,
	                success: function(result) {
	                	
	                	if(result !== undefined){
	                		this.capabilities = result.entry[0].content.capabilities;
	                	}
	                	
	                }.bind(this)
	            });
        	}
            
            return $.inArray(capability, this.capabilities) >= 0;
        	
        },
        
        /**
         * Cancel the given operation.
         */
        cancelOperation: function(){
        	this.cancel_operation = true;
        },
        
        /**
         * Close the dialog that displays progress on queued up searches.
         */
        closeOperationDialog: function(){
        	$("#search-operation-modal", this.$el).modal('hide');
        },
        
        /**
         * Perform an operation on the queued up searches
         */
        doOperationOnQueuedSearches: function(operation, next_function_to_call, success_message){
        	
        	// Go ahead hide the dialog if the operation was cancelled
        	if( this.cancel_operation ){
        		this.closeOperationDialog();
        	}
        	
        	// Re-render if we are done and stop scheduling the calls to 'next_function_to_call'
        	if( this.search_processing_queue.length === 0 || this.cancel_operation ){
        		
        		// Clear the cache of correlation searches so that they are forced to reload
        		this.clearCorrelationSearchCache();
        		
        		// Set the dialog to show that we are done
        		this.setOperationModalProgress(100, true);
        		
        		// Show a message indicating success unless we are showing the dialog
        		if( this.show_message_on_complete && success_message && this.cancel_operation === false ){
        			this.showMessage(success_message, true);
        		}
        		
        		// Render the searches list to show the updated content
    			setTimeout(function(){
    				this.render_searches_list(true);
    			}.bind(this), 100);
    			
    			return;
        	}
        	
        	// Get the next search to process
        	var search_name = this.search_processing_queue.pop();
        	
        	// Perform the operation
        	this.doOperation(operation, { 'searches' : search_name },
	        	function(result){
        			
        			if( this.show_message_on_complete && result && result.messages.length > 0 ){
        				
        				if( result.messages[0]['severity'] == 'info' ){
        					this.showMessage(result.messages[0].message, true);
        				}
        				else{
        					this.showMessage(result.messages[0].message, false);
        					this.cancel_operation = true;
        				}
        			}
        		
        			this.setOperationModalProgress(100 * (1 - (1.0 * this.search_processing_queue.length / this.initial_processing_queue_size)), false);
	        	}.bind(this),
	        		
	        	function(){
	        		if(this.search_processing_queue.length === 0 || this.cancel_operation){
	        			setTimeout(next_function_to_call.bind(this), 400);
	        		}
	        		else{
	        			setTimeout(next_function_to_call.bind(this), 400);
	        		}
	        	}.bind(this));
        },
        
        /**
         * Disable the next search to be enabled.
         */
        disableNextSearch: function(){
        	this.doOperationOnQueuedSearches('disable_searches', this.disableNextSearch.bind(this), "Searches successfully disabled");
        },
        
        /**
         * Reload the searches on the server.
         */
        reloadSearches: function(){
        	
        	var uri = Splunk.util.make_url("/splunkd/__raw/services/saved/searches/_reload");
        	 
            // Fire off the request
            jQuery.ajax({
                url:     uri,
                type:    'POST',
                async:   false
            });
        },
        
        /**
         * Perform a batch operation and schedule the next one.
         */
        doOperation: function(operation, params, success_callback, complete_callback){
        	
            var uri = Splunk.util.make_url('/custom/SA-ThreatIntelligence/correlation_searches/' + operation);
        	
            // Fire off the request
            jQuery.ajax({
                url:     uri,
                type:    'POST',
                data:    params,
                success: success_callback,
                complete: complete_callback,
                async: false
            });
        },
        
        /**
         * Enable the next search to be enabled.
         */
        enableNextSearch: function(){
        	this.doOperationOnQueuedSearches('enable_searches', this.enableNextSearch.bind(this), "Searches successfully enabled");
        },
        
        /**
         * Convert the next search to real-time
         */
        convertNextSearchToRT: function(){
        	this.doOperationOnQueuedSearches('change_searches_to_rt', this.convertNextSearchToRT.bind(this));
        },
        
        /**
         * Convert the next search to scheduled
         */
        convertNextSearchToScheduled: function(){
        	this.doOperationOnQueuedSearches('change_searches_to_non_rt', this.convertNextSearchToScheduled.bind(this));
        },
        
        /**
         * Set the progress of the modal
         */
        setOperationModalProgress: function(percentage, done){
        	
        	// If we are done, then close out the dialog
        	if(done){
        		$("#close-operation", this.$el).show();
            	$("#cancel-operation", this.$el).hide();
            	$("#progress-bar", this.$el).hide();
            	$("#operation-completion-message", this.$el).show();
            	$("#operation-description", this.$el).hide();
            	return;
        	}
        	
        	// Make sure the progress does not exceed 100% or go below 0%
        	if( percentage > 100 ){
        		percentage = 100;
        	}
        	else if(percentage < 0){
        		percentage = 0;
        	}
        	
        	// Set the progress on the bar
        	$("#progress-bar", this.$el).show();
        	$("#operation-completion-message", this.$el).hide();
        	$("#operation-description", this.$el).show();
        	$(".bar", this.$el).css("width", String(percentage) + "%");
        	
        },
        
        /**
         * Open the modal used for showing the progress of a batch operation.
         */
        openOperationModal: function(title, description, completion_message){
        	$("#search-operation-modal", this.$el).modal({
        		backdrop: 'static',
        		keyboard: false
        	});
        	
        	$("#search-operation-modal h3.text-dialog-title", this.$el).text(title);
        	$("#search-operation-modal #operation-description", this.$el).text(description);
        	$("#close-operation", this.$el).hide();
        	$("#cancel-operation", this.$el).show();
        	$("#operation-completion-message", this.$el).text(completion_message);
        },
        
        /**
         * Enable the selected searches.
         */
        enableSearches: function(){
        	var searches = [];
        	
        	$("input.correlation_search_checkbox[type='checkbox']:checked", this.$el).each(function() {
        		searches.push($(this).attr('value'));
            });
        	
        	// Stop if the user didn't select any searches
        	if(searches.length === 0){
        		$("#no-searches-selected-modal", this.$el).modal();
        		return;
        	}
        	
        	this.search_processing_queue = searches;
        	this.initial_processing_queue_size = searches.length;
        	this.cancel_operation = false;
        	this.show_message_on_complete = false;
        	
        	this.openOperationModal("Enable correlation searches", "Enabling " + String(searches.length) + " correlation searches", "Searches successfully enabled");
        	this.enableNextSearch();
        },
        
        /**
         * Disable the selected searches.
         */
        disableSearches: function(){
        	var searches = [];
        	
        	$("input.correlation_search_checkbox[type='checkbox']:checked", this.$el).each(function() {
        		searches.push($(this).attr('value'));
            });
        	
        	// Stop if the user didn't select any searches
        	if(searches.length === 0){
        		$("#no-searches-selected-modal", this.$el).modal();
        		return;
        	}
        	
        	this.search_processing_queue = searches;
        	this.initial_processing_queue_size = searches.length;
        	this.cancel_operation = false;
        	this.show_message_on_complete = false;
        	
        	this.openOperationModal("Disable correlation searches", "Disabling " + String(searches.length) + " correlation searches", "Searches successfully disabled");
        	this.disableNextSearch();
        },
        
        /**
         * Enable the clicked search.
         */
        enableSearch: function(ev){
        	var search = $(ev.target).data('search');
        	
        	this.search_processing_queue = [search];
        	this.initial_processing_queue_size = 1;
        	this.cancel_operation = false;
        	this.show_message_on_complete = true;
        	
        	//this.openOperationModal("Enable correlation search", "Enabling " + search, "Search successfully Enabled");
        	this.enableNextSearch();
        },
        
        /**
         * Disable the clicked search.
         */
        disableSearch: function(ev){
        	
        	var search = $(ev.target).data('search');
        	
        	this.search_processing_queue = [search];
        	this.initial_processing_queue_size = 1;
        	this.cancel_operation = false;
        	this.show_message_on_complete = true;
        	
        	//this.openOperationModal("Disable correlation search", "Disabling " + search, "Search successfully disabled");
        	this.disableNextSearch();
        	
        },
        
        /**
         * Convert the given search to scheduled.
         */
        convertSearchToScheduled: function(ev){
        	var search = $(ev.target).data('search');
        	
        	this.search_processing_queue = [search];
        	this.initial_processing_queue_size = 1;
        	this.cancel_operation = false;
        	this.show_message_on_complete = true;
        	
        	//this.openOperationModal("Disable correlation search", "Disabling " + search, "Search successfully disabled");
        	this.convertNextSearchToScheduled();
        },
        
        /**
         * Convert the given search to real-time.
         */
        convertSearchToRealtime: function(ev){
        	var search = $(ev.target).data('search');
        	
        	this.search_processing_queue = [search];
        	this.initial_processing_queue_size = 1;
        	this.cancel_operation = false;
        	this.show_message_on_complete = true;
        	
        	//this.openOperationModal("Disable correlation search", "Disabling " + search, "Search successfully disabled");
        	this.convertNextSearchToRT();
        },
        
        /**
         * Save the settings for the selected search.
         */
        saveAcceleration: function(){
        	
        	// Get the information 
        	var cron_schedule = $('#refresh-frequency-dropdown', this.$el).val();
        	var search = $('#key-indicator-search-name', this.$el).text();
        	var owner = $('#owner', this.$el).text();
        	var app = $('#app', this.$el).text();
        	var is_scheduled = $("#accelerate-check-box", this.$el).is(":checked");
        	
        	// Prepare the arguments
            var params = new Object();
            params.output_mode = 'json';
            params.is_scheduled = is_scheduled;
            
            // Don't bother changing the cron schedule unless we are actually scheduling the search
            if(is_scheduled){
            	params.cron_schedule = cron_schedule;
            }
            
            var uri = Splunk.util.make_url('/splunkd/__raw/servicesNS/nobody/' + app + '/saved/searches/' + search);
            uri += '?' + Splunk.util.propToQueryString(params);
            
            // Change the dialog to show that we are trying to save
            this.showSaving(true);
            
            // Fire off the request
            jQuery.ajax({
                url:     uri,
                type:    'POST',
                success: function(result) {
                	
                	
                    if(result !== undefined && result.isOk === false){
                         console.error("Search could not be updated: " + result.message);
                    }
                    else{
                    	 
                    	 // Hide the modal
                    	 $('#key-indicator-accelerate-modal', this.$el).modal('hide');
                    	 
                    	 // Refresh the results to show the changes
                    	 this.clearKeyIndicatorSearchCache();
                    	 this.refreshResults(true);
                    }
                }.bind(this),
                complete: function(jqXHR, textStatus){
                	this.showSaving(false);
                }.bind(this)
            });

        },
        
        /**
         * Check or uncheck all of the items as necessary.
         */
        checkOrUncheckAll: function(){
        	if( $("#checkall", this.$el).prop("checked") ){
        		$("input[type='checkbox']:enabled", this.$el).attr('checked', 'true').prop('checked', true);
        	}
        	else{
        		$("input[type='checkbox']", this.$el).removeAttr('checked').prop('checked', false);
        	}
        },
        
        /**
         * Set the dialog such that it is showing saving progress.
         */
        showSaving: function(saving){
        	
        	if(saving){
        		$("#save-key-indicator-acceleration", this.$el).text("Saving...");
            	$("#save-key-indicator-acceleration", this.$el).attr("disabled", "true");
            	$(".btn-dialog-cancel", this.$el).attr("disabled", "true");
            	
        	}
        	else{
        		$("#save-key-indicator-acceleration", this.$el).text("Save");
            	$("#save-key-indicator-acceleration", this.$el).removeAttr("disabled");
            	$(".btn-dialog-cancel", this.$el).removeAttr("disabled");
        	}
        	
        },
        
        /**
         * Show a message indicating that some operation succeeded or failed.
         */
        showMessage: function(message, success){
        	
        	// Get rid of any existing messages first
        	$('#failure_message', this.$el).hide();
        	$('#success_message', this.$el).hide();
        	
        	if( success ){
        		$('#success_text', this.$el).text(message);
                $('#success_message', this.$el).show();
        	}
        	else{
                $('#error_text', this.$el).text(message);
                $('#failure_message', this.$el).show();	
        	}
        },
        
        /**
         * Hide or show the accelerate frequency rate selection input.
         */
        showHideAccelerateTime: function(){
        	
        	// Show or hide the refresh frequency controls depending on if the accelerate checkbox is set
        	if($("#accelerate-check-box", this.$el).is(":checked")){
        		$("#refresh-frequency-controls", this.$el).show();
        	}
        	else{
        		$("#refresh-frequency-controls", this.$el).hide();
        	}
        },
        
        /**
         * Show the dialog for accelerating key indicators
         */
        showAccelerateKeyIndicatorDialog: function(ev){
        	
        	// Show the tooltip for the refresh frequency description
        	$('.tooltip-link', this.$el).tooltip();
        	
        	// Make sure the controls are enabled and are not indicating that a save is in progress
        	this.showSaving(false);
        	
        	// Get the information about the search
        	var search = $(ev.target).data('search');
        	var is_scheduled = $(ev.target).data('is-scheduled');
        	var cron_schedule = $(ev.target).data('cron-schedule');
        	var app = $(ev.target).data('app');
        	var owner = $(ev.target).data('owner');
        		
        	// Set the title according to the selected
        	$('#key-indicator-search-name', this.$el).text(search);
        	
        	// Set the search owner and app
        	$('#app', this.$el).text(app);
        	$('#owner', this.$el).text(owner);
        	
        	// Set the refresh frequency
        	$('#refresh-frequency-dropdown option', this.$el).each(function( index ) {
        		
        		if($(this).attr("value") == cron_schedule){
        			$(this).attr("selected", "selected");
        		}
        	
        	});
        	
        	// If no refresh frequency was selected, then set the default one
        	if( $('#refresh-frequency-dropdown option[selected]', this.$el).length === 0 ){
        		$("option[data-default-option]", this.$el).attr("selected", "selected");
        	}
        	
        	// Set the accelerated checkbox
        	if(is_scheduled === true){
        		$('#accelerate-check-box', this.$el)[0].checked=true;
        	}
        	else{
        		$('#accelerate-check-box', this.$el).removeAttr("checked");
        	}
        	
        	this.showHideAccelerateTime();
        	
        	// Open the modal
        	$('#key-indicator-accelerate-modal', this.$el).modal();
        },
        
        /**
         * Render the list of searches
         */
        render_searches_list: function(retain_datatables_state){
        	
        	// Reload the searches on the server
        	this.reloadSearches();
        	
        	// Populate retain_datatables_state if it was not provided
        	retain_datatables_state = (typeof retain_datatables_state === "undefined") ? false : retain_datatables_state;
        	
        	// Get the correlation searches
            var correlation_searches = this.fetchCorrelationSearches(
            		function(){
            			this.render_searches_list(retain_datatables_state);
            		}.bind(this) );
            
            if( correlation_searches === null ){
            	return;
            }
            
            // Get the key indicator and swimlane searches
            this.fetchKeyIndicatorAndSwimlaneSearches(
            		function(){
            			this.render_searches_list(retain_datatables_state);
            		}.bind(this) );
            
            if( this.key_indicator_searches === null || this.swimlane_searches === null ){
            	return;
            }
            
            // Determine if the user can edit correlation searches
            var can_edit_correlation_searches = this.hasCapability('edit_correlationsearches');
            
            // Get the template
            var search_list_template = $('#search-list-template', this.$el).text();
            
            // Render the table
            $("#content", this.$el).html( _.template(search_list_template,{
            	key_indicator_searches: this.key_indicator_searches,
            	swimlane_searches: this.swimlane_searches,
            	correlation_searches: correlation_searches,
            	can_edit_correlation_searches: can_edit_correlation_searches
            }) );
            
            // Make the table filterable, sortable and paginated with data-tables
            $('#table', this.$el).dataTable( {
                "iDisplayLength": 25,
                "bLengthChange": false,
                "bStateSave": true,
                "fnStateLoadParams": function (oSettings, oData) {
                	return retain_datatables_state;
                },
                "aaSorting": [[ 1, "asc" ]],
                "aoColumns": [
                              { "bSortable": false }, // Select all checkbox
                              null,                   // Name
                              null,                   // Type
                              null,                   // App
                              { "bSortable": false }, // Acceleration
                              { "bSortable": false }  // Actions
                            ]
              } );
            
        },
        
        /**
         * Render the list or a dialog if the user doesn't have permission.
         */
        render: function(retain_datatables_state){
            
        	// Populate retain_datatables_state if it was not provided
        	retain_datatables_state = (typeof retain_datatables_state === "undefined") ? false : true;
            
            // Render the content
            this.$el.html(CustomSearchesListTemplate);
            
            this.render_searches_list(retain_datatables_state);
            
            return this;
        },
        
        /**
         * Get the information about correlation searches
         */
        fetchCorrelationSearches: function(success_callback){
        	
        	if( this.correlation_searches !== null ){
        		return this.correlation_searches;
        	}
        	
        	if(typeof success_callback === "undefined"){
        		success_callback = null;
        	}
        	
            // Load all of the saved searches and look for those that are those that we are interested in
            var params = new Object();
            params.output_mode = 'json';
            params.count = '-1';
            
            var uri = Splunk.util.make_url('/custom/SA-ThreatIntelligence/correlation_searches/get_searches/');
            uri += '?' + Splunk.util.propToQueryString(params);

            var searches = null;
            
            // Determine if the call should be asynchronous
            var async = true;
            
            if(success_callback === null){
            	async = false;
            }
            
            jQuery.ajax({
                url:     uri,
                type:    'GET',
                success: function(result) {
                     if(result !== undefined && result.isOk === false){
                         console.error("Could not obtain the list of searches: " + result.message);
                     }
                     else if(result !== undefined){
                    	 this.correlation_searches = result;
                    	 
                    	 if(success_callback !== null){
                    		 success_callback();
                    	 }
                     }
                }.bind(this),
                async:   async
            });
            
            return this.correlation_searches;
            
        },
        
        /**
         * Clear the cache of correlation searches so that they will be reloaded when they are fetched.
         */
        clearCorrelationSearchCache: function(){
        	this.correlation_searches = null;
        },
        
        /**
         * Clear the cache of key indicators searches so that they will be reloaded when they are fetched.
         */
        clearKeyIndicatorSearchCache: function(){
        	this.key_indicator_searches = null;
        },
        
        /**
         * Get the list of key indicators and swimlanes from the server.
         */
        fetchKeyIndicatorAndSwimlaneSearches: function(success_callback){
        	
        	// Stop if we already got the searches
        	if( this.key_indicator_searches !== null ){
        		return;
        	}
        	
        	if(typeof success_callback === "undefined"){
        		success_callback = null;
        	}
        	
            // Load all of the saved searches and look for those that are those that we are interested in
            var params = new Object();
            params.output_mode = 'json';
            params.count = '-1';
            params.search = 'action.keyindicator=1 OR action.swimlane=1';
            
            var uri = Splunk.util.make_url('/splunkd/__raw/services/saved/searches/');
            uri += '?' + Splunk.util.propToQueryString(params);

            var searches = null;
            
            // Determine if the call should be asynchronous
            var async = true;
            
            if(success_callback === null){
            	async = false;
            }
            
            jQuery.ajax({
                url:     uri,
                type:    'GET',
                success: function(result) {
                     if(result !== undefined && result.isOk === false){
                         console.error("Could not obtain the list of searches: " + result.message);
                     }
                     else if(result !== undefined){
                    	 
                    	 this.key_indicator_searches = [];
                    	 this.swimlane_searches = [];
                    	 
                    	 for( var i = 0; i < result.entry.length; i++){
                    		 
                    		 // Figure out which type of search it is and store it accordingly
                    		 if( result.entry[i].content['action.keyindicator'] == '1' ){
                    			 this.key_indicator_searches.push(result.entry[i]);
                    		 }
                    		 else if( result.entry[i].content['action.swimlane'] == '1' ){
                    			 this.swimlane_searches.push(result.entry[i]);
                    		 }
                    	 }
                    	 
                    	 if(success_callback !== null){
                    		 success_callback();
                    	 }
                    	 
                     }
                }.bind(this),
                async:   async
            });
            
        },
        
        /**
         * Refresh the list of searches and re-render the display.
         */
        refreshResults: function(retain_datatables_state){
            
        	// Populate retain_datatables_state if it was not provided
        	retain_datatables_state = (typeof retain_datatables_state === "undefined") ? false : true;
        	
            this.render_searches_list(retain_datatables_state);
        }
    });
    
    return CustomSearchListView;
});
