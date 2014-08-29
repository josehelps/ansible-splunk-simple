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
            if (!this.get("type")) {
                this.set("type", "divider");
            }
    	}
    });
});