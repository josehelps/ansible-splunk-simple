require.config({
    paths: {
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
    "splunkjs/mvc/simpleform/formutils",
    "splunkjs/mvc/simpleform/input/dropdown",
    "splunkjs/mvc/simpleform/input/text",
    'splunkjs/mvc/searchmanager',
    "text!../app/SA-ThreatIntelligence/js/templates/AdHocRiskScoreDialog.html",
    "console"
], function(_, Backbone, mvc, $, SimpleSplunkView, FormUtils, DropdownInput, TextInput, SearchManager, AdHocRiskScoreViewTemplate){
	
    // Define the custom view class
    var AdHocRiskScoreView = SimpleSplunkView.extend({
    	
        className: "AdHocRiskScoreView",

        /**
         * Setup the defaults
         */
        defaults: {
        	search_managers: []
        },
        
        /**
         * Wire up the events
         */
        events: {
        	"click #create-adhoc-risk": "openAdHocRiskDialog",
        	"click .btn-save" : "saveAdHocEntry"
        },
        
        initialize: function() {
        	// Apply the defaults
        	this.options = _.extend({}, this.defaults, this.options);
        	
        	this.search_managers = this.options.search_managers.slice(0); // Includes the search managers that ought to be restarted once the changes are posted
        	
        	this.capabilities = null;
        },
        
        /**
         * Set the dialog such that it is showing saving progress.
         */
        showSaving: function(saving){
        	
        	if(saving){
        		$("#save", this.$el).text("Saving...");
            	$("#cancel", this.$el).attr("disabled", "true");
        	}
        	else{
        		$("#save", this.$el).text("Save");
            	$("#cancel", this.$el).attr("disabled", "false");
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
         * Parse the integer if it is valid; return NaN if it is not.
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
         * Validate the form values.
         */
        validate: function(){
        	
            if(!this.parseIntIfValid(mvc.Components.get("risk_score").val())){
            	this.showWarning("The risk score must be a valid integer");
            	return false;
            }
            
            if(mvc.Components.get("risk_object").val() === "" ){
            	this.showWarning("The risk object must be defined");
            	return false;
            }
            
            if(mvc.Components.get("risk_object_type").val() === ""){
            	this.showWarning("The risk object type must be selected");
            	return false;
            }
            
            if(mvc.Components.get("risk_description").val() === ""){
            	this.showWarning("The risk description must be provided");
            	return false;
            }
            
            return true;
        },
        
        /**
         * Make the content body of the event we are creating.
         */
        makeContentBody: function(fields){
            
            // Make the content body field
            var content_body = '\n==##~~##~~  1E8N3D4E6V5E7N2T9 ~~##~~##==\n';
            
        	for (var key in fields) {
        		content_body = content_body + key + '=\"' + fields[key] + '\", ';
        	}
            
            return content_body;
    	},
        
    	/**
    	 * Clear the form fields.
    	 */
    	clearForm: function(){
    		this.hideWarning();
    		
    		mvc.Components.get("risk_description").val("");
            mvc.Components.get("risk_score").val("");
            mvc.Components.get("risk_object").val("");
            mvc.Components.get("risk_object_type").val("");
    	},
    	
    	/**
    	 * Kick off the searches.
    	 */
    	kickSearches: function(){
        	// Kick the searches
        	if( this.search_managers ){
        		
        		// If the search managers are an array, then kick off them all
        		if( Object.prototype.toString.call( this.search_managers ) === '[object Array]' ) {
        			
        			for( var i = 0; i < this.search_managers.length; i++ ){
        				this.search_managers[i].startSearch();
        			}
        		}
        		else{
        			this.search_managers.startSearch();
        		}
        		
        	}
    	},
    	
    	/**
    	 * Save an ad-hoc risk entry.
    	 */
        saveAdHocEntry: function(){
        	
        	// Validate the input
        	if( !this.validate() ){
        		return;
        	}
        	
           	// Prepare the arguments
            var params = new Object();
            params.index = 'risk';
            params.source = 'AdHoc Risk Score';
            params.sourcetype = 'stash_new';
            params.host = document.domain;
            params.output_mode = 'json';
            
            var content = new Object();
            content.description = mvc.Components.get("risk_description").val();
            content.risk_score = mvc.Components.get("risk_score").val();
            content.risk_object = mvc.Components.get("risk_object").val();
            content.risk_object_type = mvc.Components.get("risk_object_type").val();
            
            var uri = Splunk.util.make_url('/splunkd/__raw/services/receivers/simple');
            uri += '?' + Splunk.util.propToQueryString(params);
            
            // Change the dialog to show that we are trying to save
            this.showSaving(true);
            
            // Fire off the request
            jQuery.ajax({
                url:         uri,
                type:        'POST',
                data:        this.makeContentBody(content),
                contentType: false,
                processData: false,
                success: function(result) {
                	$("#adHocRiskScoreModal", this.$el).modal('hide');
                	this.clearForm();
                	this.kickSearches();
                }.bind(this),
                complete: function(jqXHR, textStatus){
                	this.showSaving(false);
                }.bind(this)
            });
        },
        
        /**
         * Open a dialog to make an ad-hoc risk entry.
         */
        openAdHocRiskDialog: function(){
        	$("#adHocRiskScoreModal", this.$el).modal();
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
         * Render the dialog.
         */
        render: function(){
        	
        	this.$el.html(AdHocRiskScoreViewTemplate);
        	
        	// Show the link to open the dialog if the user has the necessary permissions
        	if( this.hasCapability('edit_tcp') ){
        		$('#create-adhoc-risk-holder', this.$el).show();
        	}
        	
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
                "el": $('#risk-object-type', this.$el)
            }, {tokens: true}).render();
            
        	// The input for the risk object
        	var risk_object = new TextInput({
                "id": "risk_object",
                "searchWhenChanged": false,
                "value": "$form.risk_object$",
                "el": $('#risk-object', this.$el)
            }, {tokens: true}).render();
        	
        	// The input for the risk score
        	var risk_score = new TextInput({
                "id": "risk_score",
                "searchWhenChanged": false,
                "value": "$form.risk_score$",
                "el": $('#risk-score', this.$el)
            }, {tokens: true}).render();
        	
        	// The input for the risk description
        	var risk_description = new TextInput({
                "id": "risk_description",
                "searchWhenChanged": false,
                "value": "$form.risk_description$",
                "el": $('#risk-description', this.$el)
            }, {tokens: true}).render();
        	
        }
    });
    
    return AdHocRiskScoreView;
});