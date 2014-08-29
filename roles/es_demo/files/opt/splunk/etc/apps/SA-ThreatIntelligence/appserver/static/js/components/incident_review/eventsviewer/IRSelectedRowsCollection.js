define(
		[
		 'backbone',
		 'app-components/incident_review/eventsviewer/IRSelectedRowModel'
		 ],
		 function(Backbone, SelectedRowModel) {
			return Backbone.Collection.extend({
				 initialize: function(models, options) {
					Backbone.Collection.prototype.initialize.apply(this, arguments);
				 },
				model: SelectedRowModel
			});
		}
);
