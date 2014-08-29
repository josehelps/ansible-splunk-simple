define( [
    'underscore',
    'module',
    'views/shared/controls/Control',
    'splunk.util'
], function(
    _,
    module,
    Control,
    splunk_util)
{
    /**
     * Synthetic Button
     *
     * @param {Object} options
     *                        {Object} model The model to operate on
     *                        {String} modelAttribute The attribute on the model to observe and update on selection
     *                        {Object} items An array of one-level deep data structures:
     *                                 label (textual display),
     *                                      value (value to store in model)
     *                                      icon (icon name to show in menu and button label)
     *                                 (ie, {label: 'Foo Bar', value: 'foo', icon: 'bar'}).
     *                        {Boolean} invertValue (Optional) If true, then a clicked button has a value of false and
     *                                  an unclicked has a value of true. This is useful for model attributes that denote a negative
     *                                  (ex. disabled). Defaults to false.
     *                        {String} buttonClassName (Optional) Class attribute to the button element. Default is btn.
     *                        {String} additionalClassNames (Optional) Class attribute(s) to add to control
     */
    var SyntheticButtonControl = Control.extend({
        className: 'control',
        moduleId: module.id,
        initialize: function(){
            var defaults = {
                buttonClassName: 'btn',
                defaultValue: true,
                label: ''
            };

            _.defaults(this.options, defaults);
            
            if (this.options.modelAttribute) {
                this.$el.attr('data-name', this.options.modelAttribute);
            }
            
            Control.prototype.initialize.apply(this, arguments);
        },
        events: {
            'click button': function(e) {
                !this.options.enabled || this.setValue(!this._value);
                e.preventDefault();
            }
        },
        disable: function(){
            this.options.enabled = false;
            //this.$('.syn-btn-label').removeClass('active');
            //this.$('.btn').removeClass('btn-off');
        },
        enable: function(){
            this.options.enabled = true;
            //this.$('.syn-btn-label').addClass('active');
            //this.$('.btn').addClass('btn-off');
        },
        normalizeValue: function(value) {
            return splunk_util.normalizeBoolean(value) ? 1 : 0;
        },
        render: function(){
            //console.log("synbutton", this.options.model);
            var clicked = this.options.invertValue ? !this.getValue() : this.getValue();

            if (!this.el.innerHTML) {
                var template = _.template(this.template, {
                                options: this.options,
                                clicked: clicked
                        });
                this.$el.html(template);
                
                if (!this.options.enabled) {
                    this.disable();
                }
            }

            var additionalClassNames = this.options.additionalClassNames;
            if(additionalClassNames) {
                this.$el.addClass(additionalClassNames); 
            }

            return this;
        },

        template: '\
            <button class="syn-btn-label <%- options.buttonClassName %> <% if(options.isSelected){%>active<%}%>" type="button" value="<%- options.label %>">\
                <span class="syn-left-label"><% if(options.label.toUpperCase() == "INFORMATIONAL") {%>INFO<%} else {%><%-options.label.toUpperCase()%><%}%></span>\
                <span class="syn-right-label"><%- options.count%></span>\
            </button>'


    });
    
    return SyntheticButtonControl;
});
