
require.config({
    paths: {
        custom_search_list_view: "../app/SplunkEnterpriseSecuritySuite/js/views/CustomSearchListView"
    }
});

require([
         "jquery",
         "underscore",
         "backbone",
         "custom_search_list_view",
         "splunkjs/mvc/simplexml/ready!"
     ], function($, _, Backbone, CustomSearchListView)
     {
         var customSearchList = new CustomSearchListView({
        	 'el': $(".custom_search_list #list_table")
        	 });
         
         customSearchList.render();
     }
);