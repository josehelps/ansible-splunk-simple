//splunk cmd node $SPLUNK_HOME/lib/node_modules/requirejs/bin/r.js -o homepage.build.profile.js
({
    preserveLicenseComments: false,
    name: 'app/components/investigator',
    optimize: 'uglify2',
    generateSourceMaps: true,         
    include: [  "splunkjs/mvc/headerview", "splunkjs/mvc/simplexml" ],
    out: '../build/investigator.built.js',
    mainConfigFile: './shared.js',
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
    stubModules: [],
    uglify2: {
        //Example of a specialized config. If you are fine
        //with the default options, no need to specify
        //any of these properties.
        output: {
            beautify: false 
        },
        compress: {
            sequences: false,
            properties: false,
            global_defs: {
                DEBUG: false
            }
        },
        warnings: false,
        mangle: false
    },
    enforceDefine: false
})
