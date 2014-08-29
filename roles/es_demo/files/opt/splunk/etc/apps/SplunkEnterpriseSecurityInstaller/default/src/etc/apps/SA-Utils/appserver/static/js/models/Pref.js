define([
    'jquery',
    'underscore',
    'backbone',
    'app/sync/URLSync',
    'splunk.util'
], function(
    $,
    _,
    Backbone,
    URLSync
) {
    return Backbone.Model.extend({
        defaults: {
            changes: [
            ],
            file_name: 'prefs',
            selected: 'Default',
            user_name: Splunk.util.getConfigValue('USERNAME')
        },
        initialize: function() { 
            this.debounceSave = _.debounce(this.save, 500);
            this.urlSync = new URLSync(this.get('component_id'), this.id);
            this.sync = _.debounce(this._sync, 25, this);
        },
        _sync: function(method, model, options) {
            options = options || {};
            if (options.isNew) {
                options.data = options.data || {};
                method = 'create';
                options.url = this.onCreateURL();
                options.data = $.extend(options.data, this.getPOSTData(method, model));
            }
            // Uncomment this if you want to constantly sync with the URL
            // this.urlSync.sync(method, model, options);
            return Backbone.sync.apply(this, arguments);
        },
        getPOSTData: function(method, model) {
            return {
                'name': model.id,
                'model': JSON.stringify(model.toJSON())
            };
        },
        onCreateURL: function() {
            return url = Splunk.util.make_url([
                'splunkd',
                'servicesNS',
                this.get('user_name'),
                this.get('app_name'),
                'configs',
                'conf-'+this.get('component_id')+'_'+this.get('file_name')+
                '?output_mode=json'
            ].join('/'));
        },
        toJSON: function(options) {
            var output = _.clone(this.attributes);
            delete output.app_name;
            delete output.changes;
            delete output.component_id;
            delete output.entry;
            delete output.file_name;
            delete output.generator;
            delete output.links;
            delete output.messages;
            delete output.origin;
            delete output.paging;
            delete output.updated;
            delete output.user_name;
            return output;
        },
        url: function() {
            return url = Splunk.util.make_url([
                'splunkd',
                'servicesNS',
                this.get('user_name'),
                this.get('app_name'),
                'configs',
                'conf-'+this.get('component_id')+'_'+this.get('file_name'),
                this.id+'?output_mode=json'
            ].join('/'));
        },
        clearClickedEvents: function() {
            _.each(this.get("lane_prefs"), function(lane_pref) {
                lane_pref.clicked = [];
            });
            this.save();
        }
    });
});

