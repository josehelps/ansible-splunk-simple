require.config({
    paths: {
        text: "../app/SA-Utils/js/lib/text",
        console: '../app/SA-Utils/js/util/Console',
        tagmanager: '../app/SA-ThreatIntelligence/contrib/tagmanager/tagmanager',
        guided_search_editor_view: '../app/SA-ThreatIntelligence/js/views/GuidedSearchEditorView'
    },
    shim: {
        'tagmanager': {
            deps: ['jquery']
        }
    }
});

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "splunkjs/mvc/utils",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "splunkjs/mvc/simpleform/input/dropdown",
    'splunkjs/mvc/searchmanager',
    "text!../app/SA-ThreatIntelligence/js/templates/CorrelationSearchEditor.html",
    "guided_search_editor_view",
    "tagmanager",
    "css!../app/SA-ThreatIntelligence/contrib/tagmanager/tagmanager.css",
    "css!../app/SA-ThreatIntelligence/css/CorrelationSearchEditor.css",
    "console"
], function(_, Backbone, mvc, utils, $, SimpleSplunkView, DropdownInput, SearchManager, CorrelationSearchEditorTemplate, GuidedSearchEditorView){
	
    // Define the custom view class
    var CorrelationSearchEditorView = SimpleSplunkView.extend({
    	
        className: "CorrelationSearchEditorView",

        /**
         * Setup the defaults
         */
        defaults: {
        	list_link: null,
        	list_link_title: "Back to list",
        	search_name: null,
        	redirect_to_list_on_save: true
        },
        
        initialize: function() {
            this.apps = null;
            
            // Apply the defaults
            this.options = _.extend({}, this.defaults, this.options);
            
            options = this.options || {};
            
            this.list_link = options.list_link;
            this.list_link_title = options.list_link_title;
            this.redirect_to_list_on_save = options.redirect_to_list_on_save;
            
            // Indicates the search that was loaded
            this.search_name = null;
            
            // A cache of the user's capabilities
            this.capabilities = null;

            // The search that was fetched
            this.fetched_search = null;
            
            // The following contains cached information that is helpful when making correlation searches
            this.correlation_search_meta_info = null;
            this.notable_info = null;
            
            // A reference to the dialog that walks the user through the process of making the search
            this.guided_mode_dialog = null;
            
            // The information about the search itself. This information is necessary for us to determine if the raw search is based upon the search spec.
            this.search_string = null;
            this.search_spec = null;
            this.using_search_spec = false;
            
            // Listen to the event indicating that the guided mode successfully updated the search
            this.listenTo(Backbone, "guided-mode-search-updated-event", function(search_string, search_spec, start_time, end_time) {
            		this.updateSearchInformation(search_string, search_spec, start_time, end_time, true);
            }.bind(this));
            
            // The following is used to disable links when something is happening that should block users from changing the page ro doing some actions.
            var disable_links = false;
            
        },
        
        events: {
        	"click #save": "save",
        	"click #cancel": "redirectToList",
        	"change input[name='start_time']" : "toggleCronSchedule",
        	"change input[name='end_time']" : "toggleCronSchedule",
        	"change select[name='domain']" : "selectAppContext",
        	"change input" : "validate",
        	"change select" : "validate",
        	"change textarea" : "validate",
        	"click input[name='email_isenabled']": "toggleEmailAction",
        	"click input[name='script_isenabled']": "toggleScriptAction",
        	"click input[name='risk_isenabled']": "toggleRiskAction",
        	"click input[name='notable_isenabled']": "toggleNotableAction",
        	"click #show-guided-search-editor": "openGuidedSearchEditor",
        	"click #change-to-manual-mode": "changeToManualMode",
        	"click #email_settings_link": "openEmailSettingsLink",
        	"click #edit-email-action" : "editEmailAction"
        },
        
        /**
         * Update the state of the search string such that notify the user
         */
        updateSearchInformation: function(search_string, search_spec, start_time, end_time, using_search_spec){
        	
        	this.search_string = search_string;
        	this.search_spec = search_spec;
        	this.using_search_spec = using_search_spec;
        	
        	// Update the form data
        	$("textarea[name='search']", this.$el).val(search_string);
        	
        	if( start_time !== undefined ){
        		$("input[name='start_time']", this.$el).val(start_time);
        	}
        	
        	if( end_time !== undefined ){
        		$("input[name='end_time']", this.$el).val(end_time);
        	}
        	
        	this.validate();
        	
        	// Change the state of the search string such that we recognize if the search spec is in force
        	if( using_search_spec ){
        		$("#change-to-manual-mode", this.$el).show();
        	}
        	else{
        		$("#change-to-manual-mode", this.$el).hide();
        	}
        	
        	$("textarea[name='search']", this.$el).val(search_string).prop('disabled', using_search_spec);
        },
        
        /**
         * Switch from using the search spec back to manually created search.
         */
        changeToManualMode: function(){
        	
        	// Stop if we shouldn't be allowing things to happen now
        	if( this.disable_links ){
        		return false;
        	}
        	
        	this.updateSearchInformation(this.search_string, this.search_spec, undefined, undefined, false);
        },
        
        /**
         * Get the list of group-bys fields.
         */
        getGroupBys: function(){
        	
    		var group_bys = $('input[name=hidden-group_by]', this.$el).val();
    		
    		if( group_bys ){
    			group_bys = group_bys.split(",");
    		}
    		else if(group_bys === ""){
    			group_bys = null;
    		}
    		
    		// If a duration is defined, then assume the default 'const_dedup_id' group-by
    		if(group_bys === null && $('input[name=duration]', this.$el).val().length > 0){
    			group_bys = ['const_dedup_id'];
    		}
    		
    		return group_bys;
        },
        
        /**
         * Open the email action edit page.
         */
        editEmailAction: function(){
        	
        	var path = "/servicesNS/nobody/" + this.fetched_search.acl.app + "/saved/searches/" + this.fetched_search.name;
        	
        	//The following is the link used by the Core search editor. This doesn't work because Splunk doesn't correctly figure out what to do
        	//when the app doesn't support UI access.
        	//var redirect = Splunk.util.make_url("/savedsearchredirect?s=" + encodeURIComponent(path) );
        	var redirect = Splunk.util.make_url("/app/" + utils.getCurrentApp() + "/alert?dialog=actions&s=" + encodeURIComponent(path) );
        	redirect = redirect.replace(/[%]20/g, "%2520");
        	window.open(redirect);
        },
        
        /**
         * Open the editor for guided mode
         */
        openGuidedSearchEditor: function(){
        	
        	// Stop if we shouldn't be allowing things to happen now
        	if( this.disable_links ){
        		return false;
        	}
        	
            // Make the guided mode dialog
        	if( this.guided_mode_dialog === null ){
	        	this.guided_mode_dialog = new GuidedSearchEditorView({
	        		el: $("#guided-mode-dialog-placeholder", this.$el)
	        	});
	        	
	        	// Render the guided mode dialog
	        	this.guided_mode_dialog.render();
        	}
        	
        	// Load the current search spec
        	if( this.search_spec !== null && this.search_spec !== "" ){
        		
        		var group_bys = this.getGroupBys();
        		
        		this.guided_mode_dialog.loadSearchSpec(this.search_spec, $("input[name='start_time']", this.$el).val(), $("input[name='end_time']", this.$el).val(), group_bys);
        	}
        	
        	// Open the modal
        	this.guided_mode_dialog.show();
        	
        	// Return false so that the click handler doesn't try to open the URL
        	return false;
        },
        
        /**
         * Determines if this search would run in real-time
         */
        isRealtime: function(){
        	 return this.isTimeRT( $("input[name='start_time']", this.$el).val() ) || this.isTimeRT( $("input[name='end_time']", this.$el).val() );
        },
        
        /**
         * Toggle cron schedule selection input based on whether the search is real-time or not.
         */
        toggleCronSchedule: function(){
        	if( this.isRealtime() ){
        		$("input[name='cron_schedule']", this.$el).val("*/5 * * * *");
        		$("input[name='cron_schedule']", this.$el).prop('disabled', true);
        	}
        	else{
        		$("input[name='cron_schedule']", this.$el).prop('disabled', false);
        	}
        },
        
        /**
         * Toggle the email related inputs.
         */
        toggleEmailAction: function(){
        	if( $("input[name=email_isenabled]", this.$el).prop("checked") ){
        		$("#email-subject-control-group", this.$el).show();
        		$("#email-to-control-group", this.$el).show();
        		$("#email-send-results-control-group", this.$el).show();
        	}
        	else{
        		$("#email-subject-control-group", this.$el).hide();
        		$("#email-to-control-group", this.$el).hide();
        		$("#email-send-results-control-group", this.$el).hide();
        	}
        },
        
        /**
         * Toggle the script related inputs.
         */
        toggleScriptAction: function(){
        	if( $("input[name=script_isenabled]", this.$el).prop("checked") ){
        		$("#script-filename-control-group", this.$el).show();
        	}
        	else{
        		$("#script-filename-control-group", this.$el).hide();
        	}
        },
        
        /**
         * Toggle the risk related inputs.
         */
        toggleRiskAction: function(){
        	this.toggleSelectors( $("input[name=risk_isenabled]", this.$el).prop("checked"), [
        	                                                                                  "#risk-score-control-group",
        	                                                                                  "#risk-object-control-group",
        	                                                                                  "#risk-object-type-control-group"]);
        },
        
        /**
         * Toggle the notable event related inputs.
         */
        toggleNotableAction: function(){
        	this.toggleSelectors( $("input[name=notable_isenabled]", this.$el).prop("checked"), [
        	                                                                                     "#rule-title-control-group",
        	                                                                                     "#rule-description-control-group",
        	                                                                                     "#domain-control-group",
        	                                                                                     "#severity-control-group",
        	                                                                                     "#default-owner-control-group",
        	                                                                                     "#default-status-control-group",
        	                                                                                     "#drill-down-name-control-group",
        	                                                                                     "#drill-down-search-control-group"]);
        },
        
        /**
         * Toggle the given selectors based on the first argument.
         */
        toggleSelectors: function(show, selectors_to_show_or_hide){
        	
        	for( var i = 0; i < selectors_to_show_or_hide.length; i++){
        		if(show){
        			$(selectors_to_show_or_hide[i], this.$el).show();
        		}
        		else{
        			$(selectors_to_show_or_hide[i], this.$el).hide();
        		}
        	}
        	
        },
        
        /**
         * Select the app content associated with the security domain.
         */
        selectAppContext: function(){
        	
        	var domain_namespace_map = {
        			'Access' : 'SA-AccessProtection',
        			'Audit' : 'SA-AuditAndDataProtection',
        			'Endpoint' : 'SA-EndpointProtection',
        			'Identity' : 'SA-IdentityManagement',
        			'Network' : 'SA-NetworkProtection',
        			'Threat' : 'SA-ThreatIntelligence'
        	};
        	
        	
        	var ns = domain_namespace_map[$("select[name='domain']", this.$el).val()];
        	
        	$("option[value='" + ns + "']", this.$el).prop('selected', true);
        	
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
         * Refresh the search string from the search spec if the search spec is being used.
         */
        refreshSearchString: function(){
        	
            // Make the guided mode dialog
        	if( this.guided_mode_dialog === null ){
	        	this.guided_mode_dialog = new GuidedSearchEditorView({
	        		el: $("#guided-mode-dialog-placeholder", this.$el)
	        	});
        	}
        	
        	// Update the search
        	var search_string = this.guided_mode_dialog.getSearchString(this.search_spec, $("input[name='start_time']", this.$el).val(), $("input[name='end_time']", this.$el).val(), this.getGroupBys());
        	 
        	$('textarea[name=search]', this.$el).val(search_string);
        },
        
        /**
         * Save the settings for the given search.
         */
        save: function(){
        	
        	// Make sure that the options appear to be valid
        	if( !this.validate() ){
        		// Could not validate options
        		return;
        	}
        	
        	// Determine if we are making a new entry or editing a existing one
        	var is_new = this.search_name === null;
        	
        	// Prepare the arguments
            var params = new Object();
            params.output_mode = 'json';
            
            // Specify the saved search information
            params.cron_schedule = $('input[name=cron-schedule]', this.$el).val();
            
            params.search = $('textarea[name=search]', this.$el).val();
            
            if(this.using_search_spec){
                params.search_spec = JSON.stringify(this.search_spec);
            }
            else{
            	params.search_spec = "{}";
            }
            
            if( is_new ){
            	params.namespace = $('select[name=namespace]', this.$el).val();
            	params.domain = $('select[name=domain]', this.$el).val();
            	params.name = $('input[name=name]', this.$el).val();
            }
            else{
            	params.sid = this.fetched_search.name;
            	params.domain = this.fetched_search.content['security_domain'];
            	params.name = this.fetched_search.content['rule_name'];
            }
            
            params.default_status = $('select[name=default_status]', this.$el).val();
            params.default_owner = $('select[name=default_owner]', this.$el).val();
            
            params.start_time = $('input[name=start_time]', this.$el).val();
            params.end_time = $('input[name=end_time]', this.$el).val();
            params.description = $('input[name=description]', this.$el).val();
            params.cron_schedule = $('input[name=cron_schedule]', this.$el).val();
            params.severity = $('select[name=severity]', this.$el).val();
            
            params.drilldown_search = $('input[name=drilldown_search]', this.$el).val();
            params.drilldown_name = $('input[name=drilldown_name]', this.$el).val();
            
            params.summary_index_action_enabled = $("input[name=notable_isenabled]", this.$el).prop("checked");
            
            params.duration = $('input[name=duration]', this.$el).val();
            params.group_by = $('input[name=hidden-group_by]', this.$el).val();
            
            // Actions:
            params.rule_title = $('input[name=rule_title]', this.$el).val();
            params.rule_description = $('input[name=rule_description]', this.$el).val();
            
            params.email_isenabled = $("input[name=email_isenabled]", this.$el).prop("checked");
            params.email_to = $("input[name=hidden-email_to]", this.$el).val();
            params.email_subject = $("input[name=email_subject]", this.$el).val();
            params.email_format = $("select[name=email_format]", this.$el).val();
            params.email_sendresults = $("input[name=email_sendresults]", this.$el).prop("checked");
            
            params.rss_isenabled = $("input[name=rss_isenabled]", this.$el).prop("checked");
            
            params.script_isenabled = $("input[name=script_isenabled]", this.$el).prop("checked");
            params.script_filename = $("input[name=script_filename]", this.$el).val();
            
            // Risk:
            params.risk_action_enabled = $("input[name=risk_isenabled]", this.$el).prop("checked");
            params.risk_score = $("input[name=risk_score]", this.$el).val();
            params.risk_object = $("input[name=risk_object]", this.$el).val();
            params.risk_object_type = mvc.Components.get("risk_object_type").val();
            
        	// Make the URL
            var uri = Splunk.util.make_url('/custom/SA-ThreatIntelligence/correlation_searches/update_or_create_search');
            
            // Change the dialog to show that we are trying to save
            this.showSaving(true);
            
            // Block some operations while the process continues because we don't want people to start editing the page and then have the page forward them elsewhere
            if(this.redirect_to_list_on_save && this.list_link){
            	this.disable_links = true;
            }
            
            // Save the search_name so that we can remember which search this is after editing is complete
            if( is_new ){
            	search_name = params.name;
        	}
            
            // Fire off the request
            jQuery.ajax({
                url:     uri,
                type:    'POST',
                data: params,
                success: function(result) {
                	
                    if(result !== undefined && (result.isOk === false || result['success'] === false )){
                         $('#error_text', this.$el).text("Search could not be updated: " + result.message);
                         $('#failure_message', this.$el).show();
                    }
                    else{
                    	 
                    	// Save the search name so that we can now edit it if necessary
                    	if( is_new ){
	                    	this.search_name = result.sid;
	                    	
	                    	// Set the search name input to disabled
	                    	$('input[name="name"]', this.$el).prop('disabled', true);
                    	}
                    	
                    	// Indicate that the search was saved
                    	$('#success_message', this.$el).show();
                    	
                    	// Redirect the user to the list page after a few seconds
                    	if(this.redirect_to_list_on_save && this.list_link){
                    		setTimeout( function() { this.redirectToList(); }.bind(this), 3000 );
                    	}
                    	else{
                    		// Allow various operations again since we are done
                            this.disable_links = false;
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
                    
                    // Allow the links to work
                    this.disable_links = false;
                },
                complete: function(jqXHR, textStatus){
                	this.showSaving(false);
                }.bind(this)
            });

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
         * Set the dialog such that it is showing saving progress.
         */
        showSaving: function(saving){
        	
        	if(saving){
        		$("#save", this.$el).text("Saving...");
            	$("#save", this.$el).attr("disabled", "true");
            	//$(".btn-dialog-cancel", this.$el).attr("disabled", "true");
            	
        	}
        	else{
        		$("#save", this.$el).text("Save");
            	$("#save", this.$el).removeAttr("disabled");
            	//$(".btn-dialog-cancel", this.$el).removeAttr("disabled");
        	}
        	
        },
        
        /**
         * Get the given correlation search.
         */
        fetchSearch: function(name){
        	
        	var search = null;
        	
        	// Prepare the arguments
            var params = new Object();
            params.output_mode = 'json';
            params.search = name;
            
            var uri = Splunk.util.make_url('/custom/SA-ThreatIntelligence/correlation_searches/get_search');
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
            
            // Store the last fetched search
            this.fetched_search = search;
            
            // Return the search
            return search;
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
                    return decodeURIComponent(parameterName[1]);
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
         * Validate the provided options.
         */
        validate: function(){
        	
        	// Determine if we are making a new entry or editing a existing one
        	var is_new = this.search_name === null;
        	
            // Record the number of failures
            var failures = 0;
            
            // Verify search_name
            if( is_new ){
                failures += this.validateField( $('#search-name-control-group', this.$el), $('input[name=name]', this.$el).val(), "Cannot be empty",
                        function(val){
                            return val.length !== 0;
                        }
                );
            }
            
            // Verify namespace
            if( is_new ){
                failures += this.validateField( $('#namespace-control-group', this.$el), $('select[name=namespace]', this.$el).val(), "Cannot be empty",
                        function(val){
                            return val.length !== 0;
                        }
                );
            }
            
            // Verify search
            failures += this.validateField( $('#search-control-group', this.$el), $('textarea[name=search]', this.$el).val(), "Cannot be empty",
                    function(val){
                        return val.length !== 0;
                    }
            );
            
        	// Verify cron-schedule
            failures += this.validateField( $('#cron-schedule-control-group', this.$el), $('input[name=cron_schedule]', this.$el).val(), "Cannot be empty",
                    function(val){
                        return val.length !== 0;
                    }
            );
            
        	// Verify duration
            failures += this.validateField( $('#duration-control-group', this.$el), $('input[name=duration]', this.$el).val(), "Cannot be empty if group-by fields are provided",
                    function(val){
            			if( $('input[name=hidden-group_by]', this.$el).val().length > 0 ){
            				return val.length !== 0;
            			}
            			else{
            				return true;
            			}
                    }.bind(this));
            
            // Verify email subject
            failures += this.validateField( $('#email-subject-control-group', this.$el), $('input[name=email_subject]', this.$el).val(), "Cannot be empty",
                    function(val){
            			if( $('input[name=email_isenabled]', this.$el).prop('checked') ){
            				return val.length !== 0;
            			}
            			else{
            				return true;
            			}
                    }.bind(this));
            
            // Verify email addresses
            failures += this.validateField( $('#email-to-control-group', this.$el), $('input[name=hidden-email_to]', this.$el).val(), "Cannot be empty",
                    function(val){
            			if( $('input[name=email_isenabled]', this.$el).prop('checked') ){
            				
            				var email_list_re = /^([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4})([,][A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4})*$/i;
            				
            				return email_list_re.test(val);
            			}
            			else{
            				return true;
            			}
                    }.bind(this));
            
            // Verify risk score
            failures += this.validateField( $('#risk-score-control-group', this.$el), $('input[name=risk_score]', this.$el).val(), "Must be an integer",
                    function(val){
            			if( $('input[name=risk_isenabled]', this.$el).prop('checked') ){
            				return !isNaN(this.parseIntIfValid(val));
            			}
            			else{
            				return true;
            			}
                    }.bind(this));
            
            // Verify risk object type
            failures += this.validateField( $('#risk-object-type-control-group', this.$el), mvc.Components.get("risk_object_type").val(), "Must be selected",
                    function(val){
            			if( $('input[name=risk_isenabled]', this.$el).prop('checked') && (val == undefined || val.length <= 0) ){
            				return false;
            			}
            			else{
            				return true;
            			}
                    }.bind(this));
            
            // Verify risk object
            failures += this.validateField( $('#risk-object-control-group', this.$el), $('input[name=risk_object]', this.$el).val(), "Must be defined",
                    function(val){
            			if( $('input[name=risk_isenabled]', this.$el).prop('checked') && val.length <= 0){
            				return false;
            			}
            			else{
            				return true;
            			}
                    }.bind(this));
            
            // Return a boolean indicating the validation succeeded or not
            return failures === 0;
            
        },
        
        /**
         * Get the fields out of a search and convert to an array.
         */
        getNamedArrayFromSearch: function(search){
        	var a = {
        			search_name: search.name,
        			namespace: search.acl['app'],
        			owner: search.acl['owner'],
        			domain: search.content['security_domain'],
        			start_time: search.content['dispatch.earliest_time'],
        			end_time: search.content['dispatch.latest_time'],
        			search: search.content['savedsearch'],
        			search_spec: search.content['search'],
        			description: search.content['description'],
        			cron_schedule: search.content['cron_schedule'],
        			severity: search.content['severity'],
        			
        			default_status: search.content['default_status'],
        			default_owner: search.content['default_owner'],
        			
        			drilldown_search: search.content['drilldown_search'],
        			drilldown_name: search.content['drilldown_name'],
        			
        			duration: search.content['alert.suppress.period'],
        			group_by: search.content['alert.suppress.fields'],
        			
        			email_to: search.content['action.email.to'],
        			email_subject: search.content['action.email.subject'],
        			email_sendresults: search.content['action.email.sendresults'] == 1,
        			email_isenabled: search.content['action.email'] == 1,
        			
        			notable_isenabled: search.content['action.summary_index'] == 1 && search.content['action.summary_index._name'] == 'notable',
        			
        			risk_score: search.content['action.risk._risk_score'],
        			risk_object_type: search.content['action.risk._risk_object_type'],
        			risk_object: search.content['action.risk._risk_object'],
        			risk_isenabled: search.content['action.risk'] == 1,
        			
        			rss_isenabled: search.content['action.rss'] == 1,
        			script_isenabled: search.content['action.script'] == 1,
        			script_filename: search.content['action.script.filename'],
        			
        			rule_title: search.content['rule_title'],
        			rule_description: search.content['rule_description'],
        			name: search.content['rule_name']
        	};
        	
        	// Filter a group-by of 'const_dedup_id', this is automatically added by the correlation search helper class when a duration is set but no group-by
        	if( a.duration && a.group_by == "const_dedup_id"){
        		a.group_by = "";
        	}
        	
        	// Determine the email format
        	if(search.content['action.email.sendcsv'] == 1) {
        		a.email_format = 'csv';
        	} else if(search.content['action.email.sendpdf'] == 1) {
        		a.email_format = 'pdf';
        	} else if(search.content['action.email.inline'] == 1) {
        		a.email_format = 'html';
        	} else {
        		// set default; will be unused unless action.email.sendresults == 1
        		a.email_format = 'html';
        	}

        	return a;
        },
        
        /**
         * Returns true if the search time appears to be real-time
         */
        isTimeRT: function(search_str){
        	return search_str.indexOf("rt") >= 0;
        },
        
        /**
         * Get information that is necessary for making correlation searches
         */
        getCorrelationSearchInfo: function(){
        	
        	if( this.correlation_search_meta_info ){
        		return this.correlation_search_meta_info;
        	}
        	
    		var uri = Splunk.util.make_url('/custom/SA-ThreatIntelligence/correlation_searches/all_info');
    		
    		jQuery.ajax({
    			url:     uri,
    			type:    'GET',
    			cache:    false,
    			success: function(result, textStatus, jqXHR ) {
	    				
	    			    if(result !== undefined && result.isOk === false){
	    			    	alert(result.message);
	    		        }
	    			    else if( result !== undefined && result !== "" && !result.preview && result !== undefined && jqXHR.status == 200 ){
	    			    	this.correlation_search_meta_info = result;
	    			    }
    				}.bind(this),
    			async:   false
    		});
    		
    		return this.correlation_search_meta_info;
        	
        },
        
        /**
         * Get information that is necessary for managing notable events.
         */
        getNotableInfo: function(){
        	
        	if( this.notable_info ){
        		return this.notable_info;
        	}
        	
    		var uri = Splunk.util.make_url('/custom/SA-ThreatIntelligence/notable_info/all');
    		
    		jQuery.ajax({
    			url:     uri,
    			type:    'GET',
    			cache:    false,
    			success: function(result, textStatus, jqXHR ) {
	    				
	    			    if(result !== undefined && result.isOk === false){
	    			    	alert(result.message);
	    		        }
	    			    else if( result !== undefined && result !== "" && !result.preview && result !== undefined && jqXHR.status == 200 ){
	    			    	this.notable_info = result;
	    			    }
    				}.bind(this),
    			async:   false
    		});
    		
    		return this.notable_info;
        	
        },
        
        /**
         * Open the link to the email settings page.
         */
        openEmailSettingsLink: function(){
        	window.open(Splunk.util.make_url("/manager/" + utils.getCurrentApp()  + "/admin/alert_actions/email?action=edit"), '_blank');
        	return false;
        },
        
        /**
         * Render the editor.
         */
        render: function(){
        	
        	// Make sure the user has the necessary capability
        	if( !this.hasCapability('edit_correlationsearches') ){
        		this.$el.html('<div class="permission_denied">You do not have the necessary capabilities required to edit Correlation Searches.  Please contact your Splunk administrator.</div>');
        		return this;
        	}
        	
        	// This indicates if the editor is making a new search or editing an existing one
        	var is_new = true;
        	
        	// Get the name in case we are editing an existing search
        	var search_name = null;
        	
        	if( this.search_name !== null ){
        		search_name = this.search_name;
        	}
        	else{
        		search_name = this.getURLParameter("search");
        		
        		// If we couldn't get the search from the search parameter, try "name"
        		if( !search_name ){
        			search_name = this.getURLParameter("name");
        		}
        		
        		// Remember the loaded search
        		this.search_name = search_name;
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
            			namespace: '',
            			domain: '',
            			start_time: '',
            			end_time: '',
            			search: '',
            			search_spec: '',
            			description: '',
            			cron_schedule: '',
            			severity: '',
            			
            			default_status: '',
            			default_owner: '',
            			
            			drilldown_search: '',
            			drilldown_name: '',
            			
            			duration: '',
            			group_by: '',
            			
            			email_to: '',
            			email_subject: '',
            			email_format: '',
            			email_sendresults: '',
            			email_isenabled: false,
            			
            			notable_isenabled: false,
            			
            			risk_score: '',
            			risk_object_type: '',
            			risk_object: '',
            			risk_isenabled: false,
            			
            			rss_isenabled: false,
            			script_isenabled: false,
            			script_filename: '',
            			
            			rule_title: '',
            			rule_description: '',
            			name: ''
            	};
        		
        		is_new = true;
        	}
        	
        	// Add the param indicating if this is a new search
        	content.is_new = is_new;
        	
        	// Add some other parameters
        	content.list_link = this.list_link;
        	content.list_link_title = this.list_link_title;
        	
        	// Assume that the user has permission to edit
        	content.can_edit = true;
        	
        	// Get the information regarding correlation searches
        	correlation_info = this.getCorrelationSearchInfo();
        	content.domains = correlation_info['domains'];
        	content.namespaces = correlation_info['namespaces'];
        	content.severities = correlation_info['severities'];
        	content.email_formats = correlation_info['email_formats'];
        	
        	// Get the information regarding notable events
        	var notable_info = this.getNotableInfo();
        	content.owners = notable_info['users'];
			content.statuses = notable_info['statuses'];
			content.urgencies = notable_info['urgencies'];
        	
        	// Render the view
        	this.$el.html(_.template(CorrelationSearchEditorTemplate, content));
        	
        	// Create the search to populate the object types
        	var search_manager = new SearchManager({
                autostart: true,
                id: 'risk_object_type_search',
                earliest_time: "-24h",
                latest_time: "now",
                search: '| `risk_object_types`'
            }, {tokens: true});
        	
            // Make the input for the list of risk object types
            var risk_object_type = new DropdownInput({
                "id": "risk_object_type",
                "selectFirstChoice": false,
                "value": "$form.risk_object_type$",
                "managerid": "risk_object_type_search",
                "valueField": "risk_object_type",
                "labelField": "risk_object_type",
                "showClearButton": false,
                "el": $('#risk_object_type', this.$el)
            }, {tokens: true}).render();
            
            // Set the value of the risk object type
            mvc.Components.get("risk_object_type").val(content.risk_object_type);
        	
        	this.toggleCronSchedule();
        	this.toggleEmailAction();
        	this.toggleScriptAction();
        	this.toggleRiskAction();
        	this.toggleNotableAction();
        	
        	// Make the group-by fields a list of tags
        	$("input[name='group_by']", this.$el).tagsManager({
        		delimiters: [44, 9, 13], // tab, enter, comma
        		prefilled: content['group_by']
        	});
        	
        	// Make the email addresses a list of tags
        	$("input[name='email_to']", this.$el).tagsManager({
        		delimiters: [44, 9, 13], // tab, enter, comma
        		prefilled: content['email_to']
        	});
        	
        	// Update the information regarding the search spec
        	var using_search_spec = false;
        	var search_spec_parsed = null;
        	
        	// Make sure we even have a search spec
        	if( content.search_spec.length > 0 ){
        		try{
        			search_spec_parsed = $.parseJSON(content.search_spec);
        			
        			using_search_spec = search_spec_parsed.hasOwnProperty('searches');
        		}
        		catch(SyntaxError){
        			using_search_spec = false;
        		}
        	}
        	
        	if( content.search_spec && using_search_spec ){
        		this.updateSearchInformation(content.search, search_spec_parsed, undefined, undefined, using_search_spec);
        	}
        	
            return this;
        }
    });
    
    return CorrelationSearchEditorView;
});
