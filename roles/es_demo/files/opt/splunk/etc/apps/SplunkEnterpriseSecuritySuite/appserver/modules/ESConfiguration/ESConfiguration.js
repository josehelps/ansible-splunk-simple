/**
 * Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
 */

Splunk.Module.ESConfiguration = $.klass(Splunk.Module, {
    initialize: function($super,container) {
        var retVal = $super(container);
        
        return retVal;
    }, 
    handleSubmitCallback: function() {
    	var messenger = Splunk.Messenger.System.getInstance();
    	messenger.send('info', "splunk.ess", "Message test!!!");
    	
    }
});

//SOLNESS-1794
$(document).ready(function() {
	if( $.browser.msie && $('.ESConfiguration').length > 0 ){
		$('.ESConfiguration').hide().show();
	}
});
