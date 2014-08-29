require.config({
    paths: {
    	key_indicator_editor_view: "../app/SA-Utils/js/views/KeyIndicatorEditorView",
        jasmine: "//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine"
    }
});

require([
         "jquery",
         "underscore",
         "backbone",
         "key_indicator_editor_view",
         "jasmine",
         "splunkjs/mvc/simplexml/ready!"
     ], function(
         $,
         _,
         Backbone,
         KeyIndicatorEditorView
     )
     {
	
	    // Make a key indicator
	    var key_indicator_editor_el = $('<div></div>');
	    var search = {};
	  	 
	    var keyIndicatorEditorView = new KeyIndicatorEditorView({
	    	el: key_indicator_editor_el
	    });

	    describe("KeyIndicatorsEditorView: get value or default", function() {
	     	
			 it("when value is undefined", function() {
				 expect(keyIndicatorEditorView.valueOrDefault(undefined, "default")).toBe("default");
			 });
			 
			 it("when value is empty", function() {
				 expect(keyIndicatorEditorView.valueOrDefault('', "default")).toBe("default");
			 });
			 
			 it("when value is null", function() {
				 expect(keyIndicatorEditorView.valueOrDefault(null, "default")).toBe("default");
			 });
	
			 it("when value is provided", function() {
				 expect(keyIndicatorEditorView.valueOrDefault("non-default", "default")).toBe("non-default");
			 });
	     });
	    
	    describe("KeyIndicatorsEditorView: fetch ", function() {
	     	
			 it("apps", function() {
				 expect(keyIndicatorEditorView.fetchApps().length).toBeGreaterThan(1);
			 });
				 
			 it("search", function() {
				 expect(keyIndicatorEditorView.fetchSearch("Errors in the last 24 hours")).not.toBe(null);
			 });
				 
			 it("search (and parse into an associative array)", function() {
				 expect(keyIndicatorEditorView.getNamedArrayFromSearch( keyIndicatorEditorView.fetchSearch("Errors in the last 24 hours")).app).toBe("search");
			 });
				 
	     });
	    
	    describe("KeyIndicatorsEditorView: hasCapability ", function() {
	     	
			 it("that the user possesses", function() {
				 expect(keyIndicatorEditorView.hasCapability("search")).toBe(true);
			 });
				 
			 it("that the user does not possess", function() {
				 expect(keyIndicatorEditorView.hasCapability("asdfasd")).toBe(false);
			 });
				 
	     });

     }
);