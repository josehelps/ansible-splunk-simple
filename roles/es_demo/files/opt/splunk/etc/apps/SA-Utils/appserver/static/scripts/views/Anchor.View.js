define([
    "jquery",
    "underscore",
    "backbone",
    "bootstrap.modal",
    "text!app/templates/Anchor.Template.html",
    "app/views/Alert.View"
], function(
    $,
    _,
    Backbone,
    modal,
    AnchorTemplate,
    AlertView
) {
    return Backbone.View.extend({
        className: "anchor sortable",
        initialize: function() {
            this.app = this.options.app;
            this.model = this.options.model;
        },
        render: function() {
            this.$el.attr("data-id", this.options["data-id"]);
            this.$el.html(_.template(AnchorTemplate, this.model.attributes));
            this.$(".modal").modal({keyboard: false, show: false});
            this.renderAlert();

            return this;
        },
        renderAlert: function() {
            this.alert = new AlertView();
            this.$(".modal-body").append(this.alert.render().el);
        },
        showDefault: function() {
            this.$(".removeAnchor").show();
        },
        hideDefault: function() {
            // if under "Unused Views" container, should not show the remove button
            this.$(".removeAnchor").hide();
        },
        events: {
            "click .edit": "openModal",
            "keydown .modal input": "keydown",
            "mouseover": "mouseover",
            "mouseleave": "mouseleave",
            "click .removeAnchor": "removeAnchor"
        },
        openModal: function() {
            this.$(".modal").modal("show");
        },
        keydown: function(e) {
            $(e.target).popover("destroy");
            var key = e.key || e.which || e.keyCode,
                KEY_VAL_ENTER = 13,
                KEY_VAL_ESC = 27;

            if (key === KEY_VAL_ENTER) {
                /* if user hits RETURN, save */
                var val = $(e.target).val();
                if (this.validLength(val)) {
                    this.submitEdit(e);                    
                } else {
                    $(e.target).popover({trigger: "manual", content: 'Input must be between 1 to 256 characters.'});
                    $(e.target).popover("show");
                }
            } else if (key === KEY_VAL_ESC) {
                /* if user hits ESC, cancel */
                this.cancelEdit(e);
            }
        },
        mouseover: function() {
            this.$(".disabled").addClass("hover");
        },
        mouseleave: function() {
            this.$(".disabled").removeClass("hover");
        },
        removeAnchor: function() {
            if (this.isUnused()) {
                delete this.app.viewsById[this.model.id];
                this.$el.remove();
            } else {
                $("#unused_anchors").append(this.el);
            }
        },
        /* event helpers */
        submitEdit: function(e) {
            var key = $(e.target).attr("data-key"),
                val = $(e.target).val(),
                attributes = this.model.get("attributes");

            attributes[key] = val;
            this.model.set("attributes", attributes);

            this.message("alert-success", "attribute <strong>" + key + "</strong> successfully updated.");
            $(e.target).blur();
        },
        cancelEdit: function(e) {
            var key = $(e.target).attr("data-key"),
                val = this.model.get("attributes")[key];

            $(e.target).val(val);

            this.message("", "attribute <strong>" + key + "</strong> was not updated.");
            $(e.target).blur();
        },
        message: function(alert_type, message) {
            this.alert.displayMessage(alert_type, message);
        },
        isUnused: function() {
            return this.$el.parent().attr("id") === "unused_anchors";
        },
        validLength: function(str) {
            return (str.length > 0 && str.length < 256);
        }
    });
});