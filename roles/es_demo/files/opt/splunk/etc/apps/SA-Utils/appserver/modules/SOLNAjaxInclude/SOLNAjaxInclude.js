Splunk.Module.SOLNAjaxInclude = $.klass(Splunk.Module, {
	initialize : function($super, container) {
		$super(container);
		$.ajaxSetup({ cache: false });
		this.url = this.getParam("url");
		var location;
		if (this.url.slice(0, 1) == "/") {
			//This means we go to the same domain, but path is the url
			location = window.location.protocol + "//" + window.location.host + this.url;
		}
		else if (this.url.match(/^https?:/)) {
			//This means we go to a different domain
			location = this.url;
		}
		else {
			//this.location = window.location.origin + "/app/" + Splunk.util.getCurrentApp() + "/" + this.url;
			location = window.location.protocol + "//" + window.location.host + "/app/" + Splunk.util.getCurrentApp() + "/" + this.url;
		}
		var params = {
			url: location,
			success: function(data) {
				$(this.container).html(data);
			}.bind(this),
			failure: function() {
				$(this.container).html("Could not GET content for url: " + location);
			}.bind(this)
		};
		//We do everything async
		$.ajax(params);
	},
	
	resetUI: function() {}
});
