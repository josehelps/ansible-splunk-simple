require.config({
    paths: {
        key_indicators_view: "../app/SA-Utils/js/views/KeyIndicatorsView",
        jasmine: "//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine"
    }
});

require([
         "jquery",
         "underscore",
         "backbone",
         "key_indicators_view",
         "jasmine",
         "splunkjs/mvc/simplexml/ready!"
     ], function(
         $,
         _,
         Backbone,
         KeyIndicatorsView
     )
     {
	
	    // Make a key indicator
	    var key_indicators_el = $('<div></div>');
	    var search = {};
	  	 
	    var keyIndicatorsView = new KeyIndicatorsView({
	    	group_name: 'traffic_center',
	        el: key_indicators_el
	    });
	
	    describe("KeyIndicatorsView: Retrieval of key indicator searches", function() {
	     	
			 it("for group 'traffic_center'", function() {
				 expect(keyIndicatorsView.getKeyIndicatorSearches('traffic_center').length).toBeGreaterThan(4);
			 });
	
	     });

     }
);