define([
    'jquery',
    'underscore',
    'backbone',
    'bootstrap.modal',
    'app/views/SwimlanePickersView',
    'app/views/SwimlaneGroupsView'
], function(
    $,
    _,
    Backbone,
    modal,
    SwimlanePickersView,
    SwimlaneGroupsView
) {
    return Backbone.View.extend({
        initialize: function(options) {
            this.options = options || {};
            this.collection = this.options.collection;

            this.swimlanePickersView = new SwimlanePickersView({
              el: this.$(this.options.swimlanes_el),
              collection: this.collection
            });

            this.swimlaneGroupsView = new SwimlaneGroupsView({
              el: this.$(this.options.collections_el),
              collection: this.collection
            });

            $(this.options.edit_el).click(
              _.bind(this.open, this)
            );
            return this;
        },
        open: function() {
            this.$el.modal("show");
        },
        close: function() {
            this.$el.modal("hide");
        },
        events: {
            "click .close": "close"
        }
    });
});
