define([
    'jquery',
    'underscore',
    'backbone',
    'app/models/SwimlaneGroup'
], function(
    $,
    _,
    Backbone,
    SwimlaneGroup
) {
    return Backbone.Collection.extend({
        model: SwimlaneGroup,
        initialize: function() {
            this.on("change:selected", _.bind(this.onSelectedChange, this));
        },
        onSelectedChange: function(model) {
            _.each(
                this.filter(function(m) { return m!==model; }),
                function(m){ 
                   m.set({selected: false}, {silent: true});
                }
            );
        }
    });
});

