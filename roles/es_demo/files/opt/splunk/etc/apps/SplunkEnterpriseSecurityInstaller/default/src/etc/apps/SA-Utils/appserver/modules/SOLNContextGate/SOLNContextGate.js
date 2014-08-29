Splunk.Module.SOLNContextGate = $.klass(Splunk.Module, {
	initialize: function($super, container) {
		$super(container);
		this.key = this.getParam("key");
		if (this.key) {
			this.allowAll = false;
		}
		else {
			this.allowAll = true;
		}
		this.variable = null;
		if (this.getParam("default_state") === "closed") {
			this.gate = Splunk.Module.DEFER;
		}
		else {
			this.gate = Splunk.Module.CONTINUE;
		}
		$(document).bind('openContextGate', this.onOpenContextGate.bind(this));
	},
	onOpenContextGate: function(event, eventkey, eventvar) {
		if (this.allowAll || this.key === eventkey) {
			this.gate = Splunk.Module.CONTINUE;
			var context = this.getContext();
			if (this.key && (eventvar!==null)) {
				SOLN.storeVariable(this.key, null, eventvar, context);
				this.variable = eventvar;
			}
			this.pushContextToChildren(context);
		}
	},
	isReadyForContextPush: function() {
		return this.gate;
	},
	getModifiedContext: function() {
		var context = this.getContext();
		if (this.variable !== null) {
			SOLN.storeVariable(this.key, null, this.variable, context);
		}
		return context;
	},
	_fireDispatchSuccessHandler: function($super,runningSearch) {
		this.open = true;
		var retVal = $super(runningSearch);
		this.open = this.allowSoftSubmit;
		return retVal;
	},
	resetUI: function() {} //just so splunk stops bitching at me
});
