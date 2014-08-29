define([
    "jquery",
    "underscore",
    "backbone",
    "app/utils/xml2json",
    "app/utils/json2xml",
    "app/utils/formatXML",
    "app/models/Collection.Model",
    "app/models/View.Model",
    "app/models/Anchor.Model",
    "app/models/Divider.Model"
], function(
    $,
    _,
    Backbone,
    xml2json,
    json2xml,
    formatXML,
    CollectionModel,
    ViewModel,
    AnchorModel,
    DividerModel
) {
    /* this is the parent Backbone.Collection for
     all of the navigation collections holding 
     views, anchors, dividers, sub-collections, etc. */
    return Backbone.Collection.extend({
        initialize: function(models, options) {
            options = options || {};
            this.app = options.app;
            this.type = options.type;
        },
        url: function() {
            var app = $("body").attr("s:app");
            var user = "nobody";
            if (this.type === "container") {
                return Splunk.util.make_url("/splunkd/servicesNS/" + user + "/" + app + "/data/ui/nav?output_mode=json");
            } else if (this.type === "unused") {
                return Splunk.util.make_url("/splunkd/servicesNS/" + user + "/" + app + "/data/ui/views?output_mode=json&count=0");
            }
        },
        parse: function(response) {
            
            if (this.type === "container") {
                this.parseContainer(response);
            } else if (this.type === "unused") {
                this.parseUnused(response);
            }
        },
        parseContainer: function(response) {
            
            var models = [],
                data = response.entry[0].content['eai:data'];
            var xml = new xml2json();
            data = xml.convertXML(data);

            this.attributes = data.attributes;
            this.reset(data.children);
        },
        parseUnused: function(response) {
            // do not add views with 'isVisible=false' as they will not show in the navigation
            var filteredViews = _.filter(response.entry, function(entry) {
                isVisible = entry.content["isVisible"];
                return isVisible === "true" || isVisible === true;
            });
        
            var views = _.map(filteredViews, function(entry) {
                var regex = /<label>.+?<\/label>/,
                    match = entry.content["eai:data"].match(regex);

                match = match ? match[0] : entry.name;
                match = match.replace("<label>", "").replace("</label>", "");
                return {name: match, type: "view", attributes: {name: entry.name}};
            });

            this.reset(views);

        },
        /*
        sort alphabetically by label, only if it's 
        the Unused Dashboards (#unused_views) container.
        */
        comparator: function(model) {
            if (this.type === "unused") {
                return model.get("name").toLowerCase();
            } else {
                return;
            }
        },
        reset: function(array, options) {
            // overwrite the reset method, so that the models are created correctly
            options || (options = {});

            var models,
                that = this;
            if (array[0] instanceof Backbone.Model) {
                models = array;
            } else {
                models = [];
                
                _.each(array, function(obj) {
                    obj.app = that.app;
                    // TODO: eventually move away from this hard coding
                    if (obj.type === "view") {
                        var exists = that.app.viewsById[obj.attributes.name];
                        if (exists) {
                            obj.name = exists.model.get("name");
                            exists.model.set(obj);
                            models.push(exists.model);
                        } else {
                            models.push(new ViewModel(obj));
                        }
                    } else if (obj.type === "collection") {
                        CollectionModel = CollectionModel || require("app/models/Collection.Model");
                        models.push(new CollectionModel(obj));
                    } else if (obj.type === "a") {
                        models.push(new AnchorModel(obj));
                    } else if (obj.type === "divider") {
                        models.push(new DividerModel(obj));
                    }
                });
            }
            
            this._reset(); // use backbone's internal reset method to clear collection

            this.add(models, {silent: true});
            if (!options.silent) {
                this.trigger('reset', this, options);
            }

            return this;
        },
        save: function(callback) {
            var json = this.toJSON(),
                j2x = new json2xml,
                app = $("body").attr("s:app"),
                url = Splunk.util.make_url("/custom/SA-Utils/nav_editor/" + app + "/update_nav"), // change the hard coding
                csrf_key = $('input[name=splunk_form_key]').val(),
                name = "default",
                data = j2x.convertJSON(json);

            data = formatXML(data);
            
            $.ajax({
                type: "POST",
                url: url,
                headers: {
                    'X-Splunk-Form-Key': csrf_key
                },
                data: {
                    'name': name,
                    'data': data
                },
                success: function(data) {
                    
                    var message,
                        alert_type,
                        redirect;
                    if (data.success === "true") {
                        message = "Save successful.  Navigating back to Configurations.";
                        alert_type = "alert-success";
                        redirect = true;
                    } else {
                        message = "Save failed: " + data["error"];
                        alert_type = "alert-danger";
                        redirect = false;
                    }

                    callback(alert_type, message, redirect);
                    
                }
            });
            
        },
        toJSON: function() {
            var json,
                isNav = this.attributes;

            if (isNav) {
                json = {};
                json.type = "nav";
                json.attributes = this.attributes;
                json.children = [];
            } else {
                json = [];
            }
            this.each(function(model) {
                if (isNav) {
                    json.children.push(model.toJSON());
                } else {
                    json.push(model.toJSON());
                }
            });

            return json;
        }
    });
});