define([
    "jquery",
    "underscore",
    "backbone",
    "app/collections/Collections.Collection"
], function(
    $,
    _,
    Backbone,
    CollectionsCollection
) {
    /* 
    Backbone.Model for an individual navigation collection, 
    which aggregates the dashboard views.

    {attributes}
    name: name of collection (or the navigation bar)
    children
    */
    return Backbone.Model.extend({
        initialize: function() {

            this.id = this.cid;
            this.app = this.attributes.app;
            if (!this.get("attributes")) {
                this.set("attributes", {});
            }
            if (!this.get("type")) {
                this.set("type", "collection");
            }

            this.setChildren();
            this.on("change:name", _.bind(this.setName, this));
            this.on("change:children", _.bind(this.setChildren, this));
        },
        setName: function() {
            var name = this.get("name"),
                attributes = this.get("attributes");
            attributes.label = name;

            this.set("attributes", attributes);
        },
        setChildren: function() {
            var children = this.get("children") || [];
            if (this.children) {
                this.children.reset(children);
            } else {
                CollectionsCollection = CollectionsCollection || require("app/collections/Collections.Collection");
                this.children = new CollectionsCollection([], {app: this.app});
                this.children.reset(children);
            }
        },
        toJSON: function() {
            var json = {};
            json.attributes = this.get("attributes");
            json.children = this.children.toJSON();
            json.type = this.get("type");
            json.text = "";

            return json;

        }
    });
});