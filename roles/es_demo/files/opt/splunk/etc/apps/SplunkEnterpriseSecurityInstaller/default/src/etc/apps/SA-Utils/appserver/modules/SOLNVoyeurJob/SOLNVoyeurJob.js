Splunk.Module.SOLNVoyeurJob = $.klass(Splunk.Module.DispatchingModule, {
	initialize: function($super, container) {
		$super(container);
		//Set up internal variable
		this.key = this.getParam("key");
	},
	onJobProgress: function(event, job) {
		var context = this.getContext();
		var search  = context.get("search");
		var sid = search.job.getSID();
		if (search.job.isRealTimeSearch()) {
			//well color me green and call SETI a real time job? nah we're not doing anything with this. 
			return;
		}
		//Send the progress to our overlord, SOLN
		SOLN.registerJobProgress(this.key, search.job.getDoneProgress(), sid);
		$(document).trigger("SOLNJobProgress",[this.key]);
	},
	onJobDone: function(event) {
		var context = this.getContext();
		var search  = context.get("search");
		var sid = search.job.getSID();
		var url = search.getUrl("results");
		//Send the url to our overlord, SOLN
		SOLN.registerJobDone(this.key, url, sid);
		$(document).trigger("SOLNJobDone",[this.key]);
	},
	renderResults: function() {
		//No result rendering required as we are just registering the way to get the results
		console.log("SOLNVoyeurJob does not render results it posts them up for others to enjoy!");
	},
	requiresTransformedResults: function() {
		return true;
	},
	resetUI: function() {} //Just so splunk stops bitching at me
});
