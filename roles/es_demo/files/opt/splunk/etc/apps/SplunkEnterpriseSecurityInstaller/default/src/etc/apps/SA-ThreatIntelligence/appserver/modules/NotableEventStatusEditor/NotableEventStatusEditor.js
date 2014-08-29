/**
 * Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
 */

Splunk.Module.NotableEventStatusEditor = $.klass(Splunk.Module, {
    initialize: function($super,container) {
        var retVal = $super(container);
        
        // Get a reference to the form
        var formElement = $('form', this.container);
        
        // Get the name of the view to redirect to
        var redirect = this.getParam('view_after_saving');
        
        // Toggle the placeholder
        $('#checkbox-is_default').click( function() {
        	
        	if( $('#checkbox-is_default').is(':checked') ){
        		$('#item-is_enabled_placeholder').show();
        		$('#item-is_enabled').hide();
        		$('#item-is_end_placeholder').show();
        		$('#item-is_end').hide();
        	}
        	else{
        		$('#item-is_enabled_placeholder').hide();
        		$('#item-is_enabled').show();
        		$('#item-is_end_placeholder').hide();
        		$('#item-is_end').show();
        	}
        	
        } );
        
        // Assign a redirect to the cancel button
        $('#cancel_button').click( function() { var app = $('#app', formElement).attr('value'); document.location = Splunk.util.make_url("/app/" + app + "/" + redirect); } );
        
        // Update the form call with an Ajax request submission
        formElement.submit(function(e) {
        	
        	// Stop of the form does not validate
        	if ( formElement.validationEngine('validate') === false ){
        		alert("The event status is invalid, please correct the errors and try again");
        		return false;
        	}
        	
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
                        	messenger.send('info', "splunk.ess", json["message"]);
                        	
                        	// Set the title of the button such that the user recognizes that the item has been saved
                        	$('#save_button').text("Saved!");
                        	
                        	// Get the app to redirect to
                        	var app = $('#app', formElement).attr('value');
                        	
                        	// Redirect the user
                            document.location = Splunk.util.make_url("/app/" + app + "/" + redirect);
                        	
                        // If it was unsuccessful, then print an error message accordingly
                        } else {
                            messenger.send('error', "splunk.ess", json["message"]);
                            
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
    	messenger.send('info', "splunk.ess", "Submitted edits!!!");
    	
    }
});