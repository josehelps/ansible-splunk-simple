
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc){

    function make_src_token(value) {            
        // initialize additional tokens to empty strings
        var src = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            src = '(All_Traffic.src="' + value + '" OR All_Traffic.src_ip="' + value + '" OR All_Traffic.src_mac="' + value + '" OR All_Traffic.src_translated_ip="' + value + '")';
        }

        // set new tokens
        submittedTokens.set('src',src);
    }

    function make_dest_token(value) {            
        // initialize additional tokens to empty strings
        var dest = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            dest = '(All_Traffic.dest="' + value + '" OR All_Traffic.dest_ip="' + value + '" OR All_Traffic.dest_mac="' + value + '" OR All_Traffic.dest_translated_ip="' + value + '")';
        }

        // set new tokens
        submittedTokens.set('dest',dest);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
    
    /*------ change handlers ------*/

    // When the src_form token changes...
    submittedTokens.on('change:src_form', function(){
        // if src_form exists
        if(submittedTokens.has('src_form')) { make_src_token(submittedTokens.get('src_form')); }
    });
    
    // When the dest_form token changes...
    submittedTokens.on('change:dest_form', function(){
        // if dest_form exists
        if(submittedTokens.has('dest_form')) { make_dest_token(submittedTokens.get('dest_form')); }
    });

    /*------ initialization handlers ------*/
    if(submittedTokens.has('src_form')) { make_src_token(submittedTokens.get('src_form')); }	
    if(submittedTokens.has('dest_form')) { make_dest_token(submittedTokens.get('dest_form')); }	
	
    
    /*------ datamodel search optimization ------*/
	// If search1 (| tstats) is finished and has returned 0 results, finalize search2 (| datamodel)
	// This will help cases where no results are found be faster
	var tstatsSearch = mvc.Components.get('search1');
	var datamodelSearch = mvc.Components.get('search2');

	setTimeout(function() {
		tstatsSearch.on('search:done', function() {
			var tstatsProps = tstatsSearch.get('data');
			var datamodelProps = datamodelSearch.get('data');
	
			if (tstatsProps.isDone && tstatsProps.resultCount===0 && datamodelProps.eventCount===0) {
				console.log('tstats search complete and returned 0 results, finalizing data model search');
				datamodelSearch.finalize();
			}
		}, this);
	
		// Note that the above event may never be hit, because the search
		// may already be done.
		tstatsSearch.replayLastSearchEvent(this);
	}, 3000);
	
});