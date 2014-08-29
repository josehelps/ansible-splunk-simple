require.config({
    paths: {
        key_indicator_view: '../app/SA-Utils/js/views/KeyIndicatorView',
        text: "../app/SA-Utils/js/lib/text",
        console: '../app/SA-Utils/js/util/Console'
    }
});

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "text!../app/SA-Utils/js/templates/KeyIndicatorEditor.html",
    "key_indicator_view",
    "css!../app/SA-Utils/css/KeyIndicatorEditor.css",
    "console"
], function(_, Backbone, mvc, $, SimpleSplunkView, KeyIndicatorEditorTemplate, KeyIndicatorView){
	
    // Define the custom view class
    var KeyIndicatorEditorView = SimpleSplunkView.extend({
    	
        className: "KeyIndicatorEditorView",

        /**
         * Setup the defaults
         */
        defaults: {
        	list_link: null,
        	list_link_title: "Back to list",
        	default_app: "SA-Utils",
        	search_name: null,
        	redirect_to_list_on_save: true
        },
        
        initialize: function() {
            this.apps = null;
            
            // Apply the defaults
            this.options = _.extend({}, this.defaults, this.options);
            
            options = this.options || {};
            
            this.default_app = options.default_app;
            this.list_link = options.list_link;
            this.list_link_title = options.list_link_title;
            this.redirect_to_list_on_save = options.redirect_to_list_on_save;
            this.search_name = options.search_name;
            this.capabilities = null;
        },
        
        events: {
        	"click #save-key-indicator": "saveKeyIndicator",
        	"change #schedule" : "showHideCronSchedule",
        	"click #preview-key-indicator" : "showPreview",
        	"change input" : "validate",
        	"change select" : "validate",
        	"change textarea" : "validate"
        },
        
        /**
         * Hide or show the cron schedule selection input.
         */
        showHideCronSchedule: function(){
        	
        	// Show or hide the refresh frequency controls depending on if the schedule checkbox is set
        	if($("input[name=schedule]", this.$el).is(":checked")){
        		$("#cron-schedule-control-group", this.$el).show();
        	}
        	else{
        		$("#cron-schedule-control-group", this.$el).hide();
        	}
        },
        
        /**
         * Parse the integer if it is valid. Otherwise, return NaN.
         */
        parseIntIfValid: function(val){
        	
        	var intRegex = /^[-]?\d+$/;
        	
        	if( !intRegex.test(val) ){
        		return NaN;
        	}
        	else{
        		return parseInt(val, 10);
        	}
        },
        
        /**
         * Determine if the human readable number is valid
         */
        isHumanReadableNumberValid: function( num ){
        	return (KeyIndicatorView.prototype.getActualNumberFromHumanReadable(num) !== null);
        	
        },
        
        /**
         * Save the settings for the selected search.
         */
        saveKeyIndicator: function(){
        	
        	// Make sure that the options appear to be valid
        	if( !this.validate() ){
        		// Could not validate options
        		return;
        	}
        	
        	// Determine if we are making a new entry or editing a existing one
        	var is_new = $('input[name=is_new]', this.$el).val() === 'true';
        	
        	// Prepare the arguments
            var params = new Object();
            params.output_mode = 'json';
            
            // Specify the saved search information
            params.cron_schedule = $('input[name=cron-schedule]', this.$el).val();
            params.search = $('textarea[name=search]', this.$el).val();
            params.is_scheduled = $("input[name=schedule]", this.$el).is(":checked");
            
            if( is_new ){
            	params.name = $('input[name=search-name]', this.$el).val();
            }
            
            // Specify the key indicator alert action
            params['action.keyindicator'] = 1;
            params['actions'] = 'keyindicator';
            params['action.keyindicator.title'] = $('input[name=title]', this.$el).val();
            params['action.keyindicator.subtitle'] = $('input[name=sub-title]', this.$el).val();
            params['action.keyindicator.value'] = $('input[name=value-field]', this.$el).val();
            params['action.keyindicator.threshold'] = $('input[name=threshold]', this.$el).val();
            params['action.keyindicator.delta'] = $('input[name=delta-field]', this.$el).val();
            params['action.keyindicator.value_suffix'] = $('input[name=value-suffix]', this.$el).val();
            params['action.keyindicator.invert'] = $('input[name=invert]', this.$el).is(":checked");
            params['action.keyindicator.drilldown_uri'] = $('input[name=drilldown-uri]', this.$el).val();
            
            // If the drilldown_uri is blank, then the user wants to return to the default behavior of showing the underlying search results. Set
            // this to a single space so that the REST API lets it through (a blank does nothing by default).
            if( params['action.keyindicator.drilldown_uri'] === '' ){
            	params['action.keyindicator.drilldown_uri'] = ' ';
            }
            
        	// Get the parameters that we need to build the URL, including...
            //   ... the search name ...
        	var search_name = $('input[name=search-name]', this.$el).val();
        	
        	//   ... and the app ...
        	var app = $('select[name=app]', this.$el).val();
        	
        	if( !is_new ){
        		app = $('input[name=app]', this.$el).val();
        	}
        	
        	if( app === "" ){
        		app = this.default_app;
        	}
        	
            //   ... and the owner ...
        	var owner = 'nobody';
        	
        	if( !is_new ){
        		owner = $('input[name=owner]', this.$el).val();
        	}
        	
        	// Get the entity
        	var entity = search_name;
        	
        	if( is_new ){
        		entity = "";
        	}
        	
        	// Make the URL
            var uri = Splunk.util.make_url('/splunkd/__raw/servicesNS', 'nobody', app, 'saved/searches', entity);
            
            // Change the dialog to show that we are trying to save
            this.showSaving(true);
            
            // Fire off the request
            jQuery.ajax({
                url:     uri,
                type:    'POST',
                data: params,
                success: function(result) {
                	
                    if(result !== undefined && result.isOk === false){
                         $('#error_text', this.$el).text("Search could not be updated: " + result.message);
                         $('#failure_message', this.$el).show();
                    }
                    else{
                    	 
                    	// Save the search name so that we can now edit it if necessary
                    	if( is_new ){
	                    	this.search_name = search_name;
	                    	this.render();
                    	}
                    	
                    	// Indicate that the search was saved
                    	$('#success_message', this.$el).show();
                    	
                    	// Redirect the user to the list page after a few seconds
                    	if(this.redirect_to_list_on_save && this.list_link){
                    		setTimeout( function() { this.redirectToList(); }.bind(this), 3000 );
                    	}
                    }
                }.bind(this),
                error: function(result) {
                	
                	if(result.responseJSON.messages.length > 0){
                		$('#error_text', this.$el).text(result.responseJSON.messages[0].text);
                	}
                	else{
                		$('#error_text', this.$el).text("Search could not be updated");
                	}
                	
                    $('#failure_message', this.$el).show();
                },
                complete: function(jqXHR, textStatus){
                	this.showSaving(false);
                }.bind(this)
            });

        },
        
        /**
         * Return the default if the first argument is null, empty or undefined
         */
        valueOrDefault: function( value, default_value){
        	
        	if( typeof value === undefined || value === undefined || value === null || value === '' ){
        		return default_value;
        	}
        	else{
        		return value;
        	}
        },
        
        /**
         * Open the preview dialog.
         */
        showPreview: function(){
        	
        	// Make the key indicator instance
        	var keyIndicatorView = new KeyIndicatorView({
    			title: 			$('input[name=title]', this.$el).val(),
    			subtitle :      $('input[name=sub-title]', this.$el).val(),
    			drilldown_uri:  null,
    			value:          this.valueOrDefault($('input[name=value-field]', this.$el).val(), 'current_count'),
    			delta:          this.valueOrDefault($('input[name=delta-field]', this.$el).val(), 'delta'),
    			threshold:      $('input[name=threshold]', this.$el).val(),
    			search_string:  $('textarea[name=search]', this.$el).val(),
    			invert:         $('input[name=invert]', this.$el).is(":checked"),
    			value_suffix:   $('input[name=value-suffix]', this.$el).val(),
    			
    	        el: $('#key-indicator-preview-panel', this.$el)
    	    });
        	
        	// Don't try to execute the key-indicator in preview if the settings are invalid
        	if( !this.validate() ){
        		
	        	// Show a dialog indicating that we cannot show preview
	        	$('#keyIndicatorsPreviewInvalidModal').modal();
        	}
        	else{
            	// Render the pending dialog
            	keyIndicatorView.render();
            	
            	// Open the dialog
            	$('#keyIndicatorsPreviewModal').modal();
            	
            	// Start the search and then the rendering
            	keyIndicatorView.startGettingResults();
            	keyIndicatorView.renderToCompletion();
        	}
        	

        },
        
        /**
         * Set the dialog such that it is showing saving progress.
         */
        showSaving: function(saving){
        	
        	if(saving){
        		$("#save-key-indicator", this.$el).text("Saving...");
            	$("#save-key-indicator", this.$el).attr("disabled", "true");
            	//$(".btn-dialog-cancel", this.$el).attr("disabled", "true");
            	
        	}
        	else{
        		$("#save-key-indicator", this.$el).text("Save");
            	$("#save-key-indicator", this.$el).removeAttr("disabled");
            	//$(".btn-dialog-cancel", this.$el).removeAttr("disabled");
        	}
        	
        },
        
        /**
         * Get apps.
         */
        fetchApps: function(){
        	
        	var apps = null;
        	
        	// Prepare the arguments
            var params = new Object();
            params.output_mode = 'json';
            
            var uri = Splunk.util.make_url('/splunkd/__raw/services/apps/local');
            uri += '?' + Splunk.util.propToQueryString(params);
            
            // Fire off the request
            jQuery.ajax({
                url:     uri,
                type:    'GET',
                success: function(result) {
                	
                    if(result !== undefined && result.isOk === false){
                         console.error("Apps list could not be obtained: " + result.message);
                    }
                    else{
                    	apps = result.entry;
                    }
                }.bind(this),
                async: false
            });
            
            return apps;
        },
        
        /**
         * Get the given key indicator search.
         */
        fetchSearch: function(name){
        	
        	var search = null;
        	
        	// Prepare the arguments
            var params = new Object();
            params.output_mode = 'json';
            
            var uri = Splunk.util.make_url('/splunkd/__raw/services/saved/searches/' + name);
            uri += '?' + Splunk.util.propToQueryString(params);
            
            // Fire off the request
            jQuery.ajax({
                url:     uri,
                type:    'GET',
                success: function(result) {
                	
                    if(result !== undefined && result.isOk === false){
                    	console.error("Search could not be obtained: " + result.message);
                    }
                    else{
                    	search = result.entry[0];
                    }
                }.bind(this),
                async: false
            });
            
            return search;
        },
        
        /**
         * Redirect the user to the list view.
         */
        redirectToList: function(){
        	if( this.list_link ){
        		document.location = this.list_link;
        	}
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
         * Get the fields out of a search and convert to an array.
         */
        getNamedArrayFromSearch: function(search){
        	var a = {
        			search_name: search.name,
        			app: search.acl['app'],
        			owner: search.acl['owner'],
        			title: search.content['action.keyindicator.title'],
        			sub_title: search.content['action.keyindicator.subtitle'],
        			drilldown_uri: search.content['action.keyindicator.drilldown_uri'],
        			cron_schedule: search.content['cron_schedule'],
        			value_field: search.content['action.keyindicator.value'],
        			delta_field: search.content['action.keyindicator.delta'],
        			threshold: search.content['action.keyindicator.threshold'],
        			value_suffix: search.content['action.keyindicator.value_suffix'],
        			invert: Splunk.util.normalizeBoolean(search.content['action.keyindicator.invert']),
        			search: search.content['search'],
        			is_scheduled: search.content['is_scheduled']
        	};
        	
        	return a;
        },
        
        /**
         * Get the given URL parameter.
         */
        getURLParameter: function(param){
        	var pageURL = window.location.search.substring(1);
            var sURLVariables = pageURL.split('&');
            for (var i = 0; i < sURLVariables.length; i++)
            {
                var parameterName = sURLVariables[i].split('=');
                if (parameterName[0] == param) 
                {
                    return parameterName[1];
                }
            }
            
            return null;
        },
        
        /**
         * Validate the given field and update the UI to show that the validation failed if necessary.
         */
        validateField: function(field_selector, val, message, test_function){
            if( !test_function(val) ){
                $(".help-inline", field_selector).show().text(message);
                $(field_selector).addClass('error');
                return 1;
            }
            else{
                $(".help-inline", field_selector).hide();
                $(field_selector).removeClass('error');
                return 0;
            }
        },
        
        /**
         * Determine if the search parses
         */
        doesSearchParse: function(){
        	return false;
        },
        
        /**
         * Validate the provided options.
         */
        validate: function(){
        	
        	// Determine if we are making a new entry or editing a existing one
        	var is_new = $('input[name=is_new]', this.$el).val() === 'true';
        	
            // Record the number of failures
            var failures = 0;
            
            // Verify search_name
            if( is_new ){
                failures += this.validateField( $('#search-name-control-group', this.$el), $('input[name=search-name]', this.$el).val(), "Cannot be empty",
                        function(val){
                            return val.length !== 0;
                        }
                );
            }
            
            // Verify app
            if( is_new ){
                failures += this.validateField( $('#app-control-group', this.$el), $('select[name=app]', this.$el).val(), "Cannot be empty",
                        function(val){
                            return val.length !== 0;
                        }
                );
            }
            
            // Verify title
            failures += this.validateField( $('#title-control-group', this.$el), $('input[name=title]', this.$el).val(), "Cannot be empty",
                    function(val){
                        return val.length !== 0;
                    }
            );
            
            // Verify Search
            failures += this.validateField( $('#search-control-group', this.$el), $('textarea[name=search]', this.$el).val(), "Cannot be empty",
                    function(val){
                        return val.length !== 0;
                    }
            );
            
        	// Verify cron-schedule
            if( $('input[name=schedule]', this.$el).is(":checked") ){
	            failures += this.validateField( $('#cron-schedule-control-group', this.$el), $('input[name=cron-schedule]', this.$el).val(), "Cannot be empty",
	                    function(val){
	                        return val.length !== 0;
	                    }
	            );
            }
            
            // Verify threshold
            verify_threshold = function(val){ 
                return val.length === 0 || this.isHumanReadableNumberValid(val);
            }.bind(this);
            
            failures += this.validateField( $('#threshold-control-group', this.$el), $('input[name=threshold]', this.$el).val(), "Value is invalid", verify_threshold );
            
            // Verify value field
            failures += this.validateField( $('#value-field-control-group', this.$el), $('input[name=value-field]', this.$el).val(), "Cannot be empty",
                    function(val){
                        return val.length !== 0 && (/[-_A-Z0-9]+/i).test(val);
                    }
            );
            
            // Verify drilldown URI field
            failures += this.validateField( $('#drilldown-uri-control-group', this.$el), $('input[name=drilldown-uri]', this.$el).val(), "Must be a valid path",
                    function(val){
                        return val.length === 0 || (/^[a-z0-9_]+([?].*)?$/i).test(val);
                    }
            );
            
            // Return a boolean indicating the validation succeeded or not
            return failures === 0;
            
        },
        
        /**
         * Render the editor.
         */
        render: function(){
        	
        	// This indicates if the editor is making a new search or editing an existing one
        	var is_new = true;
        	
        	// Get the name in case we are editing an existing search
        	var search_name = null;
        	
        	if( this.search_name !== null ){
        		search_name = this.search_name;
        	}
        	else{
        		search_name = this.getURLParameter("search");
        	}
        	
        	var search = null;
        	var content = null;
        	
        	// Load the content from the search
        	if( search_name !== null ){
        		search = this.fetchSearch(search_name);
        		content = this.getNamedArrayFromSearch(search);
        		is_new = false;
        	}
        	else{
        		// Use the default content otherwise
        		content = {
            			search_name: '',
            			app: this.default_app,
            			title: '',
            			sub_title: '',
            			drilldown_uri: '',
            			cron_schedule: '',
            			value_field: '',
            			delta_field: '',
            			threshold: '',
            			search: '',
            			invert: false,
            			value_suffix: '',
            			owner: 'nobody',
            			is_scheduled: false
            	};
        		
        		is_new = true;
        	}
        	
        	// Add the param indicating if this is a new search
        	content.is_new = is_new;
        	
        	// Add some other parameters
        	content.list_link = this.list_link;
        	content.list_link_title = this.list_link_title;
        	
        	// Get the list of apps
        	var apps = this.fetchApps();
        	content.apps = apps;
        	
        	// See if the user can edit
        	content.can_edit = this.hasCapability("schedule_search"); //SOLNESS-4861
        	
        	// If the drilldown URI is just whitespace, then treat as nothing.
        	// A single blank is used to clear out an existing drilldown in order to indicate that a user wants to return
        	// to the default mode of showing the underyling search results as opposed to pointing to a view.
        	if( content.drilldown_uri.replace(/^\s+|\s+$/g, '').length === 0 ){
        		content.drilldown_uri = '';
        	}
        	
        	// Render the view
        	this.$el.html(_.template(KeyIndicatorEditorTemplate, content));
        	
        	this.showHideCronSchedule();
        	
            return this;
        }
    });
    
    return KeyIndicatorEditorView;
});
