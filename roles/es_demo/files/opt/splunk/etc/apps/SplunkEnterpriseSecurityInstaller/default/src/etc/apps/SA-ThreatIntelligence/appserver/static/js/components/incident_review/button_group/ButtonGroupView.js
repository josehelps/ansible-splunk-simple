define([
    "underscore",
    "jquery",
    "backbone",
    "module",
    "splunkjs/mvc/basemultichoiceview",
    "app-components/incident_review/button_group/SyntheticButtonControl",
    "css!app-components/incident_review/button_group/css/SyntheticButtonControl"
    ],
    function(
        _,
        $,
        Backbone,
        module,
        BaseMultiChoiceView,
        SyntheticButtonControl) {

        var ButtonGroupView = BaseMultiChoiceView.extend({
            moduleId: module.id,
        
            className: "splunk-buttongroup splunk-choice-input",
        
            //_labelRegex: /uc_(\w+):(\w+)/i,

            options: {
                valueField: "",
                labelField: "",
                "default": undefined,
                choices: [],
                value: undefined,
                disabled: false
            },
        
            initialize: function() {
                this.options = _.extend({}, BaseMultiChoiceView.prototype.options, this.options);
                BaseMultiChoiceView.prototype.initialize.apply(this, arguments);
                this._selections = new Backbone.Model();
                this.listenTo(this._selections, "change", this._updateValue, this);
                this.updateDomVal();
            },

            _updateValue: function(model, change, options) {
                // Must copy array so we always get a change event
                var val = this.val().slice(0);
                _(model.changed).each(function(v, k) {
                   if (!v) {
                       val = _(val).without(k);
                   } else if (val.indexOf(k) < 0) {
                       val.push(k);
                       //MODIFY TOKENS WITH "K" FUNCTION
                   }
                });
                this.val(val);
            },


            _disable: function(state) {
                _.each(this._buttons, function(button) {
                    if (state){
                        button.disable();
                    } else {
                        button.enable();
                    }
                });
            },
        
            // Used by unit tests
            _domVal: function() {
                var value = [];
                _.each($('.button', this.el), function(item) {
                    var iStyle = $('i', item).attr('style') || '';
                    var isDisabled = 
                        (iStyle.indexOf('display:none') !== -1) ||
                        (iStyle.indexOf('display: none') !== -1);
                    var subvalue = $('a', item).data('name');
                
                    if (!isDisabled) {
                        value.push(subvalue);
                    }
                });
                return value;
            },

            updateDomVal: function() {
                var oldSelections = this._selections.toJSON();
                var newSelections = {};
                _(oldSelections).each(function(value, key) {
                    newSelections[key] = 0;
                });
                _.each(this.val(), function(val) {
                    newSelections[val] = 1;
                },this);
                this._selections.set(newSelections);
            },

            createView: function() {
                this.$el.empty();
                return $("<div class='splunk-buttongroup-choices btn-group-vertical' data-toggle='buttons'/>").appendTo(this.el);
            },

            updateView: function(viz, data) {
                //console.log("the selections:", this._selections);
                //console.log("the settings:", this.settings.get("value"));
                viz.empty();

                if (this._buttons){
                    _.each(this._buttons, function(button){
                        button.remove();
                    });
                }
                this._buttons = [];
                // If there is no data, we don't want to just render a message,
                // because that will look odd. Instead, we render a single button
                // that will subsequently get disabled (in BaseChoiceView), plus
                // the message. Finally, we also set the label to " " to make sure it
                // gets picked up.
                if (!data || data.length <= 1) {
                    //data = [{value: "", label: " "}];
                    //data = [{value: "", label: " "}];
                    data = [{value: "critical", label: "critical:0"},
                            {value: "high", label: "high:0"},
                            {value: "medium", label: "medium:0"},
                            {value: "low", label: "low:0"},
                            {value: "informational", label: "informational:0"}
                    ];
                }

                //debugger;
                var $choices = this.$(".splunk-buttongroup-choices");
                tokenSelections = this.settings.get("value");

                _.each(data, function(value){

                    var isSelected = false;
                    labelRegex = /(\w+):(\w+)/i;
                    var match = labelRegex.exec($.trim(value.label));
                    var newLabel = "";
                    var newCount = "";

                    if (match) {
                        newLabel = match[1];
                        newCount = match[2];
                    } else {
                        newLabel = $.trim(value.label);
                    }

                    if (tokenSelections && tokenSelections.indexOf(value.value) >= 0) {
                        isSelected = true;
                    }

                    var syntheticButtonControl = new SyntheticButtonControl({
                        model: this._selections,
                        modelAttribute: value.value,
                        //label: $.trim(value.label) || value.value
                        label: newLabel || value.value,
                        count: newCount,
                        isSelected: isSelected
                    });

                    syntheticButtonControl.render().appendTo($choices);
                    this._buttons.unshift(syntheticButtonControl);
                }, this );

                return this;
            }
        });
        
        return ButtonGroupView;
    }
);
