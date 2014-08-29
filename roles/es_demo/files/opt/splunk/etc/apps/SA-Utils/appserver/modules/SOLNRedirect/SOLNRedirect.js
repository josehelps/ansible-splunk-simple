Splunk.Module.SOLNRedirect = $.klass(Splunk.Module, {
	initialize: function($super, container) {
		$super(container);
		//Set up internal variables
		this.paramList = this.getParam("paramList") ? this.getParam("paramList").split(",") : [];
		this.renameList = this.getParam("renameList") ? this.getParam("renameList").split(",") : [];
		//Deal with the url according to rules in conf file
		this.url = this.getParam("url");
		if (this.url.slice(0, 1) == "/") {
			//This means we go to the same domain, but path is the url
			//window.location.origin only works on web-kit browsers adding more options.
			//this.location = window.location.origin + this.url;
			//this.location = window.location.protocol + "//" + window.location.hostname + ":" + window.location.port + "/" + this.url;
			this.location = window.location.protocol + "//" + window.location.host + Splunk.util.make_url(this.url);
		}
		else if (this.url.match(/^https?:/)) {
			//This means we go to a different domain
			this.location = this.url;
		}
		else {
			//this.location = window.location.origin + "/app/" + Splunk.util.getCurrentApp() + "/" + this.url;
			this.location = window.location.protocol + "//" + window.location.host + Splunk.util.make_url("/app/" + Splunk.util.getCurrentApp() + "/" + this.url);
		}
		//Deal with the link according to the conf file
		this.useLink = this.getParam("useLink") ? this.getParam("useLink") : false;
		if (this.useLink) {
			$(container).append($('<a class="soln-redirect-link" href="' + this.location + '">').text(this.useLink));
			this.$link = $(".soln-redirect-link", $(container));
		}
	},
	onContextChange: function() {
		//Handle the params and optionally do the redirect
		var names = this.paramList;
		var args = {};
		if (this.paramList.length) {
			var context = this.getContext();
			if (this.renameList.length) {
				if (this.renameList.length != this.paramList.length) {
					console.log("[SOLNRedirct] [" + this.moduleId + "] WARNING: rename list does not match param name list in legnth, will be ignored");
				}
				else {
					names = this.renameList;
				}
			}
			for (var ii=0;ii<names.length; ii++) {
				//add var if it exists otherwise warn
				if (SOLN.getVariableValue(this.paramList[ii], context)) {
					args[names[ii]] = SOLN.getVariableValue(this.paramList[ii], context);
				}
				else {
					console.log("[SOLNRedirct] [" + this.moduleId + "] WARNING: could not find var " + this.paramList[ii] + " as appVar nor context key, ignoring it.");
				}
			}
		}
		var redirect_url;
		if (Object.keys(args).length > 0) {
			redirect_url = this.location + "?" + Splunk.util.propToQueryString(args);
		}
		else {
			redirect_url = this.location;
		}
		if (this.useLink) {
			this.$link.attr("href",redirect_url);
		}
		else {
			window.location.href = redirect_url;
		}
	},
	resetUI: function() {} //Just so splunk stops bitching at me
});
