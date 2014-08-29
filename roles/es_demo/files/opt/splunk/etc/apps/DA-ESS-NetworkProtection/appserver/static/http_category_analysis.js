
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
        lookup_name: "ppf_http_category",
        panel_id: "#table1",
        search_managers: [ mvc.Components.get("search1"), mvc.Components.get("search2")],
        fields: ['category'],
        lookup_edit_view: Splunk.util.make_url("/app/SplunkEnterpriseSecuritySuite/ess_ppf_lookups_edit?path=DA-ESS-NetworkProtection%2Fppf_http_category.csv")
    } );
    
    perPanelFilterView.render();

});