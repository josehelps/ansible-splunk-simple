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
    return Backbone.Model.extend({
        initialize: function(options){
            this.prefs = options.prefs;
        },
        getUrl: function(){
            var url = this.prefs.serializeToURL();
            return url;
        }
    });
});
