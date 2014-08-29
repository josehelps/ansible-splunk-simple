/**
 * Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
 */

Splunk.Module.LogReviewConfig = $.klass(Splunk.Module, {
    initialize: function($super,container) {
        var retVal = $super(container);
        
        // Show/hide the length requirement depending on if the comment is required
        $('#checkbox-is_required', this.container).click( function() { 
        	if( $('#checkbox-is_required').is(':checked') ){
        		$('#minimum_comment_length').show();
        	}
        	else{
        		$('#minimum_comment_length').hide();	
        	}
        });
        
        // Get a reference to the form
        var formElement = $('form', this.container);
        
        // Update the form call with an Ajax request submission
        formElement.submit(function(e) {
        	
        	// Change the text on the save button to show we are doing something
        	$('#save_button').text("Saving...");
        	
        	// Initiate the Ajax request
            try {
                $(this).ajaxSubmit({
                	
                	// Upon the successful processing of the Ajax request, evaluate the response to determine if the status was created
                    'success': function(json) {
                		
                        var messenger = Splunk.Messenger.System.getInstance();
                		// If successful, print a message noting that it was successful
                        if (json["success"]) {
                        	
                        	// Print a message noting that the change was successfully made
                        	messenger.send('info', "splunk.SA-ThreatIntelligence", json["message"]);
                        	
                        	// Set the title of the button such that the user recognizes that the item has been saved
                        	$('#save_button').text("Saved!");
                        	
                        // If it was unsuccessful, then print an error message accordingly
                        } else {
                            messenger.send('error', "splunk.SA-ThreatIntelligence", _('ERROR - ') + json["message"] || json);
                            
                            $('#save_button').text("Save");
                        }
                    },
                    'dataType': 'json'
                });
                
            // The Ajax request failed, print an exception
            } catch(e) {
                alert(e);
            }

            return false;

        });
        
        return retVal;
    },
    
    handleSubmitCallback: function() {
    	var messenger = Splunk.Messenger.System.getInstance();
    	messenger.send('info', "splunk.SA-ThreatIntelligence", "Action succeeded");
    	
    }
});