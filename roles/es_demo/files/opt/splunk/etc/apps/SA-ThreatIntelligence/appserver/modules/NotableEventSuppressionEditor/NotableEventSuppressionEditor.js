/**
 * Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
 */

Splunk.Module.NotableEventSuppressionEditor = $.klass(Splunk.Module, {
	initialize: function($super,container) {
	var retVal = $super(container);

	// Get a reference to the form
	var formElement = $('form', this.container);

	// Get the name of the view to redirect to
	var redirect = this.getParam('view_after_saving');

	// Assign a redirect to the cancel button
	$('#cancel_button').click( function() { var app = $('#app', formElement).attr('value'); document.location = Splunk.util.make_url("/app/" + app + "/" + redirect); } );

	// Update the form call with an Ajax request submission
	formElement.submit(function(e) {

		// Stop of the form does not validate
		if ( formElement.validationEngine('validate') === false ){
			alert("The notable event suppression is invalid, please correct the errors and try again");
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


/*
 *  Do whatever you want with it. I don't care
 *  But don't fotget to give us some credit. (Apache License)
 *  - Tanin Na Nakorn
 *  - Sergiu Rata
 *  - Nilobol Ariyamongkollert
 */
(function($){
    $.fn.extend({         
        //pass the options variable to the function
        default_text: function(msg, opts) {
			
			if (opts == undefined) { opts = {}; }
			
            var defaultTextClassName = opts.defaultClass !== null ? opts.defaultClass : "jquery_default_text";
            var defaultIdSuffix = opts.defaultIdSuffix !== null ? opts.defaultIdSuffix : "_default_text";
			

            return this.each(function() {
                var real_obj = this;
				var default_obj = null;
				
				if ($('#' + $(this)[0].id + defaultIdSuffix).length === 0) {
					default_obj = $(this).clone();
					var real_offset = $(real_obj).offset();
					if ($(real_obj).parent().css('position') === "")
					{
						$(real_obj).parent().css('position','relative');
					}
					$(default_obj).css('position','absolute');
					$(default_obj).offset({ top: real_offset.top-1, left: real_offset.left-1});
					$(default_obj).css('z-index','-100');
					$(default_obj).attr('tabindex','-1');
					$(real_obj).css('z-index','0');

					$(default_obj).css('display',$(real_obj).css('display'))
					.attr('name',$(real_obj).attr('name')+defaultIdSuffix);
					
					$(default_obj).insertBefore(this);
					$(default_obj).val(msg).addClass(defaultTextClassName).attr('id', $(this)[0].id + defaultIdSuffix);
					
					real_obj.show_default_text = function() {
						
						this.save_background = $(real_obj).css('background-color');
						this.save_border = $(real_obj).css('border-color');
						this.save_background_image = $(real_obj).css('background-image');
						this.save_background_repeat = $(real_obj).css('background-repeat');
						
						$(this).css('background-color','transparent');
						$(this).css('border-color','transparent');
						$(this).css('background-image','url("data:image/gif;base64,R0lGODlhAQABAPAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==")');
						$(this).css('background-repeat','repeat');
					};
					
					real_obj.hide_default_text = function() {
						$(this).css('background-color',real_obj.save_background);
						$(this).css('border-color',real_obj.save_border);
						$(this).css('background-image',real_obj.save_background_image);
						$(this).css('background-repeat',real_obj.save_background_repeat);
					};
			
					if ($(real_obj).val() === "") {
	                    real_obj.show_default_text();
	                } else {
						real_obj.hide_default_text();
	                }
	                
	                var defaultClickHandler = function() {
						
							if ($(real_obj).css('background-color') == 'transparent') {
								real_obj.hide_default_text();
							}
						
	                };
	
	                $(real_obj).focus(defaultClickHandler);
					

	                $(real_obj).blur(function() {
				
		                    if ($(real_obj).val() === "") {
		                        real_obj.show_default_text();
							}
	                });
					
				} else
				{
					$('#' + $(this)[0].id + defaultIdSuffix).val(msg);
				}
                
                
            });
        }        
    });    
})(jQuery);