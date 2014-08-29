
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc){

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