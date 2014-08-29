define([
    'jquery',
    'backbone',
    'underscore',
    'd3'
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
                window.open(self.model.get('url'));
            });
        },
        render: function(){
            return this;
        }
    });
});
