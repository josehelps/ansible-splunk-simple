Splunk.Module.SOLNSlider = $.klass(Splunk.Module, {
    initialize: function($super, container) {
	$super(container);
	//Set up internal variables
        this.varName = this.getParam("varName");
	this.minbound = this.getParam("minbound") ? parseInt(this.getParam("minbound"), 10) : 0;
	this.maxbound = this.getParam("maxbound") ? parseInt(this.getParam("maxbound"), 10) : this.minbound + 100;
        this.defaultValue = this.getParam("defaultValue");
        if (!this.defaultValue || (this.defaultValue > this.maxbound || this.defaultValue < this.minbound)){
        	this.defaultValue = (this.maxbound - this.minbound) / 2.0;
        }
        
	this.$slider = $(".solnslider-container", this.container);
	this.$slider.slider({min: this.minbound, 
			     max: this.maxbound,
			     value: this.defaultValue});

	this.firstLoad = true;
	this.stickyValue = SOLN.pullSelection(this.varName);
	// var context = this.getContext();
	// var value = this.$slider.slider('value');
	// SOLN.storeVariable(this.varName, null, value, context);
	var that = this;
	this.$slider.slider({change: function() { that.pushContextToChildren(); }});
    },
    setInitialSliderConfig: function() {
        var context = this.getContext();
	if (SOLN.getVariableValue(this.varName, context)) {
	    //Set to the value in the context if it exists and this is the first load
	    this.$slider.slider('value', SOLN.getVariableValue(this.varName, context));
	}
	else if (this.stickyValue) {
	    //Set the value to the previously selected if it exists
	    this.$slider.slider('value', this.stickyValue);
	}
	else {
	    //If all else fails, set to default
	    this.$slider.slider('value', this.defaultValue);
	}
    },
    onContextChange: function() {
	//Set to url or stored value if available
	if (this.firstLoad) {
            this.setInitialSliderConfig();
            this.firstLoad = false;
	}
    },
    getModifiedContext: function() {
	var context = this.getContext();
	var value = this.$slider.slider('value');
	    
	//Handle the sticky value
	this.stickyValue = value;
	SOLN.stickSelection(this.varName, this.stickyValue);
	    
	SOLN.storeVariable(this.varName, null, value, context);

	return context;
    },
    resetUI: function() {} //Just so splunk stops bitching at me
});
