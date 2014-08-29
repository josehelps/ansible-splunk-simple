/**
 * Customize the message module so it wont constantly be telling the user 
 * things that they dont care about and things that might alarm them.
 */
if (Splunk.Module.Message) {
    Splunk.Module.Message= $.klass(Splunk.Module.Message, {
        getHTMLTransform: function($super){
            var argh = [
                {contains:"Unknown parameter 'running_message'", level:"error"}
            ];

            // Get the messages list from the appropriate variable (depending on whether we are on 4.2 or 4.3)
            if( typeof(this.messages) != "undefined" ){
            	messages = this.messages; // 4.2
            }
            else{
            	messages = this.displayedMessages; // 4.3 or higher
            }
            
            // Remove the messages that match the filter
            for (var i=messages.length-1; i>=0; i--){
                var message = messages[i];
                for (var j=0,jLen=argh.length;j<jLen;j++) {
                    if ((message.content.indexOf(argh[j]["contains"])!=-1) && (message.level == argh[j]["level"])) {
                        messages.splice(i,1);
                        break;
                    }
                }
            }
            return $super();
        }
    });
}