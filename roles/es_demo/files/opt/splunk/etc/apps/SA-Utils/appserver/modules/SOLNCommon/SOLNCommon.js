var SOLN = {
	reservedTokens: ["search","search.earliest","search.latest","search.timerange","search.baseSearch","search.postProcess","search.sid"],
	getReservedTokenValue: function(token, context) {
		/** 
		*This function takes in a reserved token and returns its value, which is uniquely obtained
		*per reserved token.
		*ARGS:
		*	token: a string contained in the reservedTokens array.
		*RETURN:
		*	string of the value of the token
		*/
		
		//Debated on this for a while, technically we could taken the index from the inArray call and 
		//have an array of functions that contain the accessors for each special key, but that is a bit 
		//hard for the user to read. If this routine is determined to be too slow, then by all means we 
		//should change it to that and make this function internal only. 
		var search = context.get("search");
		if (search) {
			if (token == "search") {
				return (search._baseSearch + " " + search._postProcess);
			} 
			else if (token == "search.earliest") {
				return search._range.getEarliestTimeTerms();
			}
			else if (token == "search.latest") {
				return search._range.getLatestTimeTerms();
			}
			else if (token == "search.timerange") {
				return search._range.toConciseString();
			}
			else if (token == "search.baseSearch") {
				return search._baseSearch;
			}
			else if (token == "search.postProcess") {
				return search._postProcess;
			}
			else if (token == "search.sid") {
				return search.job.getSID();
			}
			else {
				console.log("WARNING: SOLN was asked to find value for reserved token that is unreserved, empty string will be sub'ed for token:" + token);
				return "";
			}
		}
		console.log("WARNING: SOLN was asked to find value for reserved token with no search in context, it will be replaced with empty string, token:" + token);
		return "";
	},
	clearVariables: function(str, default_str) {
		/** 
		*This function takes in a string and returns the same string with 
		*tokens replaced with default_str, which defaults to empty string
		*ARGS:
		*	str: a string with tokens such as $displayField.valueField$ to be replaced
		*	default_str: a string to replace tokens with defaults to empty string
		*RETURN:
		*	string with tokens replaced
		*/
		var replacementTokens = Splunk.util.discoverReplacementTokens(str);
		var replacer;
		if (default_str === null || default_str === undefined) {
			default_str = "";
		}
		var value = default_str;
		var token;
		
		for (var ii=0; ii<replacementTokens.length; ii++) {
			token = replacementTokens[ii];
			replacer = new RegExp("\\$" + this.escapeStringForRegExp(token) + "\\$");
			str = Splunk.util.replaceTokens(str, replacer, value);
		}
		return str;
	},
	replaceVariables: function(str, context) {
		/** 
		*This function takes in a string and returns the same string with 
		*context variables replaced both appVars, and splunk core vars.
		*Note that the search and search.* vars are special and handled specially,
		*no appVar or context key will ever be seen for a name of search or the special
		*search.* vars. 
		*ARGS:
		*	str: a string with tokens such as $displayField.valueField$ to be replaced
		*	context: an object containing the object of appvars variables, appVars
		*RETURN:
		*	string with tokens replaced
		*/
		var appVars = context.get("appVars");
		var replacementTokens = Splunk.util.discoverReplacementTokens(str);
		var replacer;
		var value;
		var token;
		
		if (appVars) {
			for (var ii=0; ii<replacementTokens.length; ii++) {
				token = replacementTokens[ii];
				if ($.inArray(token,this.reservedTokens) > -1) {
					replacer = new RegExp("\\$" + this.escapeStringForRegExp(token) + "\\$");
					value = this.getReservedTokenValue(token, context);
					str = Splunk.util.replaceTokens(str, replacer, value);
				}
				else if (appVars.hasOwnProperty(token)) {
					var variable = appVars[token];
					str = str.replace(variable.re, variable.val);
				}
				else if (context.has(token)) {
					replacer = new RegExp("\\$" + this.escapeStringForRegExp(token) + "\\$");
					value = context.get(token);
					str = Splunk.util.replaceTokens(str, replacer, value);
				}
			}
		}
		else {
			//No appVars just do the basic context key replacement
			for (var ij=0; ij<replacementTokens.length; ij++) {
				token = replacementTokens[ij];
				if ($.inArray(token,this.reservedTokens) > -1) {
					replacer = new RegExp("\\$" + this.escapeStringForRegExp(token) + "\\$");
					value = this.getReservedTokenValue(token, context);
					str = Splunk.util.replaceTokens(str, replacer, value);
				}
				else if (context.has(token)) {
					token = replacementTokens[ij];
					replacer = new RegExp("\\$" + this.escapeStringForRegExp(token) + "\\$");
					value = context.get(token);
					str = Splunk.util.replaceTokens(str, replacer, value);
				}
			}
		}
		return str;
	},
	storeVariable: function(displayField, valueField, value, context) {
		/** 
		*This function takes in data and a context and returns the context with the data
		*replaced as an appVar. 
		*ARGS:
		*	displayField: a string used as first part of the variable's token, the display name
		*	valueField: a string used as the second part of the variable's token, the value name.
		*	            if null only the displayField will be used to name the stored variable.
		*	value: the actual value of the variable to be stored
		*	context: the context object into which the variable is stored
		*RETURN:
		*	context with variable stored, note that even though this function returns context the context
			in the caller will already have been edited, it is not necessary to reassign it to itself. 
		*/
		var name;
		
		//Construct variable name, if no valueField just use display
		if (valueField) {
			name = displayField + "." + valueField;
		}
		else {
			name = displayField;
		}
		//Construct RegExp
		var re = new RegExp("\\$" + this.escapeStringForRegExp(name) + "\\$", "g");
		//Attach to context
		if (!context) {
			console.log("no context passed to store variable, nothing will be stored");
		}
		else {
			var appVars = context.get("appVars");
			if (!appVars) {
				appVars = {};
			}
			appVars[name] = {
				re: re,
				val: value
			};
			context.set("appVars",appVars);
			return context;
		}
	},
	getVariableValue: function(name, context) {
		/** 
		*This function takes in a variable's name and a context and returns the value of that variable 
		*from the context, if the variable does not exist it returns boolean false. appVar or context key.
		*ARGS:
		*	name: a string of the name of the variable
		*	context: the context object in which the variable is stored
		*RETURN:
		*	the variable's value or false if the variable does not exist, note that a variable 
		*	is always a string so it is safe to use in a condition for the variable's existence
		*/
		if (!context) {
			console.log("no context passed to get variable value, nothing to get");
			return false;
		}
		var appVars = context.get("appVars");
		
		if ($.inArray(name, this.reservedTokens) > -1) {
					var value = this.getReservedTokenValue(name, context);
					return value;
		}
		else if (appVars && appVars.hasOwnProperty(name)) {
			//We got a value so return it
			variable = appVars[name];
			return variable.val;
		}
		else if (context.has(name)) {
			return context.get(name);
		}
		else {
			//nothing there, return false
			return false;
		}
	},
	stickSelection: function(selectionName,selection) {
		/** 
		*This function takes in a name and a selection of any type and stores it to local storage
		*with store.js. Note that if a store with the same name exists it will be overwritten.
		*ARGS:
		*	selectionName: a string to name the selection in local storage
		*	selection: the object of any type to be stored under the selectionName
		*RETURN:
		*	true if successful false if unsuccessful (i.e. store.js not enabled)
		*/
		if (store.enabled) {
			store.set(selectionName, selection);
			return true;
		}
		else {
			console.log("Local storage is disabled, cannot store anything... sad face.");
			return false;
		}
	},
	pullSelection: function(selectionName) {
		/** 
		*This function takes in a name then pulls the value previously stored under that name
		*and returns it. This is done with store.js and will return null if the value does not 
		*exist or local storage is disabled
		*ARGS:
		*	selectionName: a string denoting the selection in local storage
		*RETURN:
		*	true if successful false if unsuccessful (i.e. store.js not enabled)
		*/
		if (store.enabled) {
			return store.get(selectionName);
		}
		else {
			console.log("Local storage is disabled, cannot retrieve anything... sad face.");
			return null;
		}
	},
	//##################################################################################################
	
	// GLOBAL JOB SUPPORT FUNCTIONS
	
	//##################################################################################################
	/**
	*The job registry contains information on how to access various search jobs, each key is a unique 
	*global job of the format:
	* {
	*	progress: float from 0.0 to 1.0 indicating "job done progress"
	*	url: a string at which the results of the job may be obtained (you must add post process and other params manually)
	* }
	*/
	jobRegistry: {}, 
	registerJobProgress: function(key, progress, sid) {
		/** 
		*This function takes in a key and a progress and updates the jobRegistry with the progress
		*ARGS:
		*	key: a key for the job in question
		*	progress: a float between 0 and 1.0 indicating the job's current progress
		*	sid: the sid fo the search job
		*RETURN:
		*	null
		*/
		if (this.jobRegistry.hasOwnProperty(key)) {
			//update the job registration
			this.jobRegistry[key].progress = progress;
			//set the job url to false to indicate it is in progress
			this.jobRegistry[key].url = false;
			this.jobRegistry[key].sid = sid;
		}
		else {
			//create the job registration if it does not exist
			this.jobRegistry[key] = {
				"progress" : progress,
				"url" : false,
				"sid": sid
			};
		}
	},
	getJobProgress: function(key) {
		/** 
		*This function takes in a key returns the job progress or 0 and logs an error if the job is not registered
		*ARGS:
		*	key: a key for the job in question
		*RETURN:
		*	the progress, or 0 if the job is not registered
		*/
		if (this.jobRegistry.hasOwnProperty(key)) {
			//return the progress from the job registration
			return this.jobRegistry[key].progress;
		}
		else {
			//Log Error return 0.0
			console.log("[SOLN GLOBAL] ERROR: progress was requested on a key that is not registered with SOLN, key:" + key);
			return 0.0;
		}
	},
	registerJobDone: function(key, url, sid) {
		/** 
		*This function takes in a key and a url and updates the jobRegistry with the done job's url (also sets progress to 1.0)
		*ARGS:
		*	key: a key for the job in question
		*	url: a url to the results for the keyed job
		*	sid: the sid fo the search job
		*RETURN:
		*	null
		*/
		if (this.jobRegistry.hasOwnProperty(key)) {
			//update the job registration
			this.jobRegistry[key].progress = 1.0;
			//set the job url
			this.jobRegistry[key].url = url;
			this.jobRegistry[key].sid = sid;
		}
		else {
			//create the job registration if it does not exist
			this.jobRegistry[key] = {
				"progress" : 1.0,
				"url" : url,
				"sid": sid
			};
		}
	},
	getSIDForKey: function(key) {
		/** 
		*This function takes in a key returns the sid of the job, false if there is no sid
		*ARGS:
		*	key: a key for the job in question
		*RETURN:
		*	sid or false
		*/
		if (this.jobRegistry.hasOwnProperty(key)) {
			//return the progress from the job registration
			return this.jobRegistry[key].sid ? this.jobRegistry[key].sid : false;
		}
		else {
			//Log Error return 0.0
			console.log("[SOLN GLOBAL] ERROR: sid was requested on a key that is not registered with SOLN, key:" + key);
			return false;
		}
	},
	isJobDone: function(key) {
		/** 
		*This function takes in a key returns true if the job is done, false otherwise
		*ARGS:
		*	key: a key for the job in question
		*RETURN:
		*	true if done, false otherwise
		*/
		if (this.jobRegistry.hasOwnProperty(key)) {
			if (this.jobRegistry[key].url) {
				return true;
			}
			else {
				return false;
			}
		}
		else {
			return false;
		}
	},
	//NOTE the following has been removed from service because results should be requested async, 
	//not hacked to be blocking here, use this as a template for your use and use the getJobResultURL method
	//
	//getResultsForJob: function(key, postProcess): {
	//	/** 
	//	*This function takes in a key returns the json results response of the job, it also applies the post process
	//	*if it is provided
	//	*ARGS:
	//	*	key: a key for the job in question
	//	*	postProcess: optional, a post process to be applied to the search if desired
	//	*RETURN:
	//	*	the JSON results response of the job if it is done, else returns false.
	//	*/
	//	if (this.isJobDone(key)) {
	//		var params = {};
	//		params['search'] = postProcess || "";
	//		params['outputMode'] = "json";
	//		var url = this.jobRegistry[key].url;
	//		url = url + "?" + Splunk.util.propToQueryString(params);
	//		$.get ...
	//	}
	//	else {
	//		return false;
	//	}
	//},
	getJobResultURL: function(key) {
		/** 
		*This function takes in a key returns the url for the results if it is done, else returns false.
		*ARGS:
		*	key: a key for the job in question
		*RETURN:
		*	the results url of the job if it is done, else returns false.
		*/
		if (this.isJobDone(key)) {
			return this.jobRegistry[key].url;
		}
		else {
			return false;
		}
	},
	//##################################################################################################
	
	// UTILITY FUNCTIONS
	
	//##################################################################################################
	escapeStringForSelector: function(str) {
		if (str) {
			return str.replace(/([ \\#;?&,.+*~':"!^$[\]()=>|\/@<%`{}])/g,'\\$1');
		}
		else {
			return str;
		}
	},
	escapeStringForRegExp: function(str) {
		return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
	},
	startswith: function(str,fragment) {
		return str.slice(0, fragment.length) == fragment;
	},
	lookupSavedSearch: function(name, nameSpace, context) {
		var ajaxResponse = "";
		var searchString = null;
		var relUri = Splunk.util.make_url('/lists/entities/admin/savedsearch/'+name);
		var targetArtifact = $.parseJSON($.ajax({
			url : (relUri+'?output_mode=json&namespace='+nameSpace),
			dataType : "json",
			async : false,
			success : function(data,textStatus) {
				ajaxResponse = textStatus;
			}
		}).responseText);
		if ( ajaxResponse == "success" && targetArtifact.length > 0 ) {
			if (targetArtifact[0].hasOwnProperty('search')) {
				searchString = targetArtifact[0]["search"];
				searchString = SOLN.replaceVariables(searchString, context);
			} else {
				console.log(("Lookup error - unable to find a field 'search' in saved search called '%s'. Namespace: '%n'. Context:").replace('%s', name).replace('%n', nameSpace),context);
			}
		} else {
			console.log(("Lookup error - unable to find a field 'search' in saved search called '%s'. Namespace: '%n'. Context:").replace('%s', name).replace('%n', nameSpace),context);
		}
		
		return searchString;
	},
	parseResults: function (results) {
		var returnedData = [];
		var splunkVersion = document.title.reverse().split(" -")[0].reverse().split(" ")[1];
		var data;
		if (typeof results === "string" && results.length !== 0){
			results = JSON.parse(results);
		}
		// Check splunk version for ACE or higher
		if (parseInt(splunkVersion.charAt(0), 10) >= 5) {
			if ( results.length === 0 ) {
				// Empty string returned, must be null, return an empty array
				returnedData = [];
			} else {
				// Results exist, so lets parse them.
				data = results;
				// Check to see if an array was created, then see if it's size is 1 and has a property of count
				if (data.length === 1) {
					if (data[0].hasOwnProperty('count')){
						// if there was only 1 result, and the count is set to 0 override it with a null array.
						// if splunk is set to do a |stats count and returns 0, it'll be a string, not an int.
						if (data[0].count === 0 && typeof(data[0].count) === "number" ) {
							console.log('Um, Yeah, Splunk says you have a result of "count = 0" - and it lies, this must be null.');
							returnedData = [];
						} else {
							// You have a |stats count in your search, but you returned more then 0 or isn't a number
							returnedData = data;
						}
					} else {
						returnedData = data;
					}
				} else {
					//  We parsed the results into an object, but there was either no array sent in the JSON, or multiples.
					//  We want to see if the element contains the elements for an error.
					if (data.hasOwnProperty('data') && data.hasOwnProperty('messages')) {
						if (data.data === null) {
							// printing the error to the console, making debuging a bit easier.
							console.log("Search returned with an error!", data.messages);
							returnedData = [];
						} else {
							// send back real data in-case the user actually had a field data and a field messages in the same search
							returnedData = data;
						}
					} else {
						returnedData = data;
					}
				}
			}
		} else {
			if ( results.length === 0 ) {
				returnedData = [];
			} else {
				data = results;
				returnedData = data;
			}
		}
		return returnedData;
	},
	getJobResults: function(context, count, offset) {
		if (count === null) {
			count = 10;
		}
		if (offset === null) {
			offset = 0;
		}
		
		var search = context.get('search');
		var urlLocation = search.getUrl('results');
		var params = {};
		params['search'] = search.getPostProcess() || "";
		params['count'] = count;
		params['offset'] = offset;
		params['outputMode'] = 'json';
	
		var targetArtifact = $.ajax({
			url : (urlLocation + '?' + Splunk.util.propToQueryString(params)),
			dataType : "json",
			async : false,
			success : function(data,textStatus) {
				targetArtifact = this.parseResults(data);
			}.bind(this),
			failure : function() {
				console.log(("Lookup error - unable to find '%s'.").replace('%s', urlLocation),context);
			}
		}).responseText;
		
		return targetArtifact;
	},
	/**
	*hello I'm splunk applications here with SOLNCommon!
	*are you tired of your freaking numbers having too many decimal places?
	*wish you didn't have to write custom code to round things for display purposes?
	*YOU NEED SOLNCOMMON!
	*now with SOLN.roundNumber you can get a number back rounded to any number of decimal places you want!
	*but wait I always want it to two places...
	*LOOK NO FURTHER, SOLN.roundNumber will default to 2 places if you don't tell it how to round just type:
	*roundedNumber = SOLN.roundNumber(num); 
	*and you're good to go!
	*/
	roundNumber: function(num, dec) {
		//Provide a dec to get it to a different rounding than 2
		if (dec === null || dec === undefined || !this.isNum(dec)) {
			dec = 2;
		}
		var result = Math.round(num*Math.pow(10,dec))/Math.pow(10,dec);
		return result;
	},
	/**
	*BUT WAIT THERE'S MORE! ever notice how checking whether or not things are
	*even numbers in the first place is a problem? Well not with your free gift of
	*SOLN.isNum! It always works in over 30 test cases of bad number coercion from
	*competitive brands!
	*/
	isNum: function(n) {
		return !isNaN(parseFloat(n)) && isFinite(n);
	},
	getModuleById: function(mid) {
		/** 
		*This function takes in a module id and returns to you the module, it is 
		*mainly for debugging purposes
		*ARGS:
		*	mid: a module id for a module on the page
		*RETURN:
		*	module object, watch out it is a ref you will edit the module unless you clone
		*	or false if module does not exist
		*/
		if (Splunk.Globals.ModuleLoader._modulesByID[mid]) {
			return Splunk.Globals.ModuleLoader._modulesByID[mid];
		}
		else {
			return false;
		}
		
	},
	getModulesByType: function(type) {
		/** 
		*This function takes in a module id and returns to you the module, it is 
		*mainly for debugging purposes
		*ARGS:
		*	type: a module type e.g. SimpleResultsTable
		*RETURN:
		*	array of module object, watch out it is a ref you will edit the module unless you clone
		*	or empty array if no modules of this type exist on the page
		*/
		mList = Splunk.Globals.ModuleLoader._modules;
		matches = [];
		var tmpType;
		
		for (var ii=0; ii<mList.length; ii++) {
			var tmpMod = mList[ii];
			if (this.startswith(tmpMod.moduleType,"Splunk.Module.")) {
				tmpType = tmpMod.moduleType.split(".")[2];
			}
			else {
				tmpType = tmpMod.moduleType;
			}
			if (tmpType == type) {
				matches.push(tmpMod);
			}
		}
		return matches;
	},
	//##################################################################################################
	
	// ANUBIS UTILITIES
	
	//##################################################################################################
	anubisWindow : "",
	keyListener: function(event) {
		if((event.which == '32') && event.ctrlKey && event.shiftKey)	// space == 32 
		{
			if (SOLN.anubisWindow === "" || SOLN.anubisWindow.closed || SOLN.anubisWindow.name == undefined) {
				SOLN.anubisWindow = window.open(Splunk.util.make_url("/custom/SA-Utils/anubis_service/" + Splunk.util.getCurrentApp() + "/show") + "?view=" + Splunk.util.getCurrentView(),"subWindow","HEIGHT=775,WIDTH=1400");
			}
			else {
				SOLN.anubisWindow.focus();
			}
		}
	}
};
//Event Bindings for SOLN Utilities
//Enable hotkeys
$(document).keydown( SOLN.keyListener );

Splunk.Module.SOLNCommon = $.klass(Splunk.Module, {
	initialize: function($super, container) {
		$super(container);
		console.log("loaded common tools into var SOLN");
		
		//Handle the Query String
		this.qsVars = Splunk.util.queryStringToProp(window.location.search);
	},
	getModifiedContext: function (context) {
		if (!context) {
			context = this.getContext();
		}
		for (var name in this.qsVars) {
			SOLN.storeVariable(name, null, this.qsVars[name], context);
		}
		return context;
	}
});

