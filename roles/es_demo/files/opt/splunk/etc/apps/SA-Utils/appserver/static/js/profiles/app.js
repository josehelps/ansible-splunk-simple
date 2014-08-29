var config = {
    baseUrl: "/en-US/static/js",
    paths: {
        'app': '../app/SA-Utils/js/',
        'lib': '../app/SA-Utils/js/lib/',
        'backbone-mediator': '../app/SA-Utils/js/lib/backbone-mediator',
        'd3': '../app/SA-Utils/js/lib/d3.v3',
        'entityUtils': '../app/SA-Utils/js/util/entity_utils'
    },
    shim: {
        d3: {
            exports: 'd3'
        }
    },
    enforceDefine: false
};

require.config(config);
