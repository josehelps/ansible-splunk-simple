
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc){

    function make_bunit_token(value) {            
        // initialize additional tokens to empty strings
        var bunit = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            bunit = '(Authentication.src_bunit="' + value + '" OR Authentication.dest_bunit="' + value + '" OR Authentication.src_user_bunit="' + value + '" OR Authentication.user_bunit="' + value + '")';
        }

        // set new tokens
        submittedTokens.set('bunit',bunit);
    }

    function make_category_token(value) {            
        // initialize additional tokens to empty strings
        var category = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            category = '(Authentication.src_category="' + value + '" OR Authentication.dest_category="' + value + '" OR Authentication.src_user_category="' + value + '" OR Authentication.user_category="' + value + '")';
        }

        // set new tokens
        submittedTokens.set('category',category);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
    
    /*------ change handlers ------*/

    // When the bunit_form token changes...
    submittedTokens.on('change:bunit_form', function(){
        // if bunit_form exists
        if(submittedTokens.has('bunit_form')) { make_bunit_token(submittedTokens.get('bunit_form')); }
    });
    
    // When the category_form token changes...
    submittedTokens.on('change:category_form', function(){
        // if category_form exists
        if(submittedTokens.has('category_form')) { make_category_token(submittedTokens.get('category_form')); }
    });

    /*------ initialization handlers ------*/
    if(submittedTokens.has('bunit_form')) { make_bunit_token(submittedTokens.get('bunit_form')); }	
    if(submittedTokens.has('category_form')) { make_category_token(submittedTokens.get('category_form')); }	

});