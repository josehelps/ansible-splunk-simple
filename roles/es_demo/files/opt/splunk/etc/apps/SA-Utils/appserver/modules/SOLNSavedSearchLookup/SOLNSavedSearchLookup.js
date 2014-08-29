Splunk.Module.SOLNSavedSearchLookup = $.klass(Splunk.Module, {
	initialize : function($super, container) {
		$super(container);
		this.childEnforcement = Splunk.Module.ALWAYS_REQUIRE;
		this.logger = Splunk.Logger.getLogger("SOLNSavedSearchLookupLookup.js");
		this.messenger = Splunk.Messenger.System.getInstance();
	},

	getModifiedContext : function() {
		var context = this.getContext();
		var search = context.get('search');
		var searchParam = this.getParam('savedSearch');
		var nameSpace = this.getParam('nameSpace', Splunk.util.getCurrentApp());
		var postProcessParam = this.getParam('setPostProcess', null);
		var targetSearch = null;
		searchParam = SOLN.replaceVariables(searchParam, context);
		search.job.setAsAutoCancellable(true);
		search.abandonJob();
		targetSearch = SOLN.lookupSavedSearch(searchParam,nameSpace,context);
		if ( targetSearch !== null && targetSearch.length > 0 ) {
				if ( postProcessParam !== null) {
					search.setPostProcess(targetSearch);
					
				} else {
					search.setBaseSearch(targetSearch);
					search.setPostProcess('');
				}
				context.set("search", search);
		} else {
			//Disabling the inline-messaging until we work around the first context push by "autoRun" that starts the module with empty context.
			//this.displayInlineErrorMessage((this.moduleType + " - Configuration error - unable to find a saved search called '%s'.").replace('%s', searchParam));
			this.logger.error((this.moduleType + " - Configuration error - unable to find a saved search called '%s'.").replace('%s', searchParam));
		}
		return context;
	},
	
	resetUI: function() {}
});
