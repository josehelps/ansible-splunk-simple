/**
 * Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
 */

Splunk.Module.NotableEventCreator = $.klass(Splunk.Module, {
	
	setHiddenFields: function() {
    	    	
		fields_not_to_add = ['title', 'severity', 'domain'];
	
		// If the URL has arguments, then parse them out and add them as hidden fields
		if( window.location.href.indexOf('?') >= 0 ){
			
			// Get the arguments from the URL
	    	var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
	    	
	    	var fields_added = 0;
	    	
	    	// Add each argument as a hidden form field
	    	for(var i = 0; i < hashes.length; i++){
	    		
	    		// Split the name and value
	    		hash = hashes[i].split('=');
	    		
	    		arg_name = hash[0];
	    		arg_value = decodeURIComponent(hash[1]);
	    		
	    		// Attach a hidden form field unless it is one of them that we already have on the form
	    		if( $.inArray(arg_name , fields_not_to_add) < 0 ){
	    			$('<input>').attr('type','hidden').attr('name', arg_name).attr('value', arg_value).appendTo('#notableEventEditorForm');
	    			
	    			fields_added = fields_added + 1;
	    		}
	    	}
	    	
	    	console.info("Added " + String(fields_added) + " hidden fields for variables to be associated with the event");
		}
	},
	
    initialize: function($super,container) {
        var retVal = $super(container);
        
        // Get a reference to the form
        var formElement = $('form', this.container);
        
    	// Get the name of the view to redirect to
    	var redirect = this.getParam('view_after_saving');
    	
    	// Assign a redirect to the cancel button
    	$('#cancel_button').click( function() { var app = $('#app', formElement).attr('value'); document.location = Splunk.util.make_url("/app/" + app + "/" + redirect); } );
    	
    	// Save off the fields we are going to send
    	Splunk.Module.NotableEventCreator.prototype.setHiddenFields();
    	
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
                        	messenger.send('info', "splunk.SA-ThreatIntelligence", json["message"]);
                        	
        					// Get the app to redirect to
        					var app = $('#app', formElement).attr('value');

        					// Redirect the user
        					document.location = Splunk.util.make_url("/app/" + app + "/" + redirect);
                        	
                        // If it was unsuccessful, then print an error message accordingly
                        } else {
                            messenger.send('error', "splunk.SA-ThreatIntelligence", _('ERROR - ') + json["message"] || json);
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