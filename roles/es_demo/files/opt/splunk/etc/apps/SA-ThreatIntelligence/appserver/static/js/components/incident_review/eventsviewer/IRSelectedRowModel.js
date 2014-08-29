define(
		[
		 'backbone'
		 ],
		 function(Backbone) {
			/**
			 *  This model is used to store select row data.
			 *  Attribute for this
			 *     id : rule_id or event_id which is unique id
			 *     status: status value for a selected event
			 */
			return Backbone.Model.extend({
				defaults: {
					"id" : "",
					"status" : ""
				}
			});
		}
);