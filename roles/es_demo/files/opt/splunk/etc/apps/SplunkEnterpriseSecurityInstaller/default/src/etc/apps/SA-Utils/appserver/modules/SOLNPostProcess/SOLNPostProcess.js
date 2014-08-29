Splunk.Module.SOLNPostProcess = $.klass(Splunk.Module.DispatchingModule, {
	initialize: function($super, container) {
		$super(container);
		this.childEnforcement = Splunk.Module.ALWAYS_REQUIRE;
		this.doneUpstream = false;
	},
	getModifiedContext: function() {
		var context = this.getContext();
		var search  = context.get("search");
		var ppString = this.getParam('search');
		ppString = SOLN.replaceVariables(ppString, context);
		
		search.setPostProcess(ppString);
		context.set("search", search);
		return context;
	},
	requiresTransformedResults: function() {
		return true;
	},
	resetUI: function() {}
});
