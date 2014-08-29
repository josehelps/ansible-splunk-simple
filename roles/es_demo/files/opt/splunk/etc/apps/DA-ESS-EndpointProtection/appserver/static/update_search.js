
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc){

    function make_signature_tokens(value) {            
        // initialize signature_token to empty strings
        var dm_signature = '',
        	signature = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
        	dm_signature = '(Updates.signature_id="' + value + '" OR Updates.signature="' + value + '")';
        	signature = '(signature_id="' + value + '" OR signature="' + value + '")';
        }

        // set new tokens
        submittedTokens.set('dm_signature',dm_signature);
        submittedTokens.set('signature',signature);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
      
    /*------ change handlers ------*/

    // When the signature token changes...
    submittedTokens.on('change:signature_form', function(){
        // if signature exists
        if(submittedTokens.has('signature_form')) { make_signature_tokens(submittedTokens.get('signature_form')); }
    });
    
    /*------ initialization handlers ------*/
    if(submittedTokens.has('signature_form')) { make_signature_tokens(submittedTokens.get('signature_form')); }
    
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