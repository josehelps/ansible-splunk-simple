require.config({
    paths: {
        text: "../app/SA-Utils/js/lib/text",
        tagmanager: '../app/SA-Utils/contrib/tagmanager/tagmanager',
        console: '../app/SA-Utils/js/util/Console'
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
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "text!../app/SA-Utils/js/templates/SwimlaneEditor.html",
    "tagmanager",
    "css!../app/SA-Utils/contrib/tagmanager/tagmanager.css",
    "css!../app/SA-Utils/css/SwimlaneEditor.css",
    "console"
], function(
    _,
    Backbone,
    mvc,
    $,
    SimpleSplunkView,
    SwimlaneEditorTemplate) {
	
    // Define the custom view class
    var SwimlaneEditorView = SimpleSplunkView.extend({
        className: "SwimlaneEditorView",
        
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
                   	
        	// Get the name in case we are editing an existing search
        	if( this.search_name === null ){
        		this.search_name = this.getURLParameter("search");
        	}
        	
        	this.is_new = (this.search_name === null);
        	this.app = null;
        	this.owner = null;
        	this.search = null;
        },

        events: {
            "click #save": "save",
            "click #cancel": "redirectToList"
        },

        /**
         * Set the dialog such that it is showing saving progress.
         */
        showSaving: function(saving){
        	
        	if(saving){
        		$("#save", this.$el).text("Saving...");
            	$("#save", this.$el).attr("disabled", "true");
            	
        	}
        	else{
        		$("#save", this.$el).text("Save");
            	$("#save", this.$el).removeAttr("disabled");
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
         * Validate the provided options.
         */
        validate: function(){
            // Record the number of failures
            var failures = 0;
            
            // Verify search_name
            if( this.is_new ){
                failures += this.validateField( $('#search-name-control-group', this.$el), $('#search_name', this.$el).val(), "Cannot be empty",
                        function(val){
                            return val.length !== 0;
                        }
                );
            }
            
            // Verify app
            if( this.is_new ){
                failures += this.validateField( $('#app-control-group', this.$el), $('#app', this.$el).val(), "Cannot be empty",
                        function(val){
                            return val.length !== 0;
                        }
                );
            }
            
            // Verify title
            failures += this.validateField( $('#title-control-group', this.$el), $('#title', this.$el).val(), "Cannot be empty",
                    function(val){
                        return val.length !== 0;
                    }
            );
            
            // Verify Search
            failures += this.validateField( $('#search-control-group', this.$el), $('#search', this.$el).val(), "Cannot be empty",
                    function(val){
                        return val.length !== 0;
                    }
            );
            
            // Verify drilldown field
            failures += this.validateField( $('#drilldown-search-control-group', this.$el), $('#drilldown_search', this.$el).val(), "Cannot be empty",
                    function(val){
                		return val.length !== 0;
            		}
            );
            
            // Verify constraint fields
            failures += this.validateField( $('#constraint-fields-control-group', this.$el), $('input[name=hidden-constraint_fields]', this.$el).val(), "Cannot be empty",
                    function(val){
                		return val.length !== 0;
            		}
            );
            
            // Return a boolean indicating the validation succeeded or not
            return failures === 0;
            
        },
        
        /**
         * Get the fields out of a search and convert to an array.
         */
        getNamedArrayFromSearch: function(search){
        	var a = {
        			search_name: search.name,
        			app: search.acl['app'],
        			owner: search.acl['owner'],
        			title: search.content['action.swimlane.title'],
        			drilldown_search: search.content['action.swimlane.drilldown_search'],
        			color: search.content['action.swimlane.color'],
        			constraint_method: search.content['action.swimlane.constraint_method'],
        			constraint_fields: search.content['action.swimlane.constraint_fields'],
        			search: search.content['search']
        	};
        	
        	return a;
        },
        
        save: function() {
        	
        	// Make sure that the options appear to be valid
        	if( !this.validate() ){
        		// Could not validate options
        		return;
        	}
        	
        	// Prepare the arguments
            var params = new Object();
            params.output_mode = 'json';
            
            // Specify the saved search information
            params.search = $('#search', this.$el).val();
            
            if( this.is_new ){
            	
            	params.name = $('#search_name', this.$el).val();
            }
            
            // Specify the swimlane actions information
            params['action.swimlane'] = 1;
            params['actions'] = 'swimlane';
            params['action.swimlane.title'] = $('#title', this.$el).val();
            params['action.swimlane.drilldown_search'] = $('#drilldown_search', this.$el).val();
            params['action.swimlane.color'] = $('#color', this.$el).val();
            params['action.swimlane.constraint_fields'] = $('input[name=hidden-constraint_fields]', this.$el).val();
            
            if( $('#entity_type', this.$el).val() == "asset" ){
            	params['display.page.asset_investigator.0.order'] = ' ';
            	params['action.swimlane.constraint_method'] = 'reverse_asset_lookup';
            }
            else{
            	params['display.page.identity_investigator.0.order'] = ' ';
            	params['action.swimlane.constraint_method'] = 'reverse_identity_lookup';
            }
            
        	// Get the parameters that we need to build the URL, including...
            //   ... the search name ...
        	var search_name = this.search_name;
        	
        	if( this.is_new ){
        		search_name = $('#search_name', this.$el).val();
        	}
        	
        	//   ... and the app ...
        	var app = this.app;
        	
        	if( this.is_new ){
        		app = $('#app', this.$el).val();
        	}
        	
        	if( app === "" || app === null ){
        		app = this.default_app;
        	}
        	
            //   ... and the owner ...
        	var owner = 'nobody';
        	
        	if( !this.is_new ){
        		owner = this.owner;
        	}
        	
        	// Get the entity
        	var entity = search_name;
        	
        	if( this.is_new ){
        		entity = "";
        	}
        	
        	// Make the URL
            var uri = Splunk.util.make_url('/splunkd/__raw/servicesNS', 'nobody', app, 'configs/conf-savedsearches', entity);
            
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
                    	if( this.is_new ){
	                    	this.search_name = search_name;
	                    	this.is_new = false;
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
        
        render: function() {
        	
        	var search = null;
        	var content = null;
        	
        	// Load the content from the search
        	if( !this.is_new ){
        		search = this.fetchSearch(this.search_name);
        		content = this.getNamedArrayFromSearch(search);
        		this.app = search.acl['app'];
        		this.owner = search.acl['owner'];
        	}
        	else{
        		// Use the default content otherwise
        		content = {
            			search_name: '',
            			app: this.default_app,
            			owner: 'nobody',
            			title: '',
            			drilldown_search: '',
            			color: '',
            			constraint_method: '',
            			constraint_fields: [],
                		search: ''
            	};
        	}
        	
        	// Add the param indicating if this is a new search
        	content.is_new = this.is_new;
        	
        	// Add some other parameters
        	content.list_link = this.list_link;
        	content.list_link_title = this.list_link_title;
        	
        	// Get the list of apps
        	var apps = this.fetchApps();
        	content.apps = apps;
        	
        	// Get the list of colors
        	content.colors = [ 
        	                   { 'name' : 'blue', 'label': 'Blue' },
        	                   { 'name' : 'yellow', 'label': 'Yellow' },
        	                   { 'name' : 'orange', 'label': 'Orange' },
        	                   { 'name' : 'red', 'label': 'Red' },
        	                   { 'name' : 'green', 'label': 'Green' },
        	                   { 'name' : 'purple', 'label': 'Purple' }
        	                 ];
        	
        	// Get the list of entity types
        	content.entity_types = [ 
        	                   { 'name' : 'asset', 'label': 'Asset' },
        	                   { 'name' : 'identity', 'label': 'Identity' }
        	                 ];
        	
        	if( content.constraint_method == "reverse_asset_lookup" ){
        		content.entity_type = "asset";
        	}
        	else{
        		content.entity_type = "identity";
        	}
        	
        	// See if the user can edit
        	content.can_edit = this.hasCapability("schedule_search"); //SOLNESS-4861
        	
        	// If the drilldown URI is just whitespace, then treat as nothing.
        	if( content.drilldown_search.replace(/^\s+|\s+$/g, '').length === 0 ){
        		content.drilldown_search = '';
        	}
        	
            this.$el.html(_.template(SwimlaneEditorTemplate, content));
            
            var tagclass = "";
            
            if( !content.can_edit ){
            	tagclass = "tm-tag-disabled";
            }
            
        	// Make the constraint fields a list of tags
        	$("#constraint_fields", this.$el).tagsManager({
        		delimiters: [44, 9, 13], // tab, enter, comma
        		prefilled: content['constraint_fields'],
        		tagClass: tagclass
        	});
            
            return this;
        }
        


    });
    
    return SwimlaneEditorView;
});
