Splunk.Module.SOLNCheckboxes = $.klass(Splunk.Module, {
    initialize: function($super, container) {
	$super(container);
	//Set up internal variables
        // debugger;
        this.boxConfig = {};
        this.boxIds = [];
        this.varName = "boxConfig";
        this.configStore = this.moduleId + "_" + this.varName;
        this.formatBoxConfig(this.getParam("boxConfig"));
        this.getSelectionType();
        this.addButtons();

	this.firstLoad = true;
	this.stickyValue = SOLN.pullSelection(this.configStore);
        
        // this.setInitialBoxConfig();
        // this.updateButtons();
        
        var that = this;
        $('input', this.$container).click(function() { that.pushContextToChildren(); });
    },
    onContextChange: function() {
        if (this.firstLoad) {
            this.setInitialBoxConfig();
            this.firstLoad = false;
        }
        this.updateButtons();
    },
    setInitialBoxConfig: function() {
        var loadingFromCtxt = false;
        var context = this.getContext();
        // var qvars = Splunk.util.queryStringToProp(window.location.search);
        // for (var name in qvars) {
        //     SOLN.storeVariable(name, null, qvars[name], context);
        // }
        for (var i = 0; i < this.boxIds.length; i++) { 
            var id = this.boxIds[i];
            // if (id === "marge") debugger;
            var ctxtParam = SOLN.getVariableValue(id, context);
            if (ctxtParam && 
                (ctxtParam === this.boxConfig[id].onVal || ctxtParam === this.boxConfig[id].offVal)) {
                loadingFromCtxt = true;
                this.boxConfig[id].checked = (ctxtParam === this.boxConfig[id].onVal);
            }
        }
        if (!loadingFromCtxt) {
            if (this.stickyValue) {
                this.boxConfig = this.stickyValue; 
            } else if (this.getParam("defaultSelected")) { 
                this.setDefaultSelected(); 
            }
        }
    },
    addButtons: function() {
        this.$container = $(".solncheckboxes-container", this.container);
        var inputHtml = '<input type="#SELTYPE" id="#ID" name="#SELTYPE" /><label id=#ID-label for="#ID">#LABEL</label>';
        inputHtml = inputHtml.replace(/#SELTYPE/g, this.selectionType);
        for (var i = 0; i < this.boxIds.length; i++) {
            var html = inputHtml.replace(/#ID/g, this.boxIds[i])
                .replace(/#LABEL/g, SOLN.clearVariables(this.boxConfig[this.boxIds[i]].label));
            $(html).appendTo(this.$container);
        }
        this.$container.buttonset();
    },
    updateButtons: function() {
    	var context = this.getContext();
        for (var i = 0; i < this.boxIds.length; i++) {
            var id = this.boxIds[i];
            var idSel = '#' + id;
            var labelSel = '#' + id + "-label span";
            var label = this.boxConfig[id].label;
            label = SOLN.replaceVariables(label, context);
            label = SOLN.clearVariables(label);
            $(labelSel, this.$container).text(label);
            var $button = $(idSel, this.$container);
            if (this.boxConfig[id].checked) {
                $button.attr('checked','checked');
            } else {
                if ($button.attr('checked')){
                    $button.removeAttr('checked');
                }
            }
            $button.button("refresh");
        }
    },
    updateConfig: function() {
        for (var i = 0; i < this.boxIds.length; i++){
            this.boxConfig[this.boxIds[i]].checked = false;
        }
        
        var that = this;
        $('input:checked', this.$container).each(function() {
            that.boxConfig[this.id].checked = true;
        });
    },
    getSelectionType: function() {
        switch (this.getParam("selectionType")) {
        case "checkbox":
            this.selectionType = "checkbox";
            break;
        case "radio":
            this.selectionType = "radio";
            break;
        default:
            this.selectionType = "checkbox";
        	break;
        }
    },
    setDefaultSelected: function() {
        var sel = this.getParam("defaultSelected").split(',');
        for (var i = 0; i < sel.length; i++) {
            var id = $.trim(sel[i]);
            if (this.boxConfig.hasOwnProperty(id)){
                this.boxConfig[id].checked = true;
            }
        }
    },
    formatBoxConfig: function(spec) {
        var buttonSpec = spec.split(';');
        
        for (var i = 0; i < buttonSpec.length; i++){
            buttonSpec[i] = buttonSpec[i].split(',');
        }
        
        for (var j = 0; j < buttonSpec.length; j++) {
            var id = $.trim(buttonSpec[j][0]);
            var label = $.trim(buttonSpec[j][1]);
            var onVal = $.trim(buttonSpec[j][2]);
            var offVal = $.trim(buttonSpec[j][3]);
            this.boxIds.push(id);
            var checkedDefault = false;
            this.boxConfig[id] = {"label": label, "checked": checkedDefault, "onVal": onVal, "offVal": offVal};
        }
    },
    getModifiedContext: function() {
	var context = this.getContext();
        this.updateConfig();
	SOLN.stickSelection(this.configStore, this.boxConfig);
        for (var id in this.boxConfig) {
            var button = this.boxConfig[id];
            var val = button.checked ? button.onVal : button.offVal;
	    SOLN.storeVariable(id, null, val, context);
        }

	return context;
    },
    resetUI: function() {} //Just so splunk stops bitching at me
});
