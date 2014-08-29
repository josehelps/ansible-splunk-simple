require.config({
    paths: {
        text: '../app/SA-Utils/js/lib/text',
        console: '../app/SA-Utils/js/util/Console'
    }
});

define(['underscore', 'splunkjs/mvc', 'jquery', 'splunkjs/mvc/simplesplunkview', 'text!../app/SA-Utils/js/templates/KeyIndicatorResults.html', "css!../app/SA-Utils/css/KeyIndicator.css", "console"],
function(_, mvc, $, SimpleSplunkView, KeyIndicatorTemplate) {
    
    // Assign static variables that indicate the status of the associated search
    var stateNotStarted = 0;
    var stateDispatched = 1;
    var stateRendered = 2;
    var stateError = 3;
     
    // Define the custom view class
    var KeyIndicatorView = SimpleSplunkView.extend({
        className: "KeyIndicatorView",
        
        /**
         * Setup the defaults
         */
        defaults: {
			title: undefined,
			subtitle: undefined,
			drilldown_uri: undefined,
			value_suffix: undefined,
			value: undefined,
			delta: undefined,
			invert: undefined,
			threshold: undefined,
			search_string: undefined
        },
        
        initialize: function() {
        	
            // Apply the defaults
            this.options = _.extend({}, this.defaults, this.options);
        	
        	this.search = this.options.search;
        	this.result = null;
        	
        	// The following parameters are 
        	this.state = stateNotStarted;
        	this.isDeleted = false;
        	
        	// Get the parameters that are used if the key indicator is not supposed to use an existing saved search
        	this.title = this.options.title;
        	this.subtitle = this.options.subtitle;
        	this.drilldown_uri = this.options.drilldown_uri;
        	this.value_suffix = this.options.value_suffix;
        	this.value = this.options.value;
        	this.delta = this.options.delta;
        	this.invert = this.options.invert;
        	this.threshold = this.options.threshold;
        	this.search_string = this.options.search_string;
        	
        },
        
        events: {
            "click .delete": "remove",
            "blur .threshold": "setThreshold" //Don't use onchange, this breaks Internet Explorer since it won't let users get focus on the input after re-rendering
        },
        
        /**
         * Render the panel and then keep re-rendering until the search completes
         */
        renderToCompletion: function() {
        	
        	// If the rendering isn't done yet but we are awaiting results, then refresh
        	if(!this.doneRendering() && this.gettingResults()){
                
                this.updateWithResults();
                
                // If the panel is not done being rendered then treat the panel as still needing to do work
                if( !this.doneRendering() ){
                	
                	// Reload the panel automatically
                	setTimeout(
        					function(){
        						this.renderToCompletion();
        					}.bind(this), 800 );
                }
            }
        	
        },
        
        /**
         * Render the key indicator according to its current state. Returns true if the render function was able to complete.
         */
        render: function(auto_rerender_if_pending) {
        	
        	// The search is dispatched
        	if( this.state == stateDispatched ){
        		this.renderLoadingContent();
        		
        		// If we need to re-render the pending content, then schedule it
        		if(auto_rerender_if_pending){
        			setTimeout(
        					function(){
        						this.render(true);
        					}.bind(this), 800 );
        		}
        		
        		return false;
        	}
        	
        	// We got the results, time to render them
        	else if( this.state == stateRendered ){
        		this.renderResultContent();
        		return true;
        	}
        	
        	// The key indicator has not yet been started
        	else if( this.state == undefined || this.state == stateNotStarted ){
        		this.renderPendingContent();
        		return true;
            }
        	
        	// Otherwise, render an error
        	else{
        		this.renderUnableToLoadContent();
        		return true;
        	}
        	
            return this;
        },
        
        /**
         * Determine if the search was dispatched.
         */
        wasDispatched: function(){
        	return this.state >= stateDispatched;
        },
        
        /**
         * Determine if the key indicator was told to get the results.
         */
        gettingResults: function(){
        	return this.wasDispatched();
        },
        
        /**
         * Determine if we are done rendering.
         */
        doneRendering: function(){
        	return this.state >= stateRendered;
        },
        
        /**
         * Get the actual number after the units are dereferenced.
         */
        getActualNumberFromHumanReadable: function( num ){
        	
        	var unitsTable = {
        			'T' : 1000000000000,
        			'B' : 1000000000,
        			'M' : 1000000,
        			'K' : 1000
        			};
        	
        	var parse_num = /^([-]?[0-9]+([.][0-9]+)?)\s*([a-zA-Z]?)$/i;
        	
        	var matches = parse_num.exec(num);
        	
        	if(matches){
    	    	var number = parseFloat(matches[1],10);
    	    	var units = matches[3];
    	    	
    	    	// Make sure the number is valid
    	    	if( isNaN(number) ){
    	    		return null;
    	    	}
    	    	
    	    	// Do the math to change the value according to the units
    	    	if(!units){
    	    		return number;
    	    	}
    	    	else if(unitsTable.hasOwnProperty(units.toUpperCase())){
    	    		return number * unitsTable[units.toUpperCase()];
    	    	}
    	    	else{
    	    		return null;
    	    	}
        	}
        	else{
        		// Doesn't match the regular expression, value is invalid
        		return null;
        	}
        	
        },
        
        /**
         * Get human readable number.
         */
        getHumanReadableNumber: function( num ){
        	
        	var units= "";
        	var num_abs = Math.abs(num);

        	if( num_abs >= 1000000000000 ){
        		num = num / 1000000000000;
        		units="T";
        	}
        	else if( num_abs >= 1000000000 ){
        		num = num / 1000000000;
        		units="B";
        	}
        	else if( num_abs >= 1000000 ){
        		num = num / 1000000;
        		units="M";
        	}
        	else if( num_abs >= 1000 ){
        		num = num / 1000;
        		units="k";
        	}
        	
        	if( num_abs >= 100 ){
        		num = Math.round(num);
        	}
        	else{
        		num = Math.round(num * 10) / 10;
        	}
        	
        	return num + units;
        },
        
        /**
         * Determine if the value is a valid integer
         */
        isValidInteger: function(might_be_number){
        	
        	var reg = /^-?\d+$/;
        	
        	return reg.test(might_be_number);
        	
        },
        
        /**
         * Determine if the threshold that was set from the user-interface is valid.
         */
        isThresholdFormValueValid: function(){
        	
        	// Get the set value
        	var new_threshold = this.getThresholdFormValue();
        	
        	// Validate the value
        	if( new_threshold.length > 0 && this.getActualNumberFromHumanReadable(new_threshold) === null ){
        		return false; //Value did not validate
        	}
        	
        	return true;
        	
        },
        
        /**
         * Get the threshold defined in the editing interface.
         */
        getThresholdFormValue: function(){
        	return $('.threshold', this.$el).val();
        },
        
        /**
         * User has changed the threshold value. When this is changed, this function will:
         * 
         * 1) Validate the value
         * 2) Store the modified value 
         * 3) Re=render the key indicator
         */
        setThreshold: function(){
        	
        	// Persist the value. It may seem to be odd to persist the value before validating it
        	// but we need to do this so that the value will be displayed when we re-render the
        	// interface. We will highlight the fact that the threshold is invalid in the UI and
        	// prevent the value from being saved so storing the value now even if it is invalid
        	// is ok.
        	this.threshold = this.getThresholdFormValue();
        	
        	// Re-render the view so that threshold change is represented in the view (the value changes color)
        	this.render();
        	
        	/*
        	if( $.browser.msie ){
        		// Don't re-render in Internet Explorer. For some reason, IE won't let users click into the input box if the input box is re-rendered.
        		// Instead, just highlight the invalid input
        		this.highlightInvalidInput();
        	}
        	else{
        		this.render();
        	}
        	*/
        	
        },
        
        /**
         * Highlight the input fields as invalid if they are incorrect. Otherwise, hide the text indicating that the input is invalid.
         */
        highlightInvalidInput: function(){
        	
            // Note that the threshold is invalid if it is
        	if( !this.isThresholdFormValueValid() ){
        		$('.threshold-holder', this.$el).addClass('error');
        	}
        	
        	// Otherwise, hide the error
        	else{
        		$('.threshold-holder', this.$el).removeClass('error');
        	}
        },
        
        /**
         * Render content based on the search result
         */
        renderResultContent: function(){
        	
        	fields = this.result.results[0];
        	
        	var threshold_orig = this.getFromActionOrResult("threshold", "action.keyindicator.threshold", this.search, fields, null, this.threshold);
        	var threshold = this.getActualNumberFromHumanReadable(threshold_orig);
        	
        	// If a user-defined threshold was set, then use this value
        	if( this.threshold === null ){
        		threshold_orig = "";
        	}
        	/*
        	if( this.threshold === null || isNaN(this.threshold) ){
        		threshold_orig = "";
        	}
        	*/
        	
        	/*
        	else if( this.threshold === null ){
        		threshold_orig = threshold;
        	}
        	else if( this.getActualNumberFromHumanReadable(this.threshold) ){
        		threshold = this.getActualNumberFromHumanReadable(this.threshold);
        	}*/
        	
            var value_field_name = this.getFromActionOrResult("value", "action.keyindicator.value", this.search, fields, "current_count", this.value);
            var delta_field_name = this.getFromActionOrResult("delta", "action.keyindicator.delta", this.search, fields, "delta", this.delta);
            var drilldown_uri = this.getFromActionOrResult("drilldown_uri", "action.keyindicator.drilldown_uri", this.search, fields, undefined, this.drilldown_uri);
            
            var invert = this.getBooleanFromActionOrResult("invert", "action.keyindicator.invert", this.search, fields, false, this.invert);
            var title = this.getFromActionOrResult("title", "action.keyindicator.title", this.search, fields, "", this.title);
            var subtitle = this.getFromActionOrResult("subtitle", "action.keyindicator.subtitle", this.search, fields, "", this.subtitle);
            
            var value_suffix = this.getFromActionOrResult("value_suffix", "action.keyindicator.value_suffix", this.search, fields, "", this.value_suffix);
            
            var value = "";
            var delta = "";
            
            if( fields != undefined ){
                value = this.getFloatValueOrDefault(fields[value_field_name], "Unknown");
                delta = this.getValueOrDefault(fields[delta_field_name], "");
            }
        	
            // If we didn't get a drilldown_uri from the search, then let's construct one that allows the user to see the raw results from the underyling search we got the results from
            if( (drilldown_uri === undefined || drilldown_uri === null || drilldown_uri.replace(/^\s+|\s+$/g, '').length === 0) && this.sid ){
            	drilldown_uri = 'search?sid=' + this.sid; 
            }
            
            // Render the template
            this.$el.html( _.template(KeyIndicatorTemplate,{
    			title: title,
    			subtitle: subtitle,
    			drilldown_uri: drilldown_uri,
    			value_suffix: value_suffix,
    			value: value,
    			value_readable: this.getHumanReadableNumber(value),
    			delta: parseFloat(delta, 10),
    			delta_readable: this.getHumanReadableNumber(parseFloat(delta, 10)),
    			invert: invert,
    			threshold: threshold,
    			threshold_orig: threshold_orig
            }) );
            
            // Note that the threshold is invalid if it is
        	this.highlightInvalidInput();
    		
            // Wire up the delete button
    		$(document).on('click', '#' + this.id + " .delete", function() {
    			this.remove();
    		}.bind(this));

        	
        },
        
        /**
         * Render content indicating that are loading the results from a search.
         */
        renderLoadingContent: function(){
        	this.$el.html( '<div class="KP-holder loading">Loading...</div>' );
        },
        
        /**
         * Render content indicating that the search content could not be loaded
         */
        renderUnableToLoadContent: function(){
        	this.$el.html( '<div class="KP-holder KP-indicators-no-results">Unable to load results</div>' );
        },
        
        /**
         * Render content indicating that we could not load the results
         */
        renderPendingContent: function(){
        	this.$el.html( '<div class="KP-holder pending">Pending...</div>' );
        },
        
        /**
         * Return the the value if it is defined; otherwise, return the default value.
         */
        getValueOrDefault: function( value, default_value){
            
            if( value == undefined ){
                return default_value;
            }
            else{
                return value;
            }
            
        },
        
        /**
         * Return the the value if it is defined; otherwise, return the default value. Also, convert the value to a float.
         */
        getFloatValueOrDefault : function( value, default_value){
            value = this.getValueOrDefault( value, default_value);
            
            return parseFloat( value, 10 );
        },
        
        
        /**
         * Trim whitespace from a string
         */
        trim: function(str) 
        {
        	if( str === undefined || str === null){
        		return str;
        	}
        	else{
        		return String(str).replace(/^\s+|\s+$/g, '');
        	}
        },
        
        /**
         * Return the the value if it is defined; otherwise, return the default value. Also, convert the value to a boolean.
         */
        getBooleanValueOrDefault : function( value, default_value){
            value = this.getValueOrDefault( value, default_value);
            
            
            if( value === true || value === false ){
                return value;
            }
            else if( value === undefined || value === null ){
                return false;
            }
            
            value = this.trim(value).toLowerCase();
            
            if(value == "true" || value == "t" || parseInt(value, 10) > 0){
                return true;
            }
            else{
                return false;
            }
            
        },
        
        /**
         * Substitute items items in the string based on the values in the fields.
         */
        substituteVariablesFromResult : function( str, fields ){
        	
        	// Don't try to perform substitution if the string is not a string
        	if (str === undefined || str === null || str === true || str === false){
        		return str;
        	}
        	
        	// Substitute the values
        	for (var field in fields) {
        		
        		var value = fields[field];
        		
        		str = str.replace("$" + field + "$", value);
        	}
        	
        	return str;
        	
        },
        
        /**
         * Return the value of the field from either (in order):
         *  1) the attribute value of the local instance (this.whatever)
         *  2) the key indicator alert action associated with the saved search
         *  3) the field in the results
         *  4) the default value
         */
        getFromActionOrResult : function ( field_name, action_field_name, search, fields, default_value, attribute_value ){
            
        	if( typeof attribute_value !== "undefined" ){
        		return attribute_value;
        	}
        	
        	var value = "";
        	
            if( search.content[action_field_name] !== undefined ){
            	value = search.content[action_field_name];
            }
            else if( fields === undefined ){
                value = default_value;
            }
            else if( fields[field_name] !== undefined ){
            	value = fields[field_name];
            }
            else{
            	value = default_value;
            }
            
            return this.substituteVariablesFromResult(value, fields);
            
        },
        
        /**
         * Same as getFromActionOrResult except that this converts the the returned value to a boolean.
         */
        getBooleanFromActionOrResult : function( field_name, action_field_name, search, fields, default_value, attribute_value ){
            return this.getBooleanValueOrDefault( this.getFromActionOrResult( field_name, action_field_name, search, fields, default_value, attribute_value ), default_value );
        },
        
        /**
         * Same as getFromActionOrResult except that this converts the the returned value to a float.
         */
        getFloatFromActionOrResult : function( field_name, action_field_name, search, fields, default_value, attribute_value ){
        	return this.getFloatValueOrDefault( this.getFromActionOrResult( field_name, action_field_name, search, fields, default_value, attribute_value ), default_value );
        },
        
        /**
         * Get the search results from Splunk and render accordingly
         */
        updateWithResults: function(){
        	
        	// If we don't have a search ID, then don't try to get the results
        	if( this.sid === undefined || this.sid === null ){
        		return;
        	}
        	
    		var params = new Object();
    		params.output_mode = 'json';
    		var uri = Splunk.util.make_url('/splunkd/__raw/services/search/jobs/', this.sid, '/results');
    		uri += '?' + Splunk.util.propToQueryString(params);
    		
    		jQuery.ajax({
    			url:     uri,
    			type:    'GET',
    			cache:    false,
    			success: function(result, textStatus, jqXHR ) {
	    				
	    			    if(result !== undefined && result.isOk === false){
	    			    	alert(result.message);
	    		        }
	    			    else if( result !== undefined && result !== "" && !result.preview && result !== undefined && jqXHR.status == 200 ){
	    			    	this.result = result;
	    			    	this.state = 2;
	    			    	this.render();
	    			    }
    				}.bind(this),
    			error: function(jqXHR,textStatus,errorThrown) {
                        console.warn("Unable to get the search results");
                        this.state = 3;
                        this.render();
                	}.bind(this),
    			async:   true
    		});
        	
        },
        
        /**
         * Get the dispatched search from the history
         */
        getDispatchedSearchFromHistory: function(){
        	
        	var params = new Object();
            params.output_mode = 'json';
            params.count = '1';
            params.search = 'isScheduled=1 AND isDone=1 AND isRealTimeSearch=0'; // Only get completed searches that were scheduled (not ad-hoc)
            
            var uri = Splunk.util.make_url('/splunkd/__raw/services/saved/searches/', encodeURIComponent(this.search.name), '/history');
            uri += '?' + Splunk.util.propToQueryString(params);
            
            var search_results_id = null;
            
            jQuery.ajax({
                url:     uri,
                type:    'GET',
                cache:   false,
                success: function(result) {
                     if(result !== undefined && result.isOk === false){
                         alert(result.message);
                     }
                     else if(result !== undefined && result.entry.length === 0 ){
                    	 console.warn("Unable to get historical search results for: " + this.search.name);
                     }
                     else if(result !== undefined && result.entry.length > 0 ){
                         search_results_id = result.entry[0].name;
                         console.info("Successfully retrieved historical search results for: " + this.search.name);
                     }
                     
                     this.state = 1; //stateDispatched;
                }.bind(this),
                error: function(jqXHR, textStatus, errorThrown) {
                     sid = null;
                     console.error("Unable to get search results: " + this.search.name);
                     this.state = 3;
                }.bind(this),
                async:   false
            });
            
            return search_results_id;
            
        },
        
        /**
         * Get the existing search results
         */
        getExistingResults: function(){
        	
        	// Determine if the search is scheduled
        	if( this.search.content.is_scheduled ){
        		this.getDispatchedSearchFromHistory();
        	}
        	
        },
        
        /**
         * Kick off the process of getting results
         */
        startGettingResults: function(){
        	
        	var dispatched_search_exists = false;
        	
        	if( this.search_string ){
        		console.info("Results for key indicator will be loaded from an ad-hoc search (not a saved search)");
        		
        		return this.dispatchAdHocSearch(this.search_string);
        		
        	}
        	// Determine if the search is scheduled, get the historical results if so
        	else if( this.search.content.is_scheduled ){
        		
        		this.sid = this.getDispatchedSearchFromHistory();
        		
        		if(this.sid !== null){
        			console.info("Results for key indicator will be loaded from scheduled search results (" + this.search.name + ")");
        			this.render();
        			return this.sid;
        		}
        	}
        	
        	// No historical search results existed; dispatch the search.
        	return this.dispatchSavedSearch();
        	
        },
        
        /**
         * Dispatch the saved search so that it can begin obtaining results.
         */
        dispatchSavedSearch: function(){
        	
            var params = new Object();
            params.output_mode = 'json';
            
            var uri = Splunk.util.make_url('/splunkd/__raw/services/saved/searches/', encodeURIComponent(this.search.name), '/dispatch');
            uri += '?' + Splunk.util.propToQueryString(params);

            var sid = null;
            
            jQuery.ajax({
                url:     uri,
                type:    'POST',
                cache:   false,
                success: function(result) {
                     if(result !== undefined && result.isOk === false){
                         alert(result.message);
                     }
                     else if(result !== undefined){
                         this.sid = result.sid;
                         sid = this.sid;
                     }
                     
                     this.state = 1; //stateDispatched;
                }.bind(this),
                error: function(jqXHR, textStatus, errorThrown) {
                     sid = null;
                     console.error("Unable to dispatch search: " + this.search.name);
                     this.state = 3;
                }.bind(this),
                async:   false
            });
            
        	this.render();
            return sid;
        },
        
        /**
         * Dispatch the search so that it can begin obtaining results.
         */
        dispatchAdHocSearch: function( search_string ){
        	
        	if( typeof search_string === "undefined" || search_string === null ){
        		console.error("Search string to execute must be provided");
        		return null;
        	}
        	
            var params = new Object();
            params.output_mode = 'json';
            params.search = search_string;
            
            var uri = Splunk.util.make_url('/splunkd/__raw/services/search/jobs');
            
            var sid = null;
            
            jQuery.ajax({
                url:     uri,
                type:    'POST',
                data:    params,
                cache:   false,
                success: function(result) {
                     if(result !== undefined && result.isOk === false){
                         alert(result.message);
                     }
                     else if(result !== undefined){
                         this.sid = result.sid;
                         sid = this.sid;
                     }
                     
                     this.state = 1; //stateDispatched;
                }.bind(this),
                error: function(jqXHR, textStatus, errorThrown) {
                     sid = null;
                     console.error("Unable to dispatch search: " + search_string);
                     this.state = 3;
                }.bind(this),
                async:   false
            });
            
        	this.render();
            return sid;
        },
        
        /**
         * Remove the given indicator
         */
        remove: function(){
        	this.$el.remove();
        	this.isDeleted = true;
        },
        
        /**
         * Indicates if the indicator is in a state that the value can be saved. This is oftentimes false when the user defined a value in the
         * editing interface is invalid and the user needs to be prompted to change it.
         */
        readyToBeSaved: function(){
        	if( !this.isThresholdFormValueValid() ){
        		return false;
        	}
        	else{
        		return true;
        	}
        }
        
    });
    
    return KeyIndicatorView;
});
