Splunk.Module.SOLNNullSwapper = $.klass(Splunk.Module.DispatchingModule, {

	initialize: function($super, container) {
		$super(container);
        this.logger = Splunk.Logger.getLogger("SOLNSearchSwapper.js");
        this.messenger = Splunk.Messenger.System.getInstance();
		this.searchParam = this.getParam("search");
		this.useSVUSub = this.getParam('useSVUSub', null);
		this.useSOLNSub = Splunk.util.normalizeBoolean(this.getParam('useSOLNSub'));
		this.lookupSavedSearch = Splunk.util.normalizeBoolean(this.getParam('lookupSavedSearch'));
		this.lookupSavedSearchNameSpace = this.getParam('lookupSavedSearchNameSpace', Splunk.util.getCurrentApp());
		if (this.useSVUSub && this.useSOLNSub) {
			console.log("Both sideview substitution and SOLN appVars substitution used, this may cause unexpected results as only SVU will be used..."); 
		}
		this.doneUpstream = false;
		this.override = false;
	},


	onContextChange: function() {
		var context = this.getContext();
		if (context.get("search").job.isDone()) {
			this.getResults();
		} else {
			this.doneUpstream = false;
		}
	},

	getModifiedContext: function(context) {
		/*jsl:ignore*/
		/* When non-explicit push context to children are called they call getModifiedContext with no arguments, so it is always best
		 * to call getContext at the beginning of getModifiedContext unless you intend to do something crazy fancy (which we don't).
		 * 
		 * Thus, ignoring the content argument is acceptable.
		 */
		var context = this.getContext();
		/*jsl:end*/
		if (this.doneUpstream) {
			this.setChildContextFreshness(false);
			if (this.override) {
				var targetSearch = this.searchParam;
				var lookupSearch;
				var search = context.get('search');
				search.job.setAsAutoCancellable(true);
				search.abandonJob();
				if (this.useSVUSub !== null) {
					Sideview.utils.setStandardTimeRangeKeys(context);
					Sideview.utils.setStandardJobKeys(context);
					targetSearch = Sideview.utils.replaceTokensFromContext(targetSearch, context);
					console.log(("Base search '%s' returned no results, swapping with '%t'").replace('%s',search.getBaseSearch()).replace('%t',targetSearch));
				} else if (this.useSOLNSub) {
					targetSearch = SOLN.replaceVariables(this.searchParam, context);
					console.log(("Base search '%s' returned no results, swapping with '%t'").replace('%s',search.getBaseSearch()).replace('%t',targetSearch));
					if (this.lookupSavedSearch) {
						lookupSearch = SOLN.lookupSavedSearch(targetSearch, this.lookupSavedSearchNameSpace,context);
						if ( lookupSearch !== null && lookupSearch.length > 0 ) {
							targetSearch = lookupSearch;
						} else {
							//Disabling the inline-messaging until we work around the first context push by "autoRun" that starts the module with empty context.
							//this.displayInlineErrorMessage((this.moduleType + " - Configuration error - unable to find a saved search called '%s'.").replace('%s', searchParam));
							this.logger.error((this.moduleType + " - Configuration error - unable to find a saved search called '%s'.").replace('%s', SOLN.replaceVariables(this.searchParam, context)));
						}
						
					}
				} else if (this.searchParam) {
					console.log(("Base search '%s' returned no results, swapping with '%t'").replace('%s',search.getBaseSearch()).replace('%t',this.searchParam));
					if (!this.lookupSavedSearch) {
						targetSearch = this.searchParam;
					} else {
						lookupSearch = SOLN.lookupSavedSearch(this.searchParam,this.lookupSavedSearchNameSpace,context);
						if ( lookupSearch !== null && lookupSearch.length > 0 ) {
							targetSearch = lookupSearch;
						} else {
							//Disabling the inline-messaging until we work around the first context push by "autoRun" that starts the module with empty context.
							//this.displayInlineErrorMessage((this.moduleType + " - Configuration error - unable to find a saved search called '%s'.").replace('%s', searchParam));
							this.logger.error((this.moduleType + " - Configuration error - unable to find a saved search called '%s'.").replace('%s', this.searchParam));
						}
					}
				}
				search.setBaseSearch(targetSearch);
				search.setPostProcess("");
				context.set('search', search);
			}
			return context;
		}
		return context;
	},
	
	onJobDone: function() {
		this.getResults();
	},

	getResults: function($super) {
		this.doneUpstream = true;
		return $super();
	},

	getResultURL: function() {
		var context = this.getContext();
		var params = {};
		var search  = context.get("search");
		params['search'] = search.getPostProcess() || "";
		params['outputMode'] = "json";
		var url = search.getUrl("results");
		return url + "?" + Splunk.util.propToQueryString(params);
	},  

	resetUI: function() {
	}, 

	onRendered: function() {
	}, 

	isReadyForContextPush: function($super) {
		if (!(this.doneUpstream)) {
			return Splunk.Module.DEFER;
		}
		return $super();
	},

	pushContextToChildren: function($super, explicitContext) {
		this.withEachDescendant(function(module) {
			module.dispatchAlreadyInProgress = false;
		});
		return $super(explicitContext);
	},

	renderResults: function(jsonRsp) {
		if (!jsonRsp) {
			this.override = true;
		}
		else {
			var jresults = SOLN.parseResults(jsonRsp);
			if (jresults.length>=1) {
				this.override = false;
			} else {
				this.override = true;
			}
		}
		this.doneUpstream = true;

		this.onRendered();
		this.pushContextToChildren();
	}
});
