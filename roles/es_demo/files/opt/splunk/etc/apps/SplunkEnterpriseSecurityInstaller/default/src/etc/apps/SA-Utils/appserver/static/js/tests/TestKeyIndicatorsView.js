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
	    
	    describe("KeyIndicatorsView: Comparing key indicator order", function() {
	     	
			 it("where the first search is before the second", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator.group.0.name"] = "traffic_center";
				 search1.content["action.keyindicator.group.0.order"] = "0";
				 
				 var search2 = {};
				 search2.content = {};
				 search2.content["action.keyindicator.group.1.name"] = "traffic_center";
				 search2.content["action.keyindicator.group.1.order"] = "1";
				 
				 expect(keyIndicatorsView.compareSearches(search1, search2, "traffic_center")).toBeLessThan(0);
			 });
			 
			 it("where the second search is before the first", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator.group.0.name"] = "traffic_center";
				 search1.content["action.keyindicator.group.0.order"] = "1";
				 
				 var search2 = {};
				 search2.content = {};
				 search2.content["action.keyindicator.group.1.name"] = "traffic_center";
				 search2.content["action.keyindicator.group.1.order"] = "0";
				 
				 expect(keyIndicatorsView.compareSearches(search1, search2, "traffic_center")).toBeGreaterThan(0);
			 });
	
	     });
	    
	    describe("KeyIndicatorsView: Retrieving key indicator order", function() {
	     	
			 it("where the search has one key indicator group name", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator.group.0.name"] = "traffic_center";
				 search1.content["action.keyindicator.group.0.order"] = "0";
				 
				 expect(keyIndicatorsView.getSearchOrder("traffic_center", search1)).toBe(0);
			 });
			 
			 it("where the search has more than one key indicator group name", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator.group.0.name"] = "not_traffic_center";
				 search1.content["action.keyindicator.group.0.order"] = "0";
				 search1.content["action.keyindicator.group.1.name"] = "traffic_center";
				 search1.content["action.keyindicator.group.1.order"] = "1";
				 
				 expect(keyIndicatorsView.getSearchOrder("traffic_center", search1)).toBe(1);
			 });
	
	     });
	    
	    describe("KeyIndicatorsView: Determine if key indicator is in group", function() {
	     	
			 it("where the search is in the group", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator"] = "1";
				 search1.content["action.keyindicator.group.0.name"] = "traffic_center";
				 
				 expect(keyIndicatorsView.isSearchInKeyIndicatorGroup(search1, "traffic_center")).toBe(true);
			 });
			 
			 it("where the search is in the group and has more than one key indicator group name", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator"] = "1";
				 search1.content["action.keyindicator.group.0.name"] = "not_traffic_center";
				 search1.content["action.keyindicator.group.0.order"] = "0";
				 search1.content["action.keyindicator.group.1.name"] = "traffic_center";
				 search1.content["action.keyindicator.group.1.order"] = "1";
				 
				 expect(keyIndicatorsView.isSearchInKeyIndicatorGroup(search1, "traffic_center")).toBe(true);
			 });
			 
			 it("where the search is in the group", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator"] = "1";
				 search1.content["action.keyindicator.group.0.name"] = "not_traffic_center";
				 
				 expect(keyIndicatorsView.isSearchInKeyIndicatorGroup(search1, "traffic_center")).toBe(false);
			 });
			 
			 it("where the search is not a key indicator (has no keyindicator alert action)", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 
				 expect(keyIndicatorsView.isSearchInKeyIndicatorGroup(search1, "traffic_center")).toBe(false);
			 });
	
	     });

	    describe("KeyIndicatorsView: Retrieving key indicator group number", function() {
	     	
			 it("where the search has one key indicator group name", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator.group.0.name"] = "traffic_center";
				 search1.content["action.keyindicator.group.0.order"] = "0";
				 
				 expect(keyIndicatorsView.getGroupNumber("traffic_center", search1)).toBe(0);
			 });
			 
			 it("where the search has more than one key indicator group name", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator.group.0.name"] = "not_traffic_center";
				 search1.content["action.keyindicator.group.0.order"] = "0";
				 search1.content["action.keyindicator.group.1.name"] = "traffic_center";
				 search1.content["action.keyindicator.group.1.order"] = "1";
				 
				 expect(keyIndicatorsView.getGroupNumber("traffic_center", search1)).toBe(1);
			 });
			 
			 it("where the search has does not match the key indicator group name", function() {
				 
				 var search1 = {};
				 search1.content = {};
				 search1.content["action.keyindicator.group.0.name"] = "not_traffic_center";
				 search1.content["action.keyindicator.group.0.order"] = "0";
				 search1.content["action.keyindicator.group.1.name"] = "also_not_traffic_center";
				 search1.content["action.keyindicator.group.1.order"] = "1";
				 
				 expect(keyIndicatorsView.getGroupNumber("traffic_center", search1)).toBe(null);
			 });
	
	     });

     }
);