Splunk.Module.SOLNSearch = $.klass(Splunk.Module, {
	initialize: function($super, container) {
		$super(container);
		this.childEnforcement = Splunk.Module.ALWAYS_REQUIRE;
		
		this.logger = Splunk.Logger.getLogger("SOLNSearch.js");
		this.messenger = Splunk.Messenger.System.getInstance();
	},

	/**
	 * Passes a Context object to its children where the search instance 
	 * has been modified. Specifically the search string will be changed 
	 * to match the string defined in the view configuration and get 
	 * $blah$ substitutd from appsVars.
	 */   
	getModifiedContext: function(context) {
		if (!context) {
		context = this.getContext();
		}
		var search  = context.get("search");
		var searchString = this._params['search'];
		search.abandonJob();
		searchString = SOLN.replaceVariables(searchString, context);
		
		search.setBaseSearch(searchString);
		search.setPostProcess("");
		context.set("search", search);
		return context;
	},
	resetUI: function() {}
});
