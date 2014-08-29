// Get the endpoint in case the root endpoint has been modified
endpoint = document.location.pathname.substring( 0, document.location.pathname.indexOf("custom") );

require.config({
    baseUrl: endpoint + "/static/app/SA-Utils/scripts/contrib/",
    paths: {
        "app": "..",
        "underscore": "underscore",
        "backbone": "backbone",
        "jquery.ui.sortable": "jquery.ui.sortable",
        "mediator": "mediator",
        "xml2json": "xml2json",
        "bootstrap.modal": "bootstrap/bootstrap-modal",
        "bootstrap.tooltip": "bootstrap/bootstrap-tooltip",
        "bootstrap.alert": "bootstrap/bootstrap-alert",
        "bootstrap.popover": "bootstrap/bootstrap-popover",
        "App.View": endpoint + "static/app/SA-Utils/scripts/views/App.View"
    },
    shim: {
        "underscore": {
            exports: "_"
        },
        "backbone": {
            deps: ["underscore", "jquery"],
            exports: "Backbone"
        },
        "bootstrap.modal": {
            deps: ['jquery']
        },
        "bootstrap.tooltip": {
            deps: ['jquery']
        },
        "bootstrap.alert": {
            deps: ['jquery']
        },
        "bootstrap.popover": {
            deps: ['jquery', 'bootstrap.tooltip']
        }
    }
});

require([
    "jquery",
    "underscore",
    "backbone",
    "App.View",
    endpoint + "config?autoload=1"
], function(
    $,
    _,
    Backbone,
    AppView
) {

    var app = {};
    app.viewsById = {}; // all views (anchors, views, dividers, collections) with their id as key

    // render views
    var appView = new AppView({
            app: app
        });

    appView.render();

    window.appView = appView;
});