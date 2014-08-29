define([
    'jquery',
    'underscore',
    'backbone',
    'contrib/text!app/templates/SwimlaneGroup.html'
], function(
    $,
    _,
    Backbone,
    SwimlaneGroupTemplate
) {
    return Backbone.View.extend({
        className: "swimlaneGroup",
        initialize: function() {
            this.input = null;
            this.model.on("change:selected", _.bind(this.onSelect, this)); 
        },
        checked: function() {
            this.model.set("selected", true);
        },
        events: {
            "click input": "checked"
        },
        onSelect: function() {
            this.$input.prop('checked', this.model.get('selected'));
        },
        render: function() {
            this.$el.html(_.template(SwimlaneGroupTemplate, this.model.attributes));
            this.$input = this.$el.find("input");
            this.onSelect();
            return this;
        }
    });
});
