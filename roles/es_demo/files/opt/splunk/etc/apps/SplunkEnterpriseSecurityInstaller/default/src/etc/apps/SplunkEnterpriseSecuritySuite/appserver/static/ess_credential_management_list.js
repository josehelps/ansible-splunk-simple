
require.config({
    paths: {
        credential_manager_view: "../app/SA-Utils/js/views/CredentialListView"
    }
});

require([
         "jquery",
         "underscore",
         "backbone",
         "credential_manager_view",
         "splunkjs/mvc/simplexml/ready!"
     ], function(
         $,
         _,
         Backbone,
         CredentialListView
     )
     {
         var credentialListView = new CredentialListView({'el': $(".credential_management_list #credential_table"), 'default_app': 'SplunkEnterpriseSecuritySuite'});
         credentialListView.render();
     }
);