
require.config({
    paths: {
        key_indicators_view: "../app/SA-Utils/js/views/KeyIndicatorsView"
    }
});

require([
         "jquery",
         "underscore",
         "backbone",
         "key_indicators_view",
         "splunkjs/mvc/simplexml/ready!"
     ], function(
         $,
         _,
         Backbone,
         KeyIndicatorsView
     )
     {
         KeyIndicatorsView.prototype.autodiscover();
     }
);