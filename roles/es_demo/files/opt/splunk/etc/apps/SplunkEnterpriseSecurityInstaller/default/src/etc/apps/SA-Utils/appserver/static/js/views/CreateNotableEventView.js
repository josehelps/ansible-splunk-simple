define([
    'jquery',
    'backbone',
    'underscore',
    'd3',
    'backbone-mediator'
],
function(
    $,
    Backbone,
    _,
    d3
){
    return Backbone.View.extend({
        initialize: function(){
            var self = this;
            this.$el.on('click', function(){
                window.location = self.model.get("url");
            });
        },
        render: function(){
        }
    });
});

