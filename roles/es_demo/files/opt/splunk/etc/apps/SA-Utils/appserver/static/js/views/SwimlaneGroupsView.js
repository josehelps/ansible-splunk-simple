define([
    'jquery',
    'underscore',
    'backbone',
    'app/views/SwimlaneGroupView'
], function(
    $,
    _,
    Backbone,
    SwimlaneGroupView
) {
    return Backbone.View.extend({
        initialize: function(options) {
            this.options = options || {};
            this.lanes = this.options.collection;
            this.collection = this.options.collection.groups;
            this.collection.on("reset", _.bind(this.render, this));
        },
        render: function(collection) {
            this.empty();
            this.renderAll();
            return this;
        },
        renderAll: function() {
            var collection = this.collection.clone(),
                custom = collection.find(
                  function(m) {
                      return m.get('title') === 'Custom';
                  }
                );
            collection.remove(custom, {silent: true}); 
            collection.each(_.bind(this.renderOne, this));
            this.renderOne(custom);
        },
        renderOne: function(model) {
            this.$el.append(new SwimlaneGroupView({model: model}).render().el);
        },
        empty: function() {
            this.$el.empty();
        }
    });
});
