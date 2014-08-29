// Test authors:
// You only need to change one thing in this file to register your tests cases.
// Declare the paths of the resources you need for testing below, and your done!
var test_script_paths = {
        test_key_indicators_view: '../app/SplunkEnterpriseSecuritySuite/js/tests/TestKeyIndicatorsView'
};




/**
 * Boilerplate below: no need to edit.
 **/

// Define the require paths with the Jasmine dependencies
var paths = {
        jasmine: "//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine",
        jasmine_html: "//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine-html"
    };

// Merge in the test scripts
for (var test_script in test_script_paths) { paths[test_script] = test_script_paths[test_script]; }

// Configure require
require.config({
    paths: paths,
	shim: {
	    'jasmine_html': {
	        deps: ['jasmine', 'jquery']
	    }
	}
});

// Make the require dependencies
var dependencies = ["jquery",
                    "underscore",
                    "backbone",
                    "jasmine",
                    "jasmine_html"];

// Add the test scripts so that they get loaded
for(test_script in test_script_paths){
	dependencies.push(test_script);
}

// Add the ready call
dependencies.push("splunkjs/mvc/simplexml/ready!");

// Let's do this thing...
require(dependencies, function($, _, Backbone)
     {
	
	    function addStylesheet( filename ){
	    
	        // For Internet Explorer, use createStyleSheet since adding a stylesheet using a link tag will not be recognized
	        // (http://stackoverflow.com/questions/1184950/dynamically-loading-css-stylesheet-doesnt-work-on-ie)
	        if( document.createStyleSheet ){
	            document.createStyleSheet(filename);
	        }
	        // For everyone else
	        else{
	            var link = $("<link>");
	            link.attr({type: 'text/css',rel: 'stylesheet', href: filename});
	            $("head").append( link );
	        }
	    }
	    
         addStylesheet('//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine.css');
         
         // Setup jasmine for execution    
         (function() {
         	
         	// Configure the environment
         	var jasmineEnv = jasmine.getEnv();
         	jasmineEnv.updateInterval = 250;
         	  
         	// Use the HTML reporter for displaying the results
     	    var htmlReporter = new jasmine.HtmlReporter();
     	    jasmineEnv.addReporter(htmlReporter);
     	    
     	    jasmineEnv.specFilter = function(spec) {
     	        return htmlReporter.specFilter(spec);
     	    };
     	    
     	    var currentWindowOnload = window.onload;
     	    window.onload = function() {
     	      if (currentWindowOnload) {
     	        currentWindowOnload();
     	      }
     	
     	      // Add the version number
     	      //document.querySelector('.version').innerHTML = jasmineEnv.versionString();
     	      //execJasmine();
     	    };
     	
     	    function execJasmine() {
     	    	
           	  $('.shared-footer').hide();
     	    
     	      jasmineEnv.execute();
     	    }
     	    
     	    // Hide the view content
     	    $('#dashboard').hide();
     	    
     	    // Reset the body margin because it looks ugly
     	    $('body').css('margin', '0px');
     	    
     	    // Start Jasmine in a bit
     	    setTimeout(execJasmine, 2000);
     	    
     	  })();

     }
);