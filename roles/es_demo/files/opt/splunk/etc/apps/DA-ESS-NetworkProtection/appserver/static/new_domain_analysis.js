
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
    
    function make_domain_token(value) {            
        // initialize additional tokens to empty strings
        var domain = '';
            
        // update tokens if value is positive
        if (value !== null && value !== '') {
            domain = '(dest="*' + value + '" OR domain="*' + value + '" OR resolved_domain="*' + value + '")';
        }

        // set new tokens
        submittedTokens.set('domain',domain);
    }
	
    function make_domain_type_tokens(value) {            
        // initialize additional tokens to empty strings
        var domain_type = '',
        	age_type = '';
            
        // update tokens if value is positive
        if (value === 'newly_registered') {
        	domain_type = '(created=* NOT created="unknown")';
        	age_type    = 'created';
        }
        
        if (value === 'newly_seen') {
        	domain_type = 'newly_seen=*';
        	age_type    = 'newly_seen';
        }

        // set new tokens
        submittedTokens.set('domain_type',domain_type);
        submittedTokens.set('age_type',age_type);
    }

    // Get Submitted Tokens
    var submittedTokens = mvc.Components.get('submitted');
    
    /*------ change handlers ------*/
    
    // When the domain_form token changes...
    submittedTokens.on('change:domain_form', function(){
        // if domain_form exists
        if(submittedTokens.has('domain_form')) { make_domain_token(submittedTokens.get('domain_form')); }
    });
    
    // When the domain_type_form token changes...
    submittedTokens.on('change:domain_type_form', function(){
        // if domain_type_form exists
        if(submittedTokens.has('domain_type_form')) { make_domain_type_tokens(submittedTokens.get('domain_type_form')); }
    });

    /*------ initialization handlers ------*/
    if(submittedTokens.has('domain_form')) { make_domain_token(submittedTokens.get('domain_form').trim()); }	
    if(submittedTokens.has('domain_type_form')) { make_domain_type_tokens(submittedTokens.get('domain_type_form')); }	
    
    
    /*------ per panel filtering ------*/
	
    // Add the checkbox to the table
    var table1Element = mvc.Components.get('table1');
    var table2Element = mvc.Components.get('table2');
    
    table1Element.getVisualization(function(tableView){
        tableView.table.addCellRenderer(new PerPanelFilteringCellRenderer({'show_checkboxes': false}));
        tableView.table.render();
    });

    table2Element.getVisualization(function(tableView){
        tableView.table.addCellRenderer(new PerPanelFilteringCellRenderer());
        tableView.table.render();
    });
    
    // Setup the per panel filter
    var perPanelFilterView = new PerPanelFilterView( {
        namespace: "DA-ESS-NetworkProtection",
        el: $('#ppf'),
        lookup_name: "ppf_new_domains",
        panel_id: "#table2",
        search_managers: [ mvc.Components.get("search1"), mvc.Components.get("search2"), mvc.Components.get("search3"),  mvc.Components.get("search4")],
        fields: ['domain'],
        lookup_edit_view: Splunk.util.make_url("/app/SplunkEnterpriseSecuritySuite/ess_ppf_lookups_edit?path=DA-ESS-NetworkProtection%2Fppf_new_domains.csv")
    } );
    
    perPanelFilterView.render();

});