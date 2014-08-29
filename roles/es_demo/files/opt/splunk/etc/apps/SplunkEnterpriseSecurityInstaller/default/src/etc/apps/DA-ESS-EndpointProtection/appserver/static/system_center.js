
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc){
	
    function make_dest_tokens(value) {            
        // initialize additional tokens to empty strings
        var dest = '',
        	performance_dest = '',
        	appstate_dest = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            dest = 'dest="' + value + '"';
            performance_dest = 'All_Performance.dest="' + value + '"';
            appstate_dest = 'All_Application_State.dest="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('dest',dest);
        submittedTokens.set('performance_dest',performance_dest);
        submittedTokens.set('appstate_dest',appstate_dest);
    }

    function make_bunit_tokens(value) {            
        // initialize additional tokens to empty strings
        var dest_bunit = '',
        	performance_bunit = '',
        	appstate_bunit = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            dest_bunit = 'dest_bunit="' + value + '"';
            performance_bunit = 'All_Performance.dest_bunit="' + value + '"';
            appstate_bunit = '(All_Application_State.dest_bunit="' + value + '" OR All_Application_State.user_bunit="' + value + '")';
        }

        // set new tokens
        submittedTokens.set('dest_bunit',dest_bunit);
        submittedTokens.set('performance_bunit',performance_bunit);
        submittedTokens.set('appstate_bunit',appstate_bunit);
    }

    function make_category_tokens(value) {            
        // initialize additional tokens to empty strings
        var dest_category = '',
        	performance_category = '',
        	appstate_category = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            dest_category = 'dest_category="' + value + '"';
            performance_category = 'All_Performance.dest_category="' + value + '"';
            appstate_category = '(All_Application_State.dest_category="' + value + '" OR All_Application_State.user_category="' + value + '")';
        }

        // set new tokens
        submittedTokens.set('dest_category',dest_category);
        submittedTokens.set('performance_category',performance_category);
        submittedTokens.set('appstate_category',appstate_category);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
    
    /*------ change handlers ------*/
    // When the dest token changes...
    submittedTokens.on('change:dest_form', function(){
        // if dest exists
        if(submittedTokens.has('dest_form')) { make_dest_tokens(submittedTokens.get('dest_form')); }
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
    if(submittedTokens.has('dest_form')) { make_dest_tokens(submittedTokens.get('dest_form')); }
    if(submittedTokens.has('bunit')) { make_bunit_tokens(submittedTokens.get('bunit')); }	
    if(submittedTokens.has('category')) { make_category_tokens(submittedTokens.get('category')); }	
});