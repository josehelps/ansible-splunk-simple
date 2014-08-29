/**
 * Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
 */

Splunk.Module.NotableEventSuppressionList = $.klass(Splunk.Module, {
    initialize: function($super,container) {
        var retVal = $super(container);
        
        return retVal;
    }, 
    handleSubmitCallback: function() {
    	var messenger = Splunk.Messenger.System.getInstance();
    	messenger.send('info', "splunk.sa_threatintelligence", "Message test!!!");
    	
    }
});
