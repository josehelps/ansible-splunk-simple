define([
    "jquery",
    "underscore",
    "backbone"
], function(
    $,
    _,
    Backbone
) {
    return Backbone.View.extend({
        initialize: function(options) {
            this.options = options || {};
            this.model = this.options.model;

            this.render = _.debounce(this._render, 100);
            this.model.on("change entity:notFound", _.bind(this.render, this));
        },
        _render: function() {
            if (!this.$("input").is(":focus")) {
                this.$("input").val(this.model.value);   
            }
        },
        events: {
            "keydown input": "keydown",
            "click .search": "search"
        },
        keydown: function(e) {
            var chara = e.which,
                ENTER_CHAR = 13,
                ESC_CHAR = 27;

            if (chara === ENTER_CHAR) {
                this.search();
            } else if (chara === ESC_CHAR) {
                this.$("input").blur();
            }
        },
        search: function() {
            var val = this.$("input").val();
            if (val) {
                this.$("input").blur();
                this.model.setNewEntity(val);
            }
        }
    });
});
