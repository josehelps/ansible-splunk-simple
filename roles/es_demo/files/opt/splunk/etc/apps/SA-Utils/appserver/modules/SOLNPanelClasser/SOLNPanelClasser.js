Splunk.Module.SOLNPanelClasser = $.klass(Splunk.Module, {
	initialize: function($super, container) {
		$super(container);
		//Set up internal variables
		this.classList = this.getParam("class") ? this.getParam("class").split(",") : [];
		this.$parentPanel = $(this.container).parent().parent().parent();
	},
	onContextChange: function() {
		//Take the param "class" and add the class to the parent object while substituting SOLN vars
		if (this.classList.length) {
			var context = this.getContext();
			for (var ii=0;ii<this.classList.length; ii++) {
				this.$parentPanel.addClass(SOLN.replaceVariables(this.classList[ii], context));
			}
		}
	},
	resetUI: function() {} //Just so splunk stops bitching at me
});
