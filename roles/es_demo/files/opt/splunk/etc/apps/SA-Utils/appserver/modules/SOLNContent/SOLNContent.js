Splunk.Module.SOLNContent = $.klass(Splunk.Module, {
	initialize: function($super, container) {
		$super(container);
		this.content = this.getParam("content");
		$(this.container).attr("style",this.getParam("style"));
	},
	onContextChange: function(context) {
		if (!context) {
		context = this.getContext();
		}
		var dynamicContent = this.content;
		dynamicContent = SOLN.replaceVariables(dynamicContent, context);
		
		$(this.container).html(dynamicContent);
	},
	resetUI: function() {}
});
