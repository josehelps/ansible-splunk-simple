
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require.config({
    paths: {
        per_panel_filtering_cell_renderer: '../app/SA-Utils/js/views/PerPanelFilteringCellRenderer',
        per_panel_filter_view: '../app/SA-Utils/js/views/PerPanelFilterView'
    }
});

require(['jquery','underscore','splunkjs/mvc', 'per_panel_filtering_cell_renderer', 'per_panel_filter_view', 'splunkjs/mvc/simplexml/ready!'],
    function($, _, mvc, PerPanelFilteringCellRenderer, PerPanelFilterView){

    function make_Z_token(value) {            
        // initialize additional tokens to empty strings
        var Z = 'Web.http_user_agent_length>0';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            Z = '[| inputlookup append=T user_agent_length_tracker | search Z=' + value + ' | fields search]';
        }

        // set new tokens
        submittedTokens.set('Z',Z);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
    
    /*------ change handlers ------*/

    // When the Z_form token changes...
    submittedTokens.on('change:Z_form', function(){
        // if Z_form exists
        if(submittedTokens.has('Z_form')) { make_Z_token(submittedTokens.get('Z_form')); }
    });

    /*------ initialization handlers ------*/
    if(submittedTokens.has('Z_form')) { make_Z_token(submittedTokens.get('Z_form')); }
    
    /*------ per panel filtering ------*/
	
    // Add the checkbox to the table
    var table1Element = mvc.Components.get('table1');

    table1Element.getVisualization(function(tableView){
        tableView.table.addCellRenderer(new PerPanelFilteringCellRenderer());
        tableView.table.render();
    });
    
    // Setup the per panel filter
    var perPanelFilterView = new PerPanelFilterView( {
        namespace: "DA-ESS-NetworkProtection",
        el: $('#ppf'),
        lookup_name: "ppf_http_user_agent",
        panel_id: "#table1",
        search_managers: [ mvc.Components.get("search1"), mvc.Components.get("search2")],
        fields: ['http_user_agent'],
        lookup_edit_view: Splunk.util.make_url("/app/SplunkEnterpriseSecuritySuite/ess_ppf_lookups_edit?path=DA-ESS-NetworkProtection%2Fppf_http_user_agent.csv")
    } );
    
    perPanelFilterView.render();

});