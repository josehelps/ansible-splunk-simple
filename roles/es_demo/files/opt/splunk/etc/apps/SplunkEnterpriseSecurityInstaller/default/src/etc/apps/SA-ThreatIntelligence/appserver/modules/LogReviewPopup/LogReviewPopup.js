Splunk.namespace("Module");

/**
 * The LogReviewPopup module provides the editor for modifying the status of notable events.
 * 
 * The class inherits from DispatchingModule so that the onJobDone() gets called once the job finishes.
 */

Splunk.Module.LogReviewPopup = $.klass(Splunk.Module.DispatchingModule, {
    initialize: function($super, container){
        $super(container);
        $(".logReviewPopupLink", this.container).click(this.openPopupFormSelected.bind(this));
        $(".logReviewPopupLinkAll", this.container).click(this.openPopupFormAllMatching.bind(this));

        var moduleReference = this;
        $("textarea", this.container).bind("keydown",function() {
            moduleReference.checkCommentLength(this,1024);
        });
    },

    // The following function ensures that comments are not too long
    checkCommentLength: function(field, maxlimit) {
        if ($(field).val().length > maxlimit ) {
            $(field).val($(field).val().substring( 0, maxlimit ));
            alert( 'Comment cannot include more than ' + maxlimit + ' characters.' );
            return false;
        }
    },
    
    
    // Get the the rule IDs that are going to be edited.
    setRuleUIDs: function() {
        // see below comment about our friend mr IE and his behavior around 
        // 'name' attributes. 
        var encodeHTMLEntities = function(string) {
            var entities = [[/&/g, "&amp;"], [/</g, "&lt;"], [/>/g, "&gt;"], [/"/g, "&quot;"]];
            var len=entities.length;
            var i = 0;
            for (i=0; i<len; i+=1) {
                var item = entities[i];
                string = string.replace(item[0], item[1]);
            }
            return string;
        };

        var form = $("form", this.container);
    
        $("form[name=LogReview] > input[name=ruleUIDs]").remove();
        $("form[name=LogReview] > input[class=oldStatus]").remove();
        
        $("input[name=ruleuid_field]:checked").each(
            function(){
                
                // using the checkbox in the one form, we make a hidden input 
                // in the other form.
                form.append(
                    $('<input type="hidden" name="ruleUIDs">')
                        .attr("value", $(this).attr("value"))
                );
            }
         );
         
        // Post a warning if no events are selected
        if( $("input[name=ruleuid_field]:checked") === null || $("input[name=ruleuid_field]:checked").length === 0 ){
            alert("Please select the events to edit.");
            return false; 
        }
        
        // Return true indicating that the form is cleared to be shown
        return true;
    },

    // Open the popup form for users that have selected the items they want to modify
    openPopupFormSelected: function(evt) {
        return this.openPopupForm(evt, false);
    },
    
    // Open the popup form to change all items that match the given filter
    openPopupFormAllMatching: function(evt) {
        return this.openPopupForm(evt, true);
    },
    
    // Get the number of events
    updateCount: function() {
    	
        var search = this.getContext().get("search");
        var is_done = search.job.isDone();
        var count = search.getEventCount();
        
        if( count === 0 ){
        	$(".logReviewPopupLinkAll", this.container).text("Edit all matching events");
        }
        else{
        	$(".logReviewPopupLinkAll", this.container).text("Edit all " + count + " matching events");
        }
    	
    },
    
    onContextChange: function() {
        this.updateCount();
    },
    
    onJobDone: function() {
    	this.updateCount();
    },
    
    onJobStatusChange: function() {
    	this.updateCount();
    },
    
    isFinalized: function() {
    	this.updateCount();
    },
    
    updateSearchID: function(){
    	
    	// Get the search
    	var context = this.getContext();
    	var search = context.get("search");
    	
    	// Get the search ID
        var sid = search.job.getSID();
        var form = $("form", this.container);
        
        // Remove the searchID list if it already exists
        $("form[name=LogReview] > input[name=searchID]").remove();
        
        // Append the search ID
        form.append( $('<input type="hidden" name="searchID">').attr("value", sid) );
    },
    
    // Open the popup form
    openPopupForm: function(evt, useSearchID) {
    	
    	// Get the search from the context so that we can determine if it is finalized
    	var context = this.getContext();
    	var search = context.get("search");
    	
    	// Don't show the log review popup if the search is not paused and not finalized since it will keep clearing the checkboxes (SOLNESS-787)
    	if( !search.job.isFinalized() && !search.job.isDone() ) {
    		alert("The search is still running. Please finalize it first in order to edit the status of notable events.");
    		return false;
    	}
    	
        var popup = null;
        var clonedForm = null;
        
        var formToClone = $("form", this.container);
        
        this.updateSearchID();
        
        // Get the notable events that will be modified
        if (useSearchID){
        	
        	// Make sure the search actually matched something, stop if it didn't
        	if( search.job.getEventCount() === 0 ){
        		alert("The search did not match any events. Thus, there are no events to edit.");
        		return false;
        	}
        	
            // Remove the ruleUIDs list
            $("form[name=LogReview] > input[name=ruleUIDs]").remove();
        }
        else{
        	// Get the list of selected events, stop if no events are selected
            if (!this.setRuleUIDs()) {
            	return false;
            }
            
        }
        
        // Now we create the instance of the Popup element and pass in our handleUpdate callback.
        // This will clone the contents of our form and create the popup onscreen.
        // All is ready for the user.
        this.popup = new Splunk.Popup(formToClone[0], {
            title: _('Edit Events'),
            buttons: [
                {
                    label: _('Cancel'),
                    type: 'secondary',
                    callback: function(){
                        return true;
                    }
                },
                {
                    label: _('Update'),
                    type: 'primary',
                    callback: this.onFormSubmit.bind(this)
                }
            ]
        });
        popupReference = this.popup.getPopup();

        this.clonedForm = $(popupReference).find("form");
        this.clonedForm.attr("action", Splunk.util.make_url('/custom/SA-ThreatIntelligence/notable_events/update_status') );
        
        return false;
        
    },

    // Determine if the selector is empty (exists and contains no content)
    isEmpty: function(selector){
    	
    	if( $(selector).length > 0 && $(selector).val().length === 0 ){
    		return true;
    	}
    	else{
    		return false;
    	}
    },
    
    // Submit the form
    onFormSubmit: function() {
        var moduleReference = this;
        
        // Don't try to submit if all inputs are empty (since this will do nothing)
        if ( this.isEmpty("select[name=urgency]") &&
        	 this.isEmpty("select[name=status]") &&
        	 this.isEmpty("select[name=newOwner]") &&
        	 this.isEmpty("textarea[name=comment]") ){
        	
        	alert("The form is empty. Please select fill in the fields that you want to change and submit again.");
        	
        	return false;
        }
        
        // Make sure that the comment is long enough
        commentLengthRequired = parseInt( $("input[name=commentLength]").val(), 10 );
        
        if( commentLengthRequired != NaN && $("textarea[name=comment]").val().length < commentLengthRequired ){
			alert("The comment must be " + commentLengthRequired + " characters or longer. Please update the comment accordingly.");
			
			return false;
		}
        
        // Submit the form
        try {
        	
            // Change it from 'Update' to 'Updating' 
            $('div.popupFooter button.splButton-primary span', this.popup._popup).text(_('Updating...'));
            
            // Grey it out and unbind the handler so you can't click it twice.
            $('div.popupFooter button.splButton-primary', this.popup._popup).unbind('click').removeClass('primary').addClass('secondary');
            
            // Submit the form
            this.clonedForm.ajaxSubmit({
                'success': function(json) {
                    var messenger = Splunk.Messenger.System.getInstance();
                    
                    if( $('div.popupFooter button.splButton-primary span').text().indexOf("Updating...") >= 0 ){
	                    Splunk.Popup._globalPopupCount -= 1;
	                    $('.popupContainer').remove();
	                    $('.splOverlay').remove();
                    }
                    
                    if (json["success"]) {
                	
                        // Print a success message if some changes were successfully submitted
                    	if( json["success_count"] > 0 && json["failure_count"] > 0 ){
                        	messenger.send('warn', "splunk.ess", json["message"] || json);
                        }
                        
                        // Print a message noting that one entry was updated
                        else if( json["success_count"] == 1 && json["failure_count"] <= 0 ){	
                        	messenger.send('info', "splunk.ess", json["success_count"] + " event successfully updated" );
                        }
                    	
                        // Print a message noting that multiple entries were updated
                        else if( json["success_count"] > 0 && json["failure_count"] <= 0 ){	
                        	messenger.send('info', "splunk.ess", json["success_count"] + " events successfully updated" );
                        }
                        
                        // Print a message describing failures
                        else{ // if( json["failure_count"] > 0 ){
                        	alert(json["failure_count"]);
                        	messenger.send('error', "splunk.ess", json["message"] || json);
                        }
                    	
                    	// Resubmit the search
                    	var module = moduleReference;
                    	
                    	// Find the search to dispatch
                    	while (module.getContext().get("search").isJobDispatched()) {
                            module = module.parent;
                        }
                    	
                    	// Push the content in order to re-submit the search
                        module.pushContextToChildren();
                    	
                    } else {
                        messenger.send('error', "splunk.ess", json["message"] || json);
                    }
                },
                'dataType': 'json'
            });
            return false;
        } 
        
        // If we're going to fail, fail fast and fail loud. 
        catch(e) {
            var messenger = Splunk.Messenger.System.getInstance();
            messenger.send('error', "splunk.ess", "an unexpected error occurred -- " + e);
        }
        
        return false;
    }
});