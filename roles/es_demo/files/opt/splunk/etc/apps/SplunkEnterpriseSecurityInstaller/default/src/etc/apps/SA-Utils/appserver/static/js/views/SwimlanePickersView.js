define([
    'jquery',
    'underscore',
    'backbone',
    'app/views/SwimlanePickerView'
], function(
    $,
    _,
    Backbone,
    SwimlanePickerView
) {
    return Backbone.View.extend({
        initialize: function(options) {
            this.options = options || {};
            this.collection = this.options.collection;
            this.collection.on("reset", _.bind(this.render, this));
        },
        render: function(collection) {
            this.renderAll();
            return this;
        },
        renderAll: function() {
            this.$el.empty();
            this.collection.each(_.bind(this.renderOne, this));
        },
        renderOne: function(model) {
            this.$el.append(new SwimlanePickerView({model: model}).render().el);
        }
    });
});
