
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
	function($, _, mvc){
	
		function make_search_template() {
			var searchTemplate = '`tstats` count from datamodel=Intrusion_Detection where * $IDS_Attacks.ip$ by _time,IDS_Attacks.src,IDS_Attacks.dest span=10m | `drop_dm_object_name("IDS_Attacks")` | `tstats` append=true count from datamodel=Network_Traffic where * $All_Traffic.ip$ by _time,All_Traffic.src,All_Traffic.dest span=10m | `drop_dm_object_name("All_Traffic")` | `tstats` append=true count from datamodel=Web where * $Web.ip$ by _time,Web.src,Web.dest span=10m | `tstats` append=true count from datamodel=Web where * $Web.url$ by _time,Web.url span=10m | `drop_dm_object_name("Web")` | fillnull value="unknown" src,dest,url | stats count by _time,src,dest,url | `threatlist_lookup_extended` | search $threatlist$ | eval threatlist_name=mvappend(src_threatlist_name,dest_threatlist_name,url_threatlist_name) | eval risk_score=count*(src_risk_score+dest_risk_score+url_risk_score)';
			var drilldownTemplate = 'search (tag=network tag=communicate) OR (tag=ids tag=attack) OR (tag=web)'; 
			
			if (submittedTokens.has('model')) {
				model = submittedTokens.get('model');
				
				if (model === 'Intrusion_Detection') {
					searchTemplate = 'tstats `summariesonly` count from datamodel=Intrusion_Detection where * $IDS_Attacks.ip$ by _time,IDS_Attacks.src,IDS_Attacks.dest span=10m | `drop_dm_object_name("IDS_Attacks")` | `threatlist_lookup_extended` | search $threatlist$ | eval threatlist_name=mvappend(src_threatlist_name,NULL,dest_threatlist_name) | eval risk_score=count*(src_risk_score+dest_risk_score)';
					drilldownTemplate = '| `datamodel("Intrusion_Detection","IDS_Attacks")` | `drop_dm_object_name("IDS_Attacks")`';
				}
				
				else if (model === 'Network_Traffic') {
					searchTemplate = 'tstats `summariesonly` count from datamodel=Network_Traffic where * $All_Traffic.ip$ by _time,All_Traffic.src,All_Traffic.dest span=10m | `drop_dm_object_name("All_Traffic")` | `threatlist_lookup_extended` | search $threatlist$ | eval threatlist_name=mvappend(src_threatlist_name,NULL,dest_threatlist_name) | eval risk_score=count*(src_risk_score+dest_risk_score)'; 
					drilldownTemplate = '| `datamodel("Network_Traffic","All_Traffic")` | `drop_dm_object_name("All_Traffic")`';
				}
				
				else if (model === 'Web_by_ip') {
					searchTemplate = 'tstats `summariesonly` count from datamodel=Web where * $Web.ip$ by _time,Web.src,Web.dest span=10m | `drop_dm_object_name("Web")` | `threatlist_lookup_extended` | search $threatlist$ | eval threatlist_name=mvappend(src_threatlist_name,NULL,dest_threatlist_name) | eval risk_score=count*(src_risk_score+dest_risk_score)'; 
					drilldownTemplate = '| `datamodel("Web","Web")` | `drop_dm_object_name("Web")`';
				}

				else if (model === 'Web_by_url') {
					searchTemplate = 'tstats `summariesonly` count from datamodel=Web where * $Web.url$ by _time,Web.url span=10m | `drop_dm_object_name("Web")` | `threatlist_lookup_extended` | search $threatlist$ | eval threatlist_name=url_threatlist_name | eval risk_score=count*url_risk_score'; 
					drilldownTemplate = '| `datamodel("Web","Web")` | `drop_dm_object_name("Web")`';
				}

			}
			
			var ids_ip = '',
				traffic_ip = '',
				web_ip = '';
				web_url = '';
			
			if (submittedTokens.has('ip')) {
				var ip = submittedTokens.get('ip');
				
				if (ip !== null && ip !== '') {
					ids_ip = '(IDS_Attacks.src="' + ip + '" OR IDS_Attacks.dest="' + ip + '")';
					traffic_ip = '(All_Traffic.src="' + ip + '" OR All_Traffic.dest="' + ip + '")';
					// Domain and IP searches are left-anchored only; URLs are wildcarded on both ends.
					web_ip = '(Web.src="*' + ip + '" OR Web.dest="*' + ip + '")';
					web_url = '(Web.url="*' + ip + '*")';
				}
			}
			
			searchTemplate = searchTemplate.replace('$IDS_Attacks.ip$',ids_ip);
			searchTemplate = searchTemplate.replace('$All_Traffic.ip$',traffic_ip);
			searchTemplate = searchTemplate.replace('$Web.ip$',web_ip);
			searchTemplate = searchTemplate.replace('$Web.url$',web_url);
			
			var threatlist_replace = '(src_threatlist_name="*" OR dest_threatlist_name="*" OR url_threatlist_name="*")';
			
			if (submittedTokens.has('threatlist')) {
				threatlist = submittedTokens.get('threatlist');
				
				if (threatlist !== null && threatlist !== '') {
					threatlist_replace = '(src_threatlist_name="' + threatlist + '" OR dest_threatlist_name="' + threatlist + '" OR url_threatlist_name="' + threatlist + '")';
				}
			}
			
			searchTemplate = searchTemplate.replace('$threatlist$',threatlist_replace);

			submittedTokens.set('searchTemplate',searchTemplate);
			submittedTokens.set('drilldownTemplate',drilldownTemplate);
		}
		
		// Token Handling
		var submittedTokens = mvc.Components.get('submitted');
	
		// Change handler registration
		submittedTokens.on('change:model change:ip change:threatlist', _.debounce(function(){
			make_search_template();
		}));
		
		// Initialization
		make_search_template();
		
	});