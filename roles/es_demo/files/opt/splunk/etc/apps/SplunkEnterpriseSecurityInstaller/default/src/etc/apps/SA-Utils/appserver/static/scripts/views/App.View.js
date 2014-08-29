define([
    "jquery",
    "underscore",
    "backbone",
    "jquery.ui.sortable",
    "app/views/Alert.View",
    "app/views/Collection.View",
    "app/views/View.View",
    "app/views/Divider.View",
    "app/views/Anchor.View",
    "app/models/Collection.Model",
    "app/models/View.Model",
    "app/models/Anchor.Model",
    "app/models/Divider.Model",
    "app/collections/Collections.Collection"
], function(
    $,
    _,
    Backbone,
    sortable,
    AlertView,
    CollectionView,
    ViewView,
    DividerView,
    AnchorView,
    CollectionModel,
    ViewModel,
    AnchorModel,
    DividerModel,
    CollectionsCollection
) {
    /* 
    master orchestrator for the whole app UI
    takes care of Unused Views and View Container
    unused: Collections.Collection of all unused views
    container: Collections.Collection of all views, collections, anchors, dividers
    */
    return Backbone.View.extend({
        el: "body",
        initialize: function() {
            this.app = this.options.app;
            this.unused = this.options.unused || new CollectionsCollection([], {app: this.app, type: "unused"});
            this.container = this.options.container || new CollectionsCollection([], {app: this.app, type: "container"});

            var that = this;
            this.unused.on("reset", function() {
                that.renderUnused();
                that.container.fetch();
            });
            this.container.on("reset", _.bind(this.renderContainer, this));

            this.unused.on("reset", _.bind(this.renderUnused, this));
        },
        render: function() {
            // manually calculate height of Unused Dashboards and Unused Links
            this.$("#unused_views, #unused_anchors").height(function() {
                var siblingsHeight = 0,
                    parentHeight = $(this).parent().height();
                $(this).siblings().each(function() {
                    siblingsHeight += $(this).outerHeight();
                });
                return parentHeight - siblingsHeight - 10;
            });

            this.unused.fetch();
        },
        renderContainer: function() {
            this.emptyContainer();
            this.renderAllContainer();
            this.addNewCollection();
            this.addNewDivider();
            this.addAlert();

            this.sortable();
        },
        renderUnused: function() {
            this.emptyUnused();
            this.renderAllUnused();

        },
        emptyContainer: function() {
            this.$("#view_container").empty();
        },
        emptyUnused: function() {
            this.$("#unused_views").empty();
        },
        /*
        renderAllContainer: renders the view container, after this.container makes
        a call to data/ui/nav and gets back default.xml.  Takes the models in
        the collection and creates a corresponding view.
        */
        renderAllContainer: function() {
            var that = this;
            this.container.each(function(model) {
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
                that.$("#view_container").append(view.render().el);
                view.$el.addClass("top");
            });
        },
        /*
        renderAllUnused: called after this.unused (a Collections.Collection) gets back
        all views available to the app, and renders it in #unused_views.
        */
        renderAllUnused: function() {
            var that = this;
            this.unused.each(function(model) {
                var view = new ViewView({app: that.app, model: model, "data-id": model.id});
                that.$("#unused_views").append(view.render().el);
                view.hideDefault();

                that.app.viewsById[model.id] = view;
            });
        },
        sortable: function() {
            $("#view_container, #unused_views, #unused_anchors, #add_dividers_container, .childrenContainer").sortable({
                connectWith: ".ui-sortable",
                placeholder: "placeholder",
                items: "> .sortable",
                tolerance: "pointer",
                scroll: "false",
                start: _.bind(this.sortStart, this),
                sort: _.bind(this.sort,this),
                stop: _.bind(this.sortStop, this)
            });
        },
        sortStart: function(e, ui) {
            ui.item.after("<div class='sort_placeholder' />");
            ui.item.addClass("above");
        },
        sort: function(e, ui) {
            
        },
        /*
        sortStop: checks at the end of a sort, after the element has been dropped
        if the element belongs in the new parent container.  If not, reverts the
        element back to its original parent container
        */
        sortStop: function(e, ui) {
            ui.item.removeClass("above");
            var parent = ui.item.parent(),
                id = ui.item.attr("data-id"),
                view = this.app.viewsById[id];
            // only views can be placed in unused views
            if (parent.is("#unused_views")
                && !ui.item.is(".view")) {
                $(".sort_placeholder").after(ui.item);
            }
            // only anchors are allowed in unused anchors
            if (parent.is("#unused_anchors")
                && !ui.item.is(".anchor")) {
                $(".sort_placeholder").after(ui.item);
            }
            // dividers can only be in collections
            if (ui.item.is(".divider")
                && !parent.is(".childrenContainer")
                && !parent.is("#view_container")) {
                $(".sort_placeholder").after(ui.item);
            } else if (ui.item.is(".divider.addNewDivider")) {
                this.addedDivider();
            }

            if (!parent.is("#unused_views")
                && (ui.item.is(".view")
                    || ui.item.is(".anchor"))) {
                // if a view was dropped into view container   
                view.showDefault();

                // and if it was dropped to the top
                if (parent.is("#view_container")) {
                    view.$el.addClass("top");
                } else {
                    view.$el.removeClass("top");
                }

            }
            // if a view was dropped in Unused Dashboard
            if (parent.is("#unused_views") 
                && ui.item.is(".view")) {
                view.hideDefault();
                view.$el.removeClass("top");

                view.alphabeticallyAppend();
            }
            // if an anchor was dropped in Unused Links
            if (parent.is("#unused_anchors") 
                && ui.item.is(".anchor")) {

                view.hideDefault();
                view.$el.removeClass("top");
            }

            $(".sort_placeholder").remove();
        },
        /*
        renders the empty collection at the end of #view_container, allowing a user
        to input a label and create a new <collection></collection>.
        */
        addNewCollection: function() {
            // render the "add new" collection
            var model = new CollectionModel();
            this.addCollection = new CollectionView({
                app: this.app,
                className: "collection addNewCollection",
                model: model,
                "data-id": model.id
            });
            this.app.viewsById[model.id] = this.addCollection;
            this.$("#view_container").append(this.addCollection.render().el);
            this.addCollection.$el.addClass("top");
        },
        /*
        renders a new divider in #add_dividers_container, allowing a user 
        to drag and drop a new <divider></divider>
        */
        addNewDivider: function() {
            var model = new DividerModel();
            this.addDivider = new DividerView({
                app: this.app,
                className: "divider addNewDivider sortable",
                model: model,
                "data-id": model.id
            });
            this.app.viewsById[model.id] = this.addDivider;
            this.$("#add_dividers_container").append(this.addDivider.render().el);
        },
        /*
        renders a new alert at the top of the screen to display success/error messages.
        only called once by AppView.render().
        */
        addAlert: function() {
        	this.alert = new AlertView();
            this.$("#alerts").append(this.alert.render().el);
        },
        /* events */
        events: {
            "click #saveButton": "save",
            "click #cancelButton": "cancel",
            "addedCollection .collection": "addedCollection",
            "keydown #addAnchor": "addAnchor",
            "blur #addAnchor": "blurAddAnchor"
        },
        /*
        saves the nav.  first reads the DOM and updates the models, then
        resets this.container with the updated models, and finally hits the REST endpoint.
        */
        save: function() {
            var models = [],
                that = this;
            this.$("#view_container").children(":not(.addNewCollection)")
                .each(function(i, child) {
                    var id = $(child).attr("data-id"),
                        view = that.app.viewsById[id],
                        model = view.model;
                    if (model.get("type") === "collection") {
                        view.save();
                    }
                    models.push(model);
                });
            this.container.reset(models, {silent: true});

            /* have this.container hit the REST endpoint and save the new
             nav, and perform the callback. */
            this.container.save(function(alert_type, message, redirect) {
            	that.alert.displayMessage(alert_type, message, redirect);

                if (redirect) {
                    setTimeout(function() {
                        window.top.location.href = Splunk.util.make_url("/app/SplunkEnterpriseSecuritySuite/ess_configuration");
                    }, 2000);
                }
            });
        },
        /*
        redirects the user back to the configuration page/
        */
        cancel: function() {
            this.alert.displayMessage("alert-danger", "Cancelling edit and navigating back to the configuration page.", true);
            setTimeout(function() {
                    window.top.location.href = Splunk.util.make_url("/app/SplunkEnterpriseSecuritySuite/ess_configuration");
                }, 1500);
        },
        addedCollection: function() {
            this.container.add(this.addCollection.model);
            this.addNewCollection();

            this.sortable();
        },
        addedDivider: function() {
            this.addDivider.dropped();
            this.container.add(this.addDivider.model);
            this.addNewDivider();

            this.sortable();
        },
        addAnchor: function(e) {
            $(e.target).popover("destroy");
            var key = e.key || e.which || e.keyCode,
                val,
                KEY_VAL_ENTER = 13,
                KEY_VAL_ESC = 27;

            if (key === KEY_VAL_ENTER) {
                val = $(e.target).val();
                if (this.validInput(val) && this.validLength(val)) {
                    var model = new AnchorModel({text: val}),
                        view = new AnchorView({
                            "data-id": model.id,
                            app: this.app,
                            model: model
                        });
                    this.$("#unused_anchors").prepend(view.render().el);
                    this.app.viewsById[model.id] = view;
                    view.hideDefault();

                    this.sortable();  // does it rebind every time?

                    $(e.target).val("");
                    $(e.target).blur();    
                } else if (!this.validLength(val)) {
                    $(e.target).popover({
                        trigger: "manual", 
                        placement: "bottom",
                        content: 'Input must be between 1 to 256 characters.'
                    });
                    $(e.target).popover("show");
                } else if (!this.validInput(val)) {
                    $(e.target).popover({
                        trigger: "manual", 
                        placement: "bottom",
                        content: 'Input is limited to alphanumeric and underscore characters.'
                    });
                    $(e.target).popover("show");
                } 
               
            } else if (key === KEY_VAL_ESC) {
                $(e.target).blur();
            }
        },
        validInput: function(val) {
            re = /^[A-Z0-9 _]+$/gi;
            return re.test(val);
        },
        validLength: function(str) {
            return (str.length > 0 && str.length < 256);
        },
        blurAddAnchor: function(e) {
            $(e.target).val("");
            $(e.target).popover("destroy");
        }
    });
});