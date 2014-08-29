define([
     "jquery",
     "underscore",
     "backbone",
     "contrib/text!app/templates/SignBoardHeader.html"
], function(
     $,
     _,
     Backbone,
     Template
) {
     return Backbone.View.extend({
          template: _.template(Template),
          initialize: function() {
              this.model.on('ready:headerData', _.bind(this.render, this));
              this.model.on('clearAll', _.bind(this.emptyAll, this));
          },
          emptyAll: function() {
              this.$el.empty();
          }, 
          render: function() {
              this.emptyAll();
              this.$el.append(this.template(this.model.get('meta')));
              return this;
          }
     });
});
