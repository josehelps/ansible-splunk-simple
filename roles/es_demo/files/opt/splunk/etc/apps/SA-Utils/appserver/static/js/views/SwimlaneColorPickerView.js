define([
    'jquery',
    'underscore',
    'backbone',
    'contrib/text!app/templates/SwimlaneColorPicker.html'
], function(
    $,
    _,
    Backbone,
    SwimlaneColorPickerTemplate
) {
    return Backbone.View.extend({
        initialize: function(options) {
            this.options = options || {};
            this.model = this.options.model;
        },
        render: function() {
            this.$el.html(_.template(SwimlaneColorPickerTemplate));
            this.close();

            return this;
        },
        open: function() {
            this.$el.show();
        },
        isOpen: function() {
            return !this.$el.is(":hidden");
        },
        close: function() {
            this.$el.hide();
        },
        isClosed: function() {
            return this.$el.is(":hidden");
        },
        events: {
            "click .swimlaneColor": "chooseColor",
            "click .swimlaneColorPickerBackground": "close"
        },
        chooseColor: function(e) {
            var color = $(e.target).attr("data-color");
            this.model.set("color", color);
            this.close();
        }
    });
});
