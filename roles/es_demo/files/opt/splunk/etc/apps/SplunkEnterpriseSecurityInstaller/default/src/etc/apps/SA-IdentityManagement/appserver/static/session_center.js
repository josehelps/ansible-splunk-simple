
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc){

    function make_session_tokens(value) {            
        // initialize additional tokens to empty strings
        var srch = '',
        	session_details = '| datamodel Network_Sessions All_Sessions search | `drop_dm_object_name("All_Sessions")` | `unprepend_assets("dest")` | `mvappend_field(src,src_ip)` | `mvappend_field(src,src_mac)` | `mvappend_field(src,src_nt_host)` | `mvappend_field(src,src_dns)` | head 1000 | table _time,src,ip,mac,nt_host,dns,user';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            srch = '(All_Sessions.src_ip="' + value + '" OR All_Sessions.src_mac="' + value + '" OR All_Sessions.src_nt_host="' + value + '" OR All_Sessions.src_dns="' + value + '" OR All_Sessions.dest_ip="' + value + '" OR All_Sessions.dest_mac="' + value + '" OR All_Sessions.dest_nt_host="' + value + '" OR All_Sessions.dest_dns="' + value + '" OR All_Sessions.user="' + value + '")';
            session_details = '| tstats `summariesonly` latest(All_Sessions.src_ip) as src_ip,latest(All_Sessions.src_mac) as src_mac,latest(All_Sessions.src_nt_host) as src_nt_host,latest(All_Sesions.src_dns) as src_dns from datamodel=Network_Sessions where ' + srch + ' by _time,All_Sessions.dest_ip,All_Sessions.dest_mac,All_Sessions.dest_nt_host,All_Sessions.dest_dns span=1s | `drop_dm_object_name("All_Sessions")` | `unprepend_assets("dest")` | `mvappend_field(src,src_ip)` | `mvappend_field(src,src_mac)` | `mvappend_field(src,src_nt_host)` | `mvappend_field(src,src_dns)` | sort - _time | fields _time,src,ip,mac,nt_host,dns,user';
        }

        // set new tokens
        submittedTokens.set('srch',srch);
        submittedTokens.set('session_details',session_details);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
    
    /*------ change handlers ------*/

    // When the srch_form token changes...
    submittedTokens.on('change:srch_form', function(){
        // if srch_form exists
        if(submittedTokens.has('srch_form')) { make_session_tokens(submittedTokens.get('srch_form')); }
    });
    
    /*------ initialization handlers ------*/
    if(submittedTokens.has('srch_form')) { make_session_tokens(submittedTokens.get('srch_form')); }	

});