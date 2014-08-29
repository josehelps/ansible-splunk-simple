require.config({
    paths: {
        console: '../app/SA-Utils/js/util/Console'
    }
});

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "splunkjs/mvc/utils",
    "splunkjs/mvc/tokenutils",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "console"
], function(_, Backbone, mvc, utils, TokenUtils, $, SimpleSplunkView ){

    // Define the custom view class
    var SearchAggregateView = SimpleSplunkView.extend({
    	
        className: "SearchAggregateView",

        /**
         * Setup the defaults
         */
        defaults: {
        	
        },
        
        events: {
        	"click .btn-remove": "removeAggregate",
        	"click .btn-edit": "editAggregate"
        },
        
        initialize: function() {
        	
        	// Apply the defaults
            this.options = _.extend({}, this.defaults, this.options);
            options = this.options || {};
            
            this.identifier = options.identifier;
            this.fx = options.fx;
            this.alias = options.alias;
            this.attribute = options.attribute;
        },
        
        editAggregate: function(){
        	Backbone.trigger("search_aggregate:edit", this.identifier, this.fx, this.attribute, this.alias);
        },
        
        removeAggregate: function(){
        	Backbone.trigger("search_aggregate:remove", this.identifier);
        },
        
        /**
         * Render the view
         */
        render: function(){
        	
        	var template = '<td><%- fx %>(<%- attribute %>) <% if(alias) { %>as <%- alias %><% } %></td>'+
        					'<td><a href="#" class="btn-edit">Edit</a></td>' +
        					'<td><a href="#" class="btn-remove">Delete</a></td>';
        	
        	this.$el.html(_.template(template, {
        		'fx': this.fx,
        		'alias': this.alias,
        		'attribute' : this.attribute,
        		'identifier' : this.identifier
        	}));
        	
        	
        }
            
	});

    return SearchAggregateView;
});