
require.config({
    paths: {
        key_indicator_editor_view: "../app/SA-Utils/js/views/KeyIndicatorEditorView"
    }
});

require([
         "jquery",
         "underscore",
         "backbone",
         "key_indicator_editor_view",
         "splunkjs/mvc/simplexml/ready!"
     ], function($, _, Backbone, KeyIndicatorEditorView)
     {
         var keyIndicatorEditorView = new KeyIndicatorEditorView({
        	 'el': $("#key_indicator_editor"),
        	 'default_app': 'SplunkEnterpriseSecuritySuite',
        	 'list_link' : 'ess_custom_searches_list',
        	 'list_link_title' : 'Back to Custom Searches'});
         
         keyIndicatorEditorView.render();
     }
);