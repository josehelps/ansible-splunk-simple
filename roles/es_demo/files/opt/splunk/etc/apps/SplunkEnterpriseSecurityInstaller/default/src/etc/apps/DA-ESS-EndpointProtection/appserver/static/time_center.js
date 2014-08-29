
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc){
	
    function make_should_timesync_tokens(value) {            
        // initialize additional tokens to empty strings
        var performance_dst = '',
        	appstate_dst = '',
        	host_should_timesync = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            performance_dst = 'All_Performance.dest_should_timesync="' + value + '"';
            appstate_dst = 'All_Application_State.dest_should_timesync="' + value + '"';
            host_should_timesync = 'orig_host_should_timesync="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('performance_dst',performance_dst);
        submittedTokens.set('appstate_dst',appstate_dst);
        submittedTokens.set('host_should_timesync',host_should_timesync);
    }
    
    function make_system_tokens(value) {            
        // initialize additional tokens to empty strings
        var performance_dest = '',
        	appstate_dest = '',
        	host = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            performance_dest = 'All_Performance.dest="' + value + '"';
            appstate_dest = 'All_Application_State.dest="' + value + '"';
            host = 'orig_host="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('performance_dest',performance_dest);
        submittedTokens.set('appstate_dest',appstate_dest);
        submittedTokens.set('host',host);
    }

    function make_bunit_tokens(value) {            
        // initialize additional tokens to empty strings
        var performance_bunit = '',
        	appstate_bunit = '',
        	host_bunit = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            performance_bunit = 'All_Performance.dest_bunit="' + value + '"';
            appstate_bunit = 'All_Application_State.dest_bunit="' + value + '"';
            host_bunit = 'orig_host_bunit="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('performance_bunit',performance_bunit);
        submittedTokens.set('appstate_bunit',appstate_bunit);
        submittedTokens.set('host_bunit',host_bunit);
    }

    function make_category_tokens(value) {            
        // initialize additional tokens to empty strings
        var performance_category = '',
        	appstate_category = '',
        	host_category = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            performance_category = 'All_Performance.dest_category="' + value + '"';
            appstate_category = 'All_Application_State.dest_category="' + value + '"';
            host_category = 'orig_host_category="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('performance_category',performance_category);
        submittedTokens.set('appstate_category',appstate_category);
        submittedTokens.set('host_category',host_category);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
    
    /*------ change handlers ------*/
    // When the should_timesync token changes...
    submittedTokens.on('change:should_timesync', function(){
        // if should_timesync exists
        if(submittedTokens.has('should_timesync')) { make_should_timesync_tokens(submittedTokens.get('should_timesync')); }
    });
    
    // When the dest token changes...
    submittedTokens.on('change:system', function(){
        // if dest exists
        if(submittedTokens.has('system')) { make_system_tokens(submittedTokens.get('system')); }
    });
    
    // When the bunit token changes...
    submittedTokens.on('change:bunit', function(){
        // if bunit exists
        if(submittedTokens.has('bunit')) { make_bunit_tokens(submittedTokens.get('bunit')); }
    });
    
    // When the category token changes...
    submittedTokens.on('change:category', function(){
        // if category exists
        if(submittedTokens.has('category')) { make_category_tokens(submittedTokens.get('category')); }
    });

    /*------ initialization handlers ------*/
    if(submittedTokens.has('should_timesync')) { make_should_timesync_tokens(submittedTokens.get('should_timesync')); }
    if(submittedTokens.has('system')) { make_system_tokens(submittedTokens.get('system')); }
    if(submittedTokens.has('bunit')) { make_bunit_tokens(submittedTokens.get('bunit')); }	
    if(submittedTokens.has('category')) { make_category_tokens(submittedTokens.get('category')); }	
});