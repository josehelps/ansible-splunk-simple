define([
    'jquery',
    'underscore',
    'backbone',
    'app/models/Event'
], function(
    $,
    _,
    Backbone,
    Event 
) {
    return Backbone.Collection.extend({
        model: Event
    });
});
