
//Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require.config({
    paths: {
        ad_hoc_risk_score: '../app/SA-ThreatIntelligence/js/views/AdHocRiskScoreView'
    }
});

require(['jquery','underscore','splunkjs/mvc', 'ad_hoc_risk_score', 'splunkjs/mvc/simplexml/ready!'],
		function($, _, mvc, AdHocRiskScoreView){
	
	function reverse_lookup(value, constraint_method) {
		var clause=null;
		$.ajax(
				{
					url:  Splunk.util.make_url('custom/SA-Utils/identitymapper/reverse_lookup?value=' + value + "&constraint_fields=All_Risk.risk_object&constraint_method=" + constraint_method),
					type: 'GET',
					// async=false is required to use the result outside the callback.
					async: false,
					success: function(data,textStatus,jqXHR){
						clause = data.clauses[0];
					},
					
					error: function(jqXHR,textStatus,errorThrown) {
						alert("Unable to retrieve search criteria.");
					}
				}
		);
		return clause;
	}
	
	function make_risk_object_token(val, obj) {            

		var clause='';

		if (val !== null && val !== '' && obj !== null && obj !== '') {
			
			if (obj === 'All_Risk.risk_object_type="system"') {
				clause = reverse_lookup(val, 'reverse_asset_lookup');
			}
			else if (obj === 'All_Risk.risk_object_type="user"') {
				clause = reverse_lookup(val, 'reverse_identity_lookup');
			}
			else {
				clause = 'All_Risk.risk_object="' + val + '"';
			}
		}
		
		// set new tokens
		submittedTokens.set('risk_object',clause);
	}
	
	// Get Submitted Tokens
	var submittedTokens = mvc.Components.get('submitted');
	/*------ change handlers ------*/
	
	// When the risk_object_type token changes...
	submittedTokens.on('change:risk_object_type change:risk_object_form', function(){
		// if form exists
		if(submittedTokens.has('risk_object_type') && submittedTokens.has('risk_object_form')) { make_risk_object_token(submittedTokens.get('risk_object_form'),submittedTokens.get('risk_object_type')); }
	});
	
	/*------ initialization handlers ------*/
	if(submittedTokens.has('risk_object_type') && submittedTokens.has('risk_object_form')) { make_risk_object_token(submittedTokens.get('risk_object_form'),submittedTokens.get('risk_object_type')); }	
	
    // Render the ad-hoc risk score dialog
    var adHocRiskScoreView = new AdHocRiskScoreView({
        el: $('#adhocdialog')
    });
    
    // Render the ad-hoc risk dialog
    adHocRiskScoreView.render();
	
});