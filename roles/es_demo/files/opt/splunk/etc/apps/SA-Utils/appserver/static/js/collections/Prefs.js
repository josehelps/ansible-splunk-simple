define([
    'jquery',
    'underscore',
    'backbone',
    'app/models/Pref',
    'app/sync/URLSync',
    'splunk.util'
], function(
    $,
    _,
    Backbone,
    Pref,
    URLSync
) {
    return Backbone.Collection.extend({
        model: Pref,
        initialize: function(models, options) {
            this.app_name = options.app_name;
            this.field_name = options.field_name;
            this.file_name = 'prefs';
            this.id = options.id;
            this.changes = options.changes || [];
            this.user_name = Splunk.util.getConfigValue('USERNAME');
            this.on('add', _.bind(this.onModelAdd, this));
            this.urlSync = new URLSync(this.id, false, this.field_name);
        },
        getPref: function(pref_id) {
            var pref = this.get(pref_id);
            if (!pref) {
                pref = new Pref({
                  app_name: this.app_name,
                  component_id: this.id,
                  file_name: this.file_name,
                  id: pref_id,
                  name: pref_id,
                  view_name: this.view_name,
                  entity_name: this.entity_name
                });
                this.add(pref);
            }
            return pref;
        },
        onModelAdd: function(model) {
            model.save([], {isNew: true});
        },
        sync: function(method, model, options) {
            var entity = this.urlSync.getEntityName();

            if (method.toLowerCase()!=='read') {
                throw new Error('invalid method: ' + method);
            }

            if (entity) {
                this.entity_name = entity; 
            }
             
            if (this.urlSync.exists()) {
                return this.urlSync.sync(method, model, options);
            } else {
                return Backbone.sync.apply(this, arguments);
            }
        },
        parse: function(content, options) {
          if(options.parseUrl){
            return this.parseURL(content, options);
          } else {
            var app_name = this.app_name,
                self = this,
                changes = this.changes,
                component_id = this.id,
                entity_name = this.entity_name,
                file_name = this.file_name,
                field_name = this.field_name,
                user_name = this.user_name, 
                output = _.compact(_.map(
                    content.entry,
                    function(item) {
                        if (item.content.model) { 
                            output = JSON.parse(item.content.model);
                            output.name = output.id = item.name;
                            output.app_name = app_name;
                            output.changes = changes;
                            output.file_name = file_name;
                            output.component_id = component_id;
                            if(output.entity_name !== undefined){
                                self.entity_name = output.entity_name;
                            }
                            output[field_name] = entity_name || output[field_name];
                            output.entity_name = entity_name || output.entity_name;
                            return output;
                        }
                    }
                ));

            return output;
          }

        },
        parseURL: function(content, options){
            var self = this,
                output = [];

            _.each(content, function(item){
              item.app_name = self.app_name;
              item.file_name = self.file_name;
              item.component_id = self.id;
              output.push(item);
            });

            return output;
        },
        url: function() {
            return url = Splunk.util.make_url([
                'splunkd', 
                'servicesNS', 
                this.user_name,
                this.app_name,
                'configs',
                'conf-'+this.id+'_'+this.file_name+'?output_mode=json'
            ].join('/'));
        },
        serializeToURL: function(options){
            return this.urlSync.createURL(this.models, options);
        }
    });
});

