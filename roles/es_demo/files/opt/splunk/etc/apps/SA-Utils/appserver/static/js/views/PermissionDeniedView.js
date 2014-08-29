define([
    'jquery',
    'underscore',
    'backbone',
    'splunk.util'
], function(
    $,
    _,
    Backbone
) {
    return Backbone.View.extend({
    	
        defaults: {
            message: "You do not have the necessary capabilities required to perform this action. Please contact your Splunk administrator."
        },
    	
        initialize: function(options) {
        	this.options = _.extend({}, this.defaults, this.options);
        	this.message = this.options.message;
            return this;
        },
        
        render: function(){
        	$(this.$el).html(this.message);
        }
    });
});
