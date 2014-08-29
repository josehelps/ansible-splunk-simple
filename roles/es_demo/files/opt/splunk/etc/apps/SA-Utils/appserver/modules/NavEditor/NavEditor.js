/**
 * Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
 */

Splunk.Module.NavEditor = $.klass(Splunk.Module, {
    initialize: function($super,container) {
        var retVal = $super(container);
        
        // Get a reference to the form
        var formElement = $('form', this.container);
        
        // Update the form call with an Ajax request submission
        formElement.submit(function(e) {
        	
        	// Initiate the Ajax request
            try {
                $(this).ajaxSubmit({
                	
                	// Upon the successful processing of the Ajax request, evaluate the response to determine if the status was created
                    'success': function(json) {
                		var messenger = Splunk.Messenger.System.getInstance();
                		
                		// If successful, print a message noting that it was successful
                        if (json["success"]) {
                        	
                        	// Print a message noting that the change was successfully made
                        	messenger.send('info', "splunk.SA-Utils", json["message"]);
                        	
                        	// Refresh the page so that the new navigation appears
                        	location.reload();
                        	
                        // If it was unsuccessful, then print an error message accordingly
                        } else {
                            messenger.send('error', "splunk.SA-Utils", _('ERROR - ') + json["message"] || json);
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
    	messenger.send('info', "splunk.SA-Utils", "Action succeeded");
    	
    }
});