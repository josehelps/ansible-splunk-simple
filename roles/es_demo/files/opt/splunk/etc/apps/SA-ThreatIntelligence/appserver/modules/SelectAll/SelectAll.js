Splunk.namespace("Module");

/**
 * 
 */

Splunk.Module.SelectAll = $.klass(Splunk.Module, {
    initialize: function($super, container){
        $super(container);
        $(".selectAll", this.container).click(this.selectAll.bind(this));
        $(".unSelectAll", this.container).click(this.unSelectAll.bind(this));
    },
    selectAll: function(evt) {
    	
    	// Get the search from the context so that we can determine if it is finalized
    	var context = this.getContext();
    	var search = context.get("search");
    	
    	// Don't show the log review popup if the search is not paused and not finalized since it will keep clearing the checkboxes (SOLNESS-787)
    	if( this.getParam('running_message') && !search.job.isFinalized() && !search.job.isDone() ) {
    		alert( this.getParam('running_message') );
    		return false;
    	}
    	
    	$(this.getParam('selector')).attr("checked", "true");
    	return false;
    },
    unSelectAll: function(evt) {
    	$(this.getParam('selector')).removeAttr("checked");
    	return false;
    }
});