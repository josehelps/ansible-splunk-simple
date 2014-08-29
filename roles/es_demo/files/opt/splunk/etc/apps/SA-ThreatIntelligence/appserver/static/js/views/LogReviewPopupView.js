require.config({
    paths: {
        text: '../app/SA-Utils/js/lib/text',
        console: '../app/SA-Utils/js/util/Console'
    }
});

define(['underscore', 'splunkjs/mvc', 'jquery', 'splunkjs/mvc/simplesplunkview', "splunkjs/mvc/simpleform/input/dropdown", 'text!../app/SA-ThreatIntelligence/js/templates/LogReviewPopup.html', "css!../app/SA-ThreatIntelligence/css/LogReviewPopup.css", "console"],
function(_, mvc, $, SimpleSplunkView, DropdownInput, LogReviewPopupTemplate) {
	
    // Define the custom view class
    var LogReviewPopupView = SimpleSplunkView.extend({
        className: "LogReviewPopupView",
     
        events: {
            "click #editAllSelected": "showLogReviewDialogSelected",
            "click #editAll": "showLogReviewDialogAllMatching",
            "click #selectAll": "selectAll",
            "click #unSelectAll": "unSelectAll",
            "click .save": "save",
        	"change textarea" : "validate",
        	"keyup textarea" : "validate"
        },
        
        
        /**
         * Setup the defaults
         */
        defaults: {
        	checkbox_el: null,
        	managerid: null,
        	show_select_unselect_all: true,
        	rule_uids_fx: null
        },
        
        /**
         * Initialize the class instance
         */
        initialize: function() {
        	
            // Apply the defaults
            this.options = _.extend({}, this.defaults, this.options);
        	
            this.rule_uids_fx = this.options.rule_uids_fx;
        	this.checkbox_el = this.options.checkbox_el;
        	this.show_select_unselect_all = this.options.show_select_unselect_all;      	
        	
        	if( this.options.managerid !== null ){
        		this.search = mvc.Components.get(this.options.managerid);
        	}
        	else{
        		this.search = null;
        	}
        	
        	// Hook into the search results
        	if( this.search !== null ){
        		this.search.on('search:done', function(){ this.updateResultInfo(); }.bind(this) );
        	}
        	
        	// These are internal variables for caching content
        	this.result_count = null;
        	this.notable_info = null;
        	this.set_editing_only_selected = false;
        	
        },
        
        /**
         * Set the dialog such that it is showing saving progress
         */
        showSaving: function(saving){
        	
        	if(saving){
        		$("#save", this.$el).text("Saving...");
        		$("#save", this.$el).attr("disabled", "true");
            	$("#cancel", this.$el).attr("disabled", "true");
            	
        	}
        	else{
        		$("#save", this.$el).text("Save changes");
            	$("#save", this.$el).removeAttr("disabled");
            	$("#cancel", this.$el).removeAttr("disabled");
        	}
        	
        },
        
        /**
         * Update the parts of the form that rely on search information.
         */
        updateResultInfo: function(){
        	
        	if( this.search ){
	        	var search_data = this.search.get('data');
	        	
	        	if( search_data && search_data.isDone ){
		        	this.result_count = search_data.eventCount;
		        	
		        	if( this.result_count > 0 ){
		        		$("#matching_event_count", this.$el).text( String(this.result_count) + " ");
		        		return;
		        	}
	        	}
        	}
        	
        	$("#matching_event_count", this.$el).text("");
        	
        },
        
        /**
         * Get information that is necessary for 
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
         * Set the checkbox as checked on all of the checkbox inputs.
         */
        selectAll: function(){
        	if( this.checkbox_el !== null ){
        		$('input:checkbox', this.checkbox_el).prop('checked', true);
        	}
        },
        
        /**
         * Set the checkbox as unchecked on all of the checkbox inputs.
         */
        unSelectAll: function(){
        	if( this.checkbox_el !== null ){
        		$('input:checkbox', this.checkbox_el).prop('checked', false);
        	}
        },
        
        /**
         * Get the selected rule UIDs.
         */
        getSelectedRuleUIDs: function(){
        	
        	var rule_ids = [];
        	
        	// Use the function if provided
        	if(this.rule_uids_fx !== null){
        		rule_ids = this.rule_uids_fx();
        	}
        	
        	// Otherwise, use the check-boxes elements if provided
        	else if(this.checkbox_el !== null){
            	$("input:checked", this.checkbox_el).each(function( index ) {
            		rule_ids.push($( this ).val() );
            	});
        	}
        	
        	return rule_ids;
        },
        
        
        /**
         * Show the log review dialog for editing of the selected items.
         */
        showLogReviewDialogSelected: function(){
        	
        	// Make sure at least one item is selected
        	if( this.getSelectedRuleUIDs().length <= 0 ){
        		this.showProblemDialog("You must select at least one notable event");
        	}
        	else{
        		this.setEditingOnlySelected(true);
        		this.showLogReviewDialog();
        	}
        },
        
        /**
         * Show a modal dialog noting that something didn't work.
         */
        showProblemDialog: function(message){
        	$("#message", this.$el).text(message);
    		$("#logReviewPopupProblemModal", this.$el).modal();
        },
        
        /**
         * Set the form element that indicates if we are editing only the selecting notable events.
         */
        setEditingOnlySelected: function(value){
        	this.set_editing_only_selected = value;
        },
        
        /**
         * Show a dialog for editing all of the matching entries.
         */
        showLogReviewDialogAllMatching: function(){
        	this.setEditingOnlySelected(false);
        	this.showLogReviewDialog();
        	return true;
        },
        
        /**
         * Show the log review dialog.
         */
        showLogReviewDialog: function(){
        	
        	if( this.search ){
        		
        		// Get the search data
	        	var search_data = this.search.get('data');
	        	
	        	// * No search data available
	        	if( !search_data ){
	        		this.showProblemDialog("The search has not returned any results to modify yet");
	        		return false;
	        	}
	        	
	        	// * Search is real-time and not done
	        	if( search_data.isRealTimeSearch && !search_data.isDone ){
	        		this.showProblemDialog("The search is running in real-time and was not finalized; please finalize the search before attempting to edit the events");
	        		return false;
	        	}
	        	
	        	// * Search is not yet done
	        	if( !search_data || !search_data.isDone ){
	        		this.showProblemDialog("The search is not yet done; please wait for the search to complete or finalize it to continue");
	        		return false;
	        	}
	        	
	        	// * Search didn't return anything
	        	else if( search_data && search_data.isDone && search_data.eventCount === 0 ){
	        		this.showProblemDialog("The search has not returned any results to modify");
	        		return false;
	        	}
        	}
        	else{
        		// No search exists
        		this.showProblemDialog("The search has not returned any results to modify");
        		return false;
        	}
        	
        	this.hideErrorMessage();
        	this.showSaving(false);
        	$('#logReviewPopupModal', this.$el).modal();
        },
        
        /**
         * Validate the given field.
         */
        performValidate: function(field_selector, val, message, test_function){
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
         * Indicates if the item is defined and greater than zero length.
         */
        isNotEmpty: function(value){
        	if( value === undefined ){
        		return false;
        	}
        	else if( value.length === 0){
        		return false;
        	}
        	else{
        		return true;
        	}
        },
        
        /**
         * Validate the input in the log review popup dialog.
         */
        validate: function(){
        	
            // Record the number of failures
            var failures = 0;
            
            var notable_info = this.getNotableInfo();
            var comment_length_required = notable_info["comment_length_required"];
            var comment_length_provided = $("textarea[name='comment']").val().length;
            
            // Update the count of characters needed
            if( comment_length_required > 0 && $("textarea[name='comment']").val() ){
            	
            	var more_needed = comment_length_required - comment_length_provided;
            	
            	if( more_needed < 0 ){
            		more_needed = 0;
            	}
            	
            	$('#moreCharsNeeded').text(String(more_needed));
            }
            
            // Verify the comment is provided
            failures += this.performValidate( $("#comment-control-group"), $("textarea[name='comment']").val(), "A comment of length " + String(comment_length_required) + " must be provided",
                    function(val){
                        return val.length >= comment_length_required;
                    }
            );
            
            // Make sure something on the form was filled out
            var filled_out = false;
            
            if( this.isNotEmpty( mvc.Components.get("log_review_statuses").val() ) || this.isNotEmpty( mvc.Components.get("log_review_urgencies").val() ) || this.isNotEmpty( mvc.Components.get("log_review_owners").val() ) ){
            	filled_out = true;
            }
            
        	// Stop if the user didn't do anything
            if( !filled_out && comment_length_provided === 0){
            	alert("Nothing in the form has been filled out, there is nothing to do");
            	return false;
            }
            
            // Return a boolean indicating the validation succeeded or not
            return failures === 0;
        	
        },
        
        /**
         * Refresh the results because we successfully applied changes.
         */
        refreshResults: function(){
        	
            if( this.search ){
	        	this.search.startSearch();
            }
            
        	console.log("Restarting search");
        },
        
        /**
         * Clear the form values so that we can start over.
         */
        clearFormValues: function(){
        	mvc.Components.get("log_review_statuses").val("");
            mvc.Components.get("log_review_urgencies").val("");
            mvc.Components.get("log_review_owners").val("");
            $("textarea[name='comment']", this.$el).val("");
        },
        
        /**
         * POST the changes to the server.
         */
        saveStatusChanges: function(){
        	
        	// Get the rule_ids that are being edited
        	var rule_ids = this.getSelectedRuleUIDs();
        	
        	// Make the other arguments
            var params = new Object();
            params.output_mode = 'json';
            
            params.status = mvc.Components.get("log_review_statuses").val();
            params.urgency =  mvc.Components.get("log_review_urgencies").val();
            params.newOwner =  mvc.Components.get("log_review_owners").val();
            params.comment = $("textarea[name='comment']", this.$el).val();
            
            // Determine if we should ignore the filtering down to the checked events
            if( this.set_editing_only_selected ){
            	params["ruleUIDs"] = rule_ids;
            }
            
            // Get the search ID if available
            if( this.search ){
	        	var search_data = this.search.get('data');
	        	params.searchID = search_data.sid;
            }
            
            // Make the URL
            var uri = Splunk.util.make_url('/custom/SA-ThreatIntelligence/notable_events/update_status');
            
            // Fire off the request
            jQuery.ajax({
                url:     uri,
                type:    'POST',
                data:    params,
                success: function(result) {

                    if(result !== undefined && result.isOk === false){
                         this.showErrorMessage("Incident review settings could not be saved: " + result.message);
                    }
                    else{
                    	
                    	// Make sure that the REST indicates success
                    	if(!result['success']){
                    		var msg = "The changes to the notable events could not be saved";
                    		
                    		if(result.hasOwnProperty('message')){
                    			msg = result['message'];
                    		}
                    		
                    		// Show the dialog indicating that something went wrong
                    		this.showErrorMessage(msg);
                    		//alert(msg);
                    		
                    		return;
                    	}
                    	// Examine the results and post a message accordingly
                    	else if(result['failure_count'] > 0 && result['success_count'] === 0){
                    		this.showErrorMessage( result['failure_count'] + " events could not be updated");
                    	}
                    	else if(result['failure_count'] > 0){
                    		this.showErrorMessage( result['failure_count'] + " events could not be updated though " + result['success_count'] + " had been updated");
                    	}
                    	else{
                    		this.showSuccessMessage( result['success_count'] + " events successfully updated");
                    	}
                    	
                    	// Clear the form values
                    	this.clearFormValues();
                    	
                    	// Hide the modal
                    	$('#logReviewPopupModal', this.$el).modal('hide');
                    	 
                    	// Refresh the results to show the changes
                    	this.refreshResults();
                    }
                }.bind(this),
                error: function(result) {
                	
                	if(result.hasOwnProperty('responseJSON') && result.responseJSON.hasOwnProperty('messages') && result.responseJSON.messages.length > 0){
                		this.showErrorMessage(result.responseJSON.messages[0].text);
                	}
                	else{
                		this.showErrorMessage("Notable events could not be updated");
                	}
                	
                }.bind(this),
                complete: function(jqXHR, textStatus){
                	this.showSaving(false);
                }.bind(this)
            });
            
            
        },
        
        /**
         * Show an error message.
         */
        showErrorMessage: function(message){
        	$('#error_text', this.$el).text(message);
        	$('#error_message', this.$el).show();
        	console.warn(message);
        },
        
        /**
         * Hide the error message.
         */
        hideErrorMessage: function(message){
        	$('#error_message', this.$el).hide();
        },
        
        showSuccessMessage: function(message){
        	console.info(message);
        },
        
        /**
         * Save the changes if the form data validates.
         */
        save: function(){
        	
        	this.hideErrorMessage();
        	
        	// Make sure the form data validates
        	if( this.validate() ){
        		this.showSaving(true);
            	this.saveStatusChanges();
        	}
        	
        },
        
        /**
         * Render the controls.
         */
        render: function(){
        	
        	var notable_info = this.getNotableInfo();
        	
            // Render the template
            this.$el.html( _.template(LogReviewPopupTemplate,{
    			owners:                   notable_info['users'],
    			statuses:                 notable_info['statuses'],
    			urgencies:                notable_info['urgencies'],
    			comment_length_required:  notable_info['comment_length_required'],
    			show_select_unselect_all: this.show_select_unselect_all,
                urgency_override_allowed: notable_info['urgency_override_allowed']
            }) );
            
            // Make the input for the owners
            var owners_input = new DropdownInput({
                "id": "log_review_owners",
                "selectFirstChoice": false,
                "default": "",
                "showClearButton": true,
                "el": $('#log_review_owners_input', this.$el)
            }, {tokens: true});
            
            owners_input.render();
            
            owners_input.settings.set("choices", notable_info['users']);
            
            // Make the input for the urgencies
            var urgencies_input = new DropdownInput({
                "id": "log_review_urgencies",
                "selectFirstChoice": false,
                "default": "",
                "showClearButton": true,
                "el": $('#log_review_urgencies_input', this.$el)
            }, {tokens: true});
            
            urgencies_input.render();
            
            urgencies_input.settings.set("choices", notable_info['urgencies']);
            
            // Make the input for the statuses
            var statuses_input = new DropdownInput({
                "id": "log_review_statuses",
                "selectFirstChoice": false,
                "default": "",
                "showClearButton": true,
                "el": $('#log_review_statuses_input', this.$el)
            }, {tokens: true});
            
            statuses_input.render();
            
            var enabled_notable_statuses = [];
            
            for( var i = 0; i < notable_info['statuses'].length; i++){
            	
            	if( !notable_info['statuses'][i]['disabled'] ){
            		enabled_notable_statuses.push(notable_info['statuses'][i]);
            	}
            }
            
            statuses_input.settings.set("choices", enabled_notable_statuses);
            
            // Update parts of the page that change based on search results
            this.updateResultInfo();
        	
        	return this;
        }
    });
    
    return LogReviewPopupView;
});