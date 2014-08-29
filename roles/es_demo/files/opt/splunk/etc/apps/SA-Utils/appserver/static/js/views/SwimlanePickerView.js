define([
    'jquery',
    'underscore',
    'backbone',
    'contrib/text!app/templates/SwimlanePicker.html',
    'app/views/SwimlaneColorPickerView'
], function(
    $,
    _,
    Backbone,
    SwimlanePickerTemplate,
    SwimlaneColorPickerView
) {
    return Backbone.View.extend({
        className: 'swimlanePicker',
        initialize: function(options) {
            this.options = options || {};
            this.model = this.options.model;
            this.colorPicker = new SwimlaneColorPickerView({model: this.model});

            this.model.on('change:selected', _.bind(this.onSelected, this));
            this.model.on('change:disabled', _.bind(this.onDisabled, this));
            this.model.on('change:color', _.bind(this.changeColor, this));
        },
        change: function(e) {
            this.model.set('selected', $(e.target).is(":checked"));
        },
        changeColor: function(model, color) {
            var prevColor = model.previous("color");
            this.$(".swimlaneChosenColor").removeClass(prevColor);
            this.$(".swimlaneChosenColor").addClass(color);
            this.model.set('color', color);
        },
        events: {
            'change input': 'change',
            'click .swimlaneChosenColor': 'toggleColorPicker'
        },
        onDisabled: function() {
            this.$('input').prop('disabled', this.model.get('disabled'));
        },
        onSelected: function(model) {
            this.$('input').prop('checked', this.model.get('selected'));
        },
        render: function() {
            this.$el.html(_.template(SwimlanePickerTemplate,{ 
              'selected': this.model.get('selected'),
              'title': this.model.id,
              'color': this.model.get('color')
            }));
            if(this.model.get('selected')){
                this.$el.find('.laneCheck')
                    .prop('checked', true);
            }
            this.$el.append(this.colorPicker.render().el);
            return this;
        },
        toggleColorPicker: function() {
            if (this.colorPicker.isClosed()) {
                this.colorPicker.open();
            } else {
                this.colorPicker.close();
            }
        }
    });
});
