require.config({
    paths: {
        key_indicators_view: "../app/SA-Utils/js/views/KeyIndicatorsView",
        key_indicator_view: '../app/SA-Utils/js/views/KeyIndicatorView',
        jasmine: "//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine"
    }
});

require([
         "jquery",
         "underscore",
         "backbone",
         "key_indicators_view",
         "key_indicator_view",
         "jasmine",
         "splunkjs/mvc/simplexml/ready!"
     ], function(
         $,
         _,
         Backbone,
         KeyIndicatorsView,
         KeyIndicatorView
     )
     {
	
	    // Make a key indicator
	    var key_indicator_el = $('<div></div>');
	    var search = {};
	  	 
	    var keyIndicatorView = new KeyIndicatorView({
	        search: search,
	        el: key_indicator_el
	    });
	
	    describe("KeyIndicatorView: Conversion of raw number to human readable number", function() {
	     	
			 // Test number in the billions
			 it("when it in the billions", function() {
				 expect( keyIndicatorView.getHumanReadableNumber(7000000000) ).toBe( "7B" );
			 });
			 
			 // Test number in the trillions
			 it("when it in the trillions", function() {
				 expect( keyIndicatorView.getHumanReadableNumber(7000000000000) ).toBe( "7T" );
			 });
			 
			 // Test number in the millions
			 it("when it in the millions", function() {
				 expect( keyIndicatorView.getHumanReadableNumber(7000000) ).toBe( "7M" );
			 });
			 
			 // Test number in the thousands
			 it("when it in the thousands", function() {
				 expect( keyIndicatorView.getHumanReadableNumber(7000) ).toBe( "7k" );
			 });
			 
			 // Test rounding when in the thousands
			 it("rounding up when it in the thousands", function() {
				 expect( keyIndicatorView.getHumanReadableNumber(7183) ).toBe( "7k" );
			 });
			 
			 // Test rounding
			 it("rounding up", function() {
				 expect( keyIndicatorView.getHumanReadableNumber(7.183) ).toBe( "7.2" );
			 });
	
	     });
		 
	    describe("KeyIndicatorView: Trim function", function() {
			 
			 // Trimming
			 it("with whitespace on both sides", function() {
				 expect( keyIndicatorView.trim(" trim me ") ).toBe( "trim me" );
			 });
	     });
	    
	    describe("KeyIndicatorView: Get value or default", function() {
			 
			 // Value is undefined
			 it("when value is undefined", function() {
				 expect( keyIndicatorView.getValueOrDefault(undefined, "some value") ).toBe("some value");
			 });
			 
			 // Value is undefined
			 it("when value is defined", function() {
				 expect( keyIndicatorView.getValueOrDefault("some other value", "some value") ).toBe("some other value");
			 });
			 
			 // Value is a float
			 it("with conversion to float", function() {
				 expect( keyIndicatorView.getFloatValueOrDefault("3.14159265", undefined) ).toBe(3.14159265);
			 });
			 
			 // Value is a boolean
			 it("with conversion to boolean from 0", function() {
				 expect( keyIndicatorView.getBooleanValueOrDefault("0", undefined) ).toBe(false);
			 });
			 
			 // Value is a boolean
			 it("with conversion to boolean from 1", function() {
				 expect( keyIndicatorView.getBooleanValueOrDefault("1", undefined) ).toBe(true);
			 });
			 
			 // Value is a boolean
			 it("with conversion to boolean from 'true'", function() {
				 expect( keyIndicatorView.getBooleanValueOrDefault("true", undefined) ).toBe(true);
			 });
			 
			 // Value is a boolean
			 it("with conversion to boolean from 'false'", function() {
				 expect( keyIndicatorView.getBooleanValueOrDefault("false", undefined) ).toBe(false);
			 });
			 
			 // Value is a boolean
			 it("with conversion to boolean from 'fALse'", function() {
				 expect( keyIndicatorView.getBooleanValueOrDefault("false", undefined) ).toBe(false);
			 });
			 
			 // Value is a boolean
			 it("with conversion to boolean from 't'", function() {
				 expect( keyIndicatorView.getBooleanValueOrDefault("t", undefined) ).toBe(true);
			 });
			 
			 // Value is a boolean
			 it("with conversion to boolean from 'f'", function() {
				 expect( keyIndicatorView.getBooleanValueOrDefault("f", undefined) ).toBe(false);
			 });
			 
	     });
	    
	     describe("KeyIndicatorView: Variable substitution from results or action fields", function() {
			 
			 it("when field exists in results and in search content", function() {
				 
				 var search = {};
				 search.content = {"foo_action" : "quux"};
				 
				 var results = {'foo' : 'bar'};
				 
				 expect( keyIndicatorView.getFromActionOrResult("foo", "foo_action", search, results, "uh oh") ).toBe( "quux" );
			 });
	    	 
			 it("when field exists in results but not in search content", function() {
				 
				 var search = {};
				 search.content = {"not_foo_action" : "quux"};
				 
				 var results = {'foo' : 'bar'};
				 
				 expect( keyIndicatorView.getFromActionOrResult("foo", "foo_action", search, results, "uh oh") ).toBe( "bar" );
			 });
			 
			 it("when field does not exist in results but in search content", function() {
				 
				 var search = {};
				 search.content = {"foo_action" : "quux"};
				 
				 var results = {'foo_not' : 'bar'};
				 
				 expect( keyIndicatorView.getFromActionOrResult("foo", "foo_action", search, results, "uh oh") ).toBe( "quux" );
			 });
			 
			 it("when field does not exist in results or search content", function() {
				 
				 var search = {};
				 search.content = {"not_foo_action" : "quux"};
				 
				 var results = {'foo_not' : 'bar'};
				 
				 expect( keyIndicatorView.getFromActionOrResult("foo", "foo_action", search, results, "not found") ).toBe( "not found" );
			 });
			 
	     });
	    
	     describe("KeyIndicatorView: Variable substitution from results", function() {
			 
			 it("using basic substitution", function() {
				 expect( keyIndicatorView.substituteVariablesFromResult("The variable for foo should be $foo$", {'foo' : 'bar'}) ).toBe( "The variable for foo should be bar" );
			 });
	     });
	     
	     describe("KeyIndicatorView: Checking if valid integer", function() {
			 
			 it("with a positive number", function() {
				 expect( keyIndicatorView.isValidInteger("123") ).toBe(true);
			 });
			 
			 it("with a negative number", function() {
				 expect( keyIndicatorView.isValidInteger("-123") ).toBe(true);
			 });
			 
			 it("with a non-number", function() {
				 expect( keyIndicatorView.isValidInteger("abc") ).toBe(false);
			 });
			 
			 it("with empty space", function() {
				 expect( keyIndicatorView.isValidInteger("") ).toBe(false);
			 });
			 
			 it("with a number followed by a some non-numeric characters", function() {
				 expect( keyIndicatorView.isValidInteger("123abc") ).toBe(false);
			 });
	     });
	     
	     describe("KeyIndicatorView: Executing search", function() {
			 
			 it("with parameters defined via constructor arguments", function() {
				    var this_key_indicator_el = $('<div></div>');
				    var search = {};
				  	 
				    var thisKeyIndicatorView = new KeyIndicatorView({
				    	search_string: "search * | head 1 | eval current=1 | eval delta=-1",
				    	title: "Test",
				        el: this_key_indicator_el
				    });
				    
				    expect( thisKeyIndicatorView.startGettingResults() ).not.toBe(null);
			 });
			 
	     });
	     
	     describe("KeyIndicatorView: Units conversion", function() {
			 
			 it("from thousands", function() {
				    expect( keyIndicatorView.getActualNumberFromHumanReadable("1k") ).toBe(1000);
			 });
	    	 
			 it("from millions", function() {
				    expect( keyIndicatorView.getActualNumberFromHumanReadable("1m") ).toBe(1000000);
			 });
			 
			 it("from millions with decimal", function() {
				    expect( keyIndicatorView.getActualNumberFromHumanReadable("1.2m") ).toBe(1200000);
			 });
			 
			 it("from millions with a space", function() {
				    expect( keyIndicatorView.getActualNumberFromHumanReadable("1  m") ).toBe(1000000);
			 });
			 
			 it("with upper case units", function() {
				    expect( keyIndicatorView.getActualNumberFromHumanReadable("1M") ).toBe(1000000);
			 });
			 
			 it("with no units", function() {
				    expect( keyIndicatorView.getActualNumberFromHumanReadable("2") ).toBe(2);
			 });
			 
			 it("with invalid value", function() {
				    expect( keyIndicatorView.getActualNumberFromHumanReadable("cm2") ).toBe(null);
			 });
			 
			 it("with negative value", function() {
				    expect( keyIndicatorView.getActualNumberFromHumanReadable("-1.2m") ).toBe(-1200000);
			 });
			 
	     });
	     
	     /*
	     describe("KeyIndicatorView: Checking if threshold value can be loaded from editing interface", function() {
			 
			 it("when set to a invalid string that starts with a number", function() {
				 $('.threshold', keyIndicatorView.$el).val("123abc");
				 expect( keyIndicatorView.getThresholdFormValue() ).toBe("123");
			 });
			 
	     });
	     
	     describe("KeyIndicatorView: Checking if threshold validation works", function() {
			 
			 it("when left to the default", function() {
				 expect( keyIndicatorView.isThresholdFormValueValid() ).toBe(true);
			 });
			 
			 it("when set to a valid value", function() {
				 $('.threshold', key_indicator_el).val("123");
				 expect( keyIndicatorView.isThresholdFormValueValid() ).toBe(true);
			 });
			 
			 it("when set to a invalid string", function() {
				 $('.threshold', keyIndicatorView.$el).val("abc");
				 expect( keyIndicatorView.isThresholdFormValueValid() ).toBe(false);
			 });
			 
			 it("when set to a invalid string that starts with a number", function() {
				 $('.threshold', keyIndicatorView.$el).val("123abc");
				 expect( keyIndicatorView.isThresholdFormValueValid() ).toBe(false);
			 });
			 
	     });
	     */
	     

     }
);