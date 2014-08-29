define([
    "jquery",
    "underscore",
    "backbone",
    "bootstrap.popover",
    "text!app/templates/Name.Template.html",
    "text!app/templates/Collection.Template.html",
    "app/views/View.View",
    "app/views/Divider.View",
    "app/views/Anchor.View"
], function(
    $,
    _,
    Backbone,
    popover,
    NameTemplate,
    CollectionTemplate,
    ViewView,
    DividerView,
    AnchorView
) {
    // view for the Collection.Model
    var CollectionView = Backbone.View.extend({
        className: "collection sortable",
        initialize: function() {
            this.app = this.options.app;
            this.model = this.options.model;

            this.model.on("change:name", _.bind(this.renderName, this));
            // this.model.on("change:children", _.bind(this.renderChildren, this));
        },
        render: function() {
            this.$el.attr("data-id", this.options["data-id"]);
            this.$el.html(_.template(CollectionTemplate));
            this.renderName();
            this.renderChildren();
            return this;
        },
        renderName: function() {
            this.$(".nameContainer:first").html(_.template(NameTemplate, this.model.attributes));
            if (this.isAddCollection()) {
                this.$(".removeCollection:first").hide();
            }

        },
        renderChildren: function() {
            var that = this; // there's gotta be a better way to do this...the same code is repeated in App.View
            this.model.children.each(function(model) {
                var type = model.get("type"),
                    input = {app: that.app, model: model, "data-id": model.id},
                    view;
                if (type === "view") {
                    var exists = that.app.viewsById[model.get("attributes").name];
                    if (exists) {
                        view = exists;
                    } else {
                        view = new ViewView(input);
                    }
                } else if (type === "collection") {
                    view = new CollectionView(input);
                } else if (type === "divider") {
                    view = new DividerView(input);
                } else if (type === "a") {
                    view = new AnchorView(input);
                }

                that.app.viewsById[model.id] = view;
                that.$(".childrenContainer:first").append(view.render().el);
            });
        },
        isAddCollection: function() {
            // is this CollectionView instance for adding a new instance?
            return this.$el.hasClass("addNewCollection");
        },
        events: {
            "click .editName:first": "editName",
            "keyup .editingName:first": "editingName",
            "blur .editingName:first": "cancelEdit",
            "click .removeCollection:first": "removeCollection"

        },
        isEditing: function() {
            return this.$(".editName:first").is(":hidden");
        },
        editName: function() {

            this.$(".editName:first").hide();
            this.$(".editingName:first").show();
            this.$(".editingName").focus();
        },
        finishEdit: function() {
            this.$(".editingName:first").hide();
            this.$(".editName:first").show();

            this.$(".nameContainer:first").popover("destroy");
            // this.invalidInputPopover.popover("hide");
        },
        editingName: function(e) {
            this.$(".nameContainer:first").popover("destroy");
            var key = e.key || e.which || e.keyCode,
                val,
                KEY_VAL_ENTER = 13,
                KEY_VAL_ESC = 27;

            if (key === KEY_VAL_ENTER) {
                /* if user hits RETURN, save */
                val = $(e.target).val();
                if (this.validateEdit(val) && this.validLength(val)) {
                    this.submitEdit(val);
                } else if (!this.validLength(val)) {
                    this.$(".nameContainer:first").popover({trigger: "manual", content: 'Input must be between 1 to 256 characters.'});
                    this.$(".nameContainer:first").popover("show");
                } else if (!this.validateEdit(val)) {
                    this.$(".nameContainer:first").popover({trigger: "manual", content: 'Input is limited to alphanumeric and underscore characters.'});
                    this.$(".nameContainer:first").popover("show");
                }
                
            } else if (key === KEY_VAL_ESC) {
                /* if user hits ESC, cancel */
                this.cancelEdit();
            }
        },
        validateEdit: function(val) {
            re = /^[A-Z0-9 _]+$/gi;
            return re.test(val);
        },
        validLength: function(str) {
            return (str.length > 0 && str.length < 256);
        },
        submitEdit: function(val) {
            if (this.isAddCollection()) {
                this.$(".removeCollection:first").show();
                this.$el.removeClass("addNewCollection");
                this.$el.addClass("sortable");
                this.$el.trigger("addedCollection");
                // this.addViewsView();
            }

            this.model.set("name", val);
            this.finishEdit();
        },
        cancelEdit: function() {
            this.renderName();
            if (!this.isAddCollection()) {
                this.finishEdit();
            }
        },
        save: function() {
            var models = [],
                that = this;
            this.$(".childrenContainer:first").children().each(function(i, child) {
                var id = $(child).attr("data-id"),
                    view = that.app.viewsById[id],
                    model = view.model;
                if (model.get("type") === "collection") {
                    view.save();
                }
                models.push(model);
            });
            this.model.set("children", models);
        },
        removeCollection: function () {
            this.$el.remove();
            delete this.app.viewsById[this.model.id];
        }
    });

    return CollectionView;
});