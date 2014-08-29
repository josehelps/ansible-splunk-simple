
require.config({
    paths: {
        correlation_search_editor_view: "../app/SA-ThreatIntelligence/js/views/CorrelationSearchEditorView"
    }
});

require([
         "jquery",
         "underscore",
         "backbone",
         "correlation_search_editor_view",
         "splunkjs/mvc/simplexml/ready!"
     ], function($, _, Backbone, CorrelationSearchEditorView)
     {
         var correlationSearchEditorView = new CorrelationSearchEditorView({
        	 'el': $("#correlation_search_editor"),
        	 'list_link' : 'ess_custom_searches_list',
        	 'list_link_title' : 'Back to Custom Searches'
         });
         
         correlationSearchEditorView.render();
     }
);