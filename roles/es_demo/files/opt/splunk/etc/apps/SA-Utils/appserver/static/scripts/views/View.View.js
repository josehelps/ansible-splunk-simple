define([
    "jquery",
    "underscore",
    "backbone",
    "bootstrap.tooltip",
    "text!app/templates/View.Template.html"
], function(
    $,
    _,
    Backbone,
    tooltip,
    ViewTemplate
) {
    /* view for View.Model */
    return Backbone.View.extend({
        className: "view sortable",
        initialize: function() {
            this.app = this.options.app;
            this.model = this.options.model;

            this.model.on("change", _.bind(this.render, this));
        },
        render: function() {
            this.$el.attr("data-id", this.options["data-id"]);
            this.$el.html(_.template(ViewTemplate, this.model.attributes));
            this.$(".view_tooltip").tooltip({placement: "bottom"});

            return this;
        },
        save: function() {
            // since no children, just give back the model
            return this.model;
        },
        showDefault: function() {
            this.$(".default").show();
            this.$(".removeView").show();
        },
        hideDefault: function() {
            // if under "Unused Views" container, should know show the 
            // default or remove button
            this.$(".default").hide();
            this.$(".removeView").hide();
        },
        events: {
            "mouseover": "mouseover",
            "mouseleave": "mouseleave",
            "click .default": "clickDefault",
            "click .removeView": "removeView"
        },
        mouseover: function() {
            this.$(".disabled").addClass("hover");
        },
        mouseleave: function() {
            this.$(".disabled").removeClass("hover");
        },
        clickDefault: function() {
            var prevModel = _.chain(this.app.viewsById)
                .map(function(view) {
                    return view.model;
                }).filter(function(model) {
                    var attributes = model.get("attributes");
                    if (attributes) {
                        return model.get("attributes")["default"];
                    }
                }).value()[0];

            if (prevModel !== this.model) {
                var prevAttrs = prevModel.get("attributes"),
                    attrs = this.model.get("attributes");

                delete prevAttrs["default"];
                attrs["default"] = "true";

                prevModel.set("attributes", prevAttrs);
                prevModel.trigger("change");
                this.model.set("attributes", attrs);
                this.model.trigger("change");  // why do i have to manually do this...?

                //TODO: don't make unused views default LOL
            }
        },
        /*
        remove the view element 
        */
        removeView: function() {
            this.hideDefault();
            this.$el.removeClass("top");

            this.alphabeticallyAppend();
        },
        /*
        append the view where alphabetically appropriate under Unused Dashboards
        */
        alphabeticallyAppend: function() {
            var name = $.trim(this.$el.text()).toLowerCase(),
                that = this;
            $("#unused_views").children().each(function() {
                var viewName = $.trim($(this).text()).toLowerCase();
                if (name < viewName) {
                    $(this).before(that.el);
                    return false;
                }
            });
        }
    });
});