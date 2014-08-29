define([
	"jquery",
	"underscore",
	"backbone",
	"bootstrap.alert",
	"text!app/templates/Alert.Template.html"
], function(
	$,
	_,
	Backbone,
	alert,
    AlertTemplate
) {
	return Backbone.View.extend({
		initialize: function(options) {
			this.options = options || {};
			this.options.message = this.options.message || "";
			this.options.alert_type = this.options.alert_type || "";
		},
		render: function() {
			this.$el.html(_.template(AlertTemplate, this.options));
			this.hide();

			return this;
		},
		displayMessage: function(alert_type, message, disappear) {
			this.options.message = message;
			this.options.alert_type = alert_type;
			this.render();

			if (disappear) {
				this.showDisappear();
			} else {
				this.show();
			}
		},
		events: {
			"click .close": "hide"
		},
		hide: function() {
			this.$el.hide();
		},
		show: function() {
			this.$el.show();
		},
		showDisappear: function() {
			this.$el.show().fadeIn().delay(1000).fadeOut();
		}
	});
});