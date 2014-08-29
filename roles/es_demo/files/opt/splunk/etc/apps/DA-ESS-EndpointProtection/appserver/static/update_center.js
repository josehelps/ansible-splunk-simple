
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc){
	
    function make_dest_should_update_tokens(value) {            
        // initialize additional tokens to empty strings
        var update_dsu = '',
        	appstate_dsu = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            update_dsu = 'Updates.dest_should_update="' + value + '"';
            appstate_dsu = 'All_Application_State.dest_should_update="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('update_dsu',update_dsu);
        submittedTokens.set('appstate_dsu',appstate_dsu);
    }
    
    function make_dest_tokens(value) {            
        // initialize additional tokens to empty strings
        var update_dest = '',
        	appstate_dest = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            update_dest = 'Updates.dest="' + value + '"';
            appstate_dest = 'All_Application_State.dest="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('update_dest',update_dest);
        submittedTokens.set('appstate_dest',appstate_dest);
    }

    function make_bunit_tokens(value) {            
        // initialize additional tokens to empty strings
        var update_bunit = '',
        	appstate_bunit = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            update_bunit = 'Updates.dest_bunit="' + value + '"';
            appstate_bunit = '(All_Application_State.dest_bunit="' + value + '" OR All_Application_State.user_bunit="' + value + '")';
        }

        // set new tokens
        submittedTokens.set('update_bunit',update_bunit);
        submittedTokens.set('appstate_bunit',appstate_bunit);
    }

    function make_category_tokens(value) {            
        // initialize additional tokens to empty strings
        var update_category = '',
        	appstate_category = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            update_category = 'Updates.dest_category="' + value + '"';
            appstate_category = '(All_Application_State.dest_category="' + value + '" OR All_Application_State.user_category="' + value + '")';
        }

        // set new tokens
        submittedTokens.set('update_category',update_category);
        submittedTokens.set('appstate_category',appstate_category);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
    
    /*------ change handlers ------*/
    // When the dest_should_update token changes...
    submittedTokens.on('change:dest_should_update', function(){
        // if dest_should_update exists
        if(submittedTokens.has('dest_should_update')) { make_dest_should_update_tokens(submittedTokens.get('dest_should_update')); }
    });
    
    // When the dest token changes...
    submittedTokens.on('change:dest', function(){
        // if dest exists
        if(submittedTokens.has('dest')) { make_dest_tokens(submittedTokens.get('dest')); }
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
    if(submittedTokens.has('dest_should_update')) { make_dest_should_update_tokens(submittedTokens.get('dest_should_update')); }
    if(submittedTokens.has('dest')) { make_dest_tokens(submittedTokens.get('dest')); }
    if(submittedTokens.has('bunit')) { make_bunit_tokens(submittedTokens.get('bunit')); }	
    if(submittedTokens.has('category')) { make_category_tokens(submittedTokens.get('category')); }	
});