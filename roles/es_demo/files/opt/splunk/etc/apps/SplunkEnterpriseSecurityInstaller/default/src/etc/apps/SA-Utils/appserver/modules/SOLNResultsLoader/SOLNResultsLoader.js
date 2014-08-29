Splunk.Module.SOLNResultsLoader = $.klass(Splunk.Module.DispatchingModule, {
	initialize: function($super, container) {
		$super(container);
		//Set up internal variables
		this.rowLimit = this.getParam("rowLimit");
		this.displayName = this.getParam("displayName");
		this.resultSet = [];
		
		//Context flow gates
		this.doneUpstream = false;
		this.gettingResults = false;
	},
	onContextChange: function() {
		var context = this.getContext();
		if (context.get("search").job.isDone()) {
			this.getResults();
		} else {
			this.doneUpstream = false;
		}
	},
	onJobDone: function(event) {
		this.getResults();
	},
	requiresDispatch: function($super,search) {
		return $super(search);
	},
	getResultURL: function() {
		var context = this.getContext();
		var params = {};
		var search  = context.get("search");
		params['search'] = search.getPostProcess() || "";
		params['outputMode'] = "json";
		params['count'] = this.rowLimit;
		var url = search.getUrl("results");
		return url + "?" + Splunk.util.propToQueryString(params);
	},
	getResults: function($super) {
		this.doneUpstream = true;
		this.gettingResults = true;
		return $super();
	},
	renderResults: function(jsonRsp) {
		var data = SOLN.parseResults(jsonRsp);
		if (data.length === 0) {
			console.log("WARNING: [SOLNResultsLoader] [" + this.moduleId + "] no results returned, nothing will be set in context.");
			//Reset the done upstream tag be cause we received nothing therefore upstairs needs an adjustment
			this.doneUpstream = false;
		}

		this.resultSet = data;

		this.gettingResults = false;
		this.pushContextToChildren();
	},
	getModifiedContext: function() {
		var context = this.getContext();
		var search  = context.get("search");
		//Get the values from results
		if (this.doneUpstream && !(this.gettingResults)) {
			var data = this.resultSet;
			var fields = Object.keys(data[0]);
			for (var ii=0; ii<data.length; ii++) {
				var row = data[ii];
				var rowName = this.displayName + "[" + String(ii) + "]";
				for (var jj=0; jj<fields.length; jj++) {
					var field = fields[jj];
					SOLN.storeVariable(rowName, field, row[field], context);
				}
			}
			return context;
		}
		else {
			this.setChildContextFreshness(false);
			return context;
		}
	},
	requiresTransformedResults: function() {
		return true;
	},
	onBeforeJobDispatched: function(search) {
		search.setMinimumStatusBuckets(1);
	},
	pushContextToChildren: function($super, explicitContext) {
		this.withEachDescendant(function(module) {
			module.dispatchAlreadyInProgress = false;
		});
		return $super(explicitContext);
	},
	isReadyForContextPush: function($super) {
		if (!(this.doneUpstream)) {
			return Splunk.Module.DEFER;
		}
		if (this.gettingResults) {
			return Splunk.Module.DEFER;
		}
		return $super();
	},
	resetUI: function() {} //Just so splunk stops bitching at me
});
