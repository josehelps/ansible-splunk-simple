Splunk.Module.SOLNTextInput = $.klass(Splunk.Module, {
	initialize: function($super, container) {
		$super(container);
		//Set up internal variables
		this.displayField = this.getParam("displayField");
		this.varName = this.getParam("varName");
		$(this.container).attr("style",this.getParam("style"));
		this.label = this.getParam("label") ? this.getParam("label") : "";
		this.defaultValue = this.getParam("default") ? this.getParam("default") : "";
		this.template = this.getParam("template");
		this.$tiElem = $("input.SOLNTextInput",this.container);

		$(".SOLNTextInputLabel",this.container).html(this.label);

		this.firstLoad = true;
		this.stickyValue = SOLN.pullSelection(this.varName);
		
		//Allow context propagation from change of text input, note anonymous to remove the event from being regarded as an explicit context
		this.$tiElem.change(function() {this.pushContextToChildren();}.bind(this));
	},
	onContextChange: function() {
		//Set to url or stored value if available
		if (this.firstLoad) {
			var context = this.getContext();
			if (SOLN.getVariableValue(this.varName, context)) {
				//Set to the value in the context if it exists and this is the first load
				this.$tiElem.val(SOLN.getVariableValue(this.varName, context));
			}
			else if (this.stickyValue) {
				//Set the value to the previously selected if it exists
				this.$tiElem.val(this.stickyValue);
			}
			else {
				//If all else fails, set to default
				this.$tiElem.val(this.defaultValue);
			}
			this.firstLoad = false;
		}
	},
	getModifiedContext: function() {
		var context = this.getContext();
		var value = this.$tiElem.val();
		
		//Handle the sticky value
		this.stickyValue = value;
		SOLN.stickSelection(this.varName, this.stickyValue);
		
		if (value !== "") {
			value = this.template.replace(/\$text\$/g, value);
		}
		
		SOLN.storeVariable(this.varName, null, value, context);

		return context;
	},
	resetUI: function() {} //Just so splunk stops bitching at me
});
