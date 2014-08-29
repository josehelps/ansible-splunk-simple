define([
    "jquery",
    "underscore",
    "backbone"
], function(
    $,
    _,
    Backbone
) {
    return Backbone.Model.extend({
        initialize: function() {
            this.id = this.cid;
            this.attributes.text = this.attributes.text || "";
            this.attributes.attributes = this.attributes.attributes || {href: "", target: "_self"};
        }
    });
});