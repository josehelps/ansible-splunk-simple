Splunk.Module.SOLNLinkToggle = $.klass(Splunk.Module, {
	initialize: function($super, container) {
		$super(container);
		//Set up internal variables
		this.varName = this.getParam("varName");
		$(this.container).attr("style",this.getParam("style"));
		this.labels = this.getParam("labels").split(",");
		this.values = this.getParam("values").split(",");
		if (this.labels.length !== 2) {
			console.log("[" + this.moduleId + "] misconfigured parameter labels, must be csv of length 2");
			this.labels = ["error in " + this.moduleId,"error in " + this.moduleId];
		}
		if (this.values.length !== 2) {
			console.log("[" + this.moduleId + "] misconfigured parameter values, must be csv of length 2");
			this.values = ["error in " + this.moduleId,"error in " + this.moduleId];
		}
		this.$aElem = $("a.SOLNLinkToggle",this.container);

		this.firstLoad = true;
		this.curIndex = 0;
		this.stickyValue = SOLN.pullSelection(this.varName);
		
		//Allow context propagation from click of the link
		this.$aElem.click(function() {this.onLinkClick();}.bind(this));
	},
	onContextChange: function() {
		var context = this.getContext();
		//Set to url or stored value if available
		if (this.firstLoad) {
			var val;
			if (SOLN.getVariableValue(this.varName, context)) {
				//Set to the value in the context if it exists and this is the first load
				val = SOLN.getVariableValue(this.varName, context);
				if (val === this.values[0]) {
					//Note that cur index refers to the index of the current label in context which is the opposite of the current value
					this.curIndex = 1;
					this.curValue = this.values[0];
				}
				else {
					this.curIndex = 0;
					this.curValue = this.values[1];
				}
			}
			else if (this.stickyValue) {
				//Set the value to the previously selected if it exists
				val = this.stickyValue;
				if (val === this.values[0]) {
					//Note that cur index refers to the index of the current label in context which is the opposite of the current value
					this.curIndex = 1;
					this.curValue = this.values[0];
				}
				else {
					this.curIndex = 0;
					this.curValue = this.values[1];
				}
			}
			else {
				//If all else fails, set to default
				this.curIndex = 0;
				this.curValue = this.values[1];
			}
			this.firstLoad = false;
		}
		this.$aElem.text(SOLN.replaceVariables(this.labels[this.curIndex], context));
	},
	getModifiedContext: function() {
		var context = this.getContext();
		var value = this.curValue;
		
		//Handle the sticky value
		this.stickyValue = value;
		SOLN.stickSelection(this.varName, this.stickyValue);
		//Store the var
		SOLN.storeVariable(this.varName, null, value, context);

		return context;
	},
	onLinkClick: function() {
		//Swap out and push context
		var context = this.getContext();
		if (this.curIndex === 1) {
			//Note that cur index refers to the index of the current label in context which is the opposite of the current value
			this.curIndex = 0;
			this.curValue = this.values[1];
		}
		else {
			this.curIndex = 1;
			this.curValue = this.values[0];
		}
		this.$aElem.text(SOLN.replaceVariables(this.labels[this.curIndex], context));
		this.pushContextToChildren();
	},
	resetUI: function() {} //Just so splunk stops bitching at me
});
