
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc){

    function make_is_expected_tokens(value) {            
        // initialize additional tokens to empty strings
        var host_is_expected = '',
            dest_is_expected = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            host_is_expected = 'host_is_expected="' + value + '"';
            dest_is_expected = 'All_Application_State.dest_is_expected="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('host_is_expected',host_is_expected);
        submittedTokens.set('dest_is_expected',dest_is_expected);
    }

    function make_system_tokens(value) {            
        // initialize additional tokens to empty strings
        var host = '',
            dest = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            host = 'host="' + value + '"';
            dest = 'All_Application_State.dest="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('host',host);
        submittedTokens.set('dest',dest);
    }

    function make_bunit_tokens(value) {            
        // initialize additional tokens to empty strings
        var host_bunit = '',
            dest_bunit = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            host_bunit = '(host_bunit="' + value + '" OR host_owner_bunit="' + value + '")';
            dest_bunit = 'All_Application_State.dest_bunit="' + value + '"';
        }

        // set new tokens
        submittedTokens.set('host_bunit',host_bunit);
        submittedTokens.set('dest_bunit',dest_bunit);
    }

    function make_category_tokens(value) {
        // initialize additional tokens to empty strings
        var host_category = '';
        var dest_category = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            host_category = '(host_category="' + value + '" OR host_owner_category="' + value + '")';
            dest_category = 'All_Application_State.dest_category="' + value + '"';
        }
            
        // set new tokens
        submittedTokens.set('host_category',host_category);
        submittedTokens.set('dest_category',dest_category);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
    
    /*------ change handlers ------*/

    // When the is_expected token changes...
    submittedTokens.on('change:is_expected', function(){
        // if is_expected exists
        if(submittedTokens.has('is_expected')) { make_is_expected_tokens(submittedTokens.get('is_expected')); }
    });
    
    // When the system token changes...
    submittedTokens.on('change:system', function(){
        // if system exists
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
    if(submittedTokens.has('is_expected')) { make_is_expected_tokens(submittedTokens.get('is_expected')); }
    if(submittedTokens.has('system')) { make_system_tokens(submittedTokens.get('system')); }
    if(submittedTokens.has('bunit')) { make_bunit_tokens(submittedTokens.get('bunit')); }
    if(submittedTokens.has('category')) { make_category_tokens(submittedTokens.get('category')); }

});