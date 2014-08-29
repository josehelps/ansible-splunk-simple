
require.config({
    paths: {
        swimlane_editor_view: "../app/SA-Utils/js/views/SwimlaneEditorView"
    }
});

require([
         "jquery",
         "underscore",
         "backbone",
         "swimlane_editor_view",
         "splunkjs/mvc/simplexml/ready!"
     ], function($, _, Backbone, SwimlaneEditorView)
     {
         var swimlaneEditorView = new SwimlaneEditorView({
        	 'el': $("#swimlane_editor"),
        	 'default_app': 'SplunkEnterpriseSecuritySuite',
        	 'list_link' : 'ess_custom_searches_list',
        	 'list_link_title' : 'Back to Custom Searches'});
         
         swimlaneEditorView.render();
     }
);