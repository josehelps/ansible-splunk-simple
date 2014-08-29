define([
    "jquery",
    "underscore",
    "backbone"
], function(
    $,
    _,
    Backbone
) {
    /* Backbone.Model for the dashboard view.  
    Currently only has one name attribute.  */
    return Backbone.Model.extend({
        initialize: function() {
            this.id = this.attributes.attributes.name;

        }
    });
});