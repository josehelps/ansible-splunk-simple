define([
    "jquery",
    "underscore",
    "backbone"
], function(
    $,
    _,
    Backbone
) {
    return Backbone.View.extend({
        className: "divider sortable",
        initialize: function() {
            this.model = this.options.model;
            this.app = this.options.app;
        },
        render: function() {
            this.$el.attr("data-id", this.options["data-id"]);
            this.$el.html('<i class="icon-remove removeDivider disabled" />');
            return this;
        },
        isAddNewDivider: function() {
            return this.$el.hasClass("addNewDivider");
        },
        dropped: function() {
            this.$el.removeClass("addNewDivider");
        },
        events: {
            "mouseover": "mouseover",
            "mouseleave": "mouseleave",
            "click .removeDivider": "removeDivider"
        },
        mouseover: function() {
            if (!this.isAddNewDivider()) {
                this.$(".disabled").addClass("hover");
            }
        },
        mouseleave: function() {
            this.$(".disabled").removeClass("hover");
        },
        removeDivider: function() {
            delete this.app.viewsById[this.model.id];
            this.$el.remove();
        }
    });
});
