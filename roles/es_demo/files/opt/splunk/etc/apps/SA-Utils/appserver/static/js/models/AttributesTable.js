define(["jquery", "underscore", "backbone"], function($, _, Backbone) {
	return Backbone.Model.extend({
		
		initialize: function(attributes, options) {
			this.collection = options.swimlanes;
			this.collection.on("reset", _.bind(this.fetchAll, this));
			this.fieldName = this.collection.prefs.field_name;
		},
		
		url: function() {
			return Splunk.util.make_url(
					"/custom/SA-Utils/identitymapper" +
					"/reverse_lookup?"+ this.query);
		},
		
		fetchAll: function() {
			
			if (this.collection.length > 0) {
				var value = this.collection.at(0).pref.get('entity_name'),
					constraint_method = this.collection.at(0).get("constraint_method");
				this.constraint_method = constraint_method;
				this.query = "value=" + value + "&constraint_method=" + constraint_method;
				this.value = value;
			}

			this.collection.each(function(model) {
				var constraint_fields = model.get("constraint_fields");
				if ((typeof value !== "undefined") && constraint_fields && constraint_method) {
					this.query += "&constraint_fields=" + constraint_fields;
				} else if (typeof value === "undefined") {
					this.trigger("entity:undefined");
					model.trigger("entity:undefined");
				}
			}, this);
			
			var that = this;
			
			this.fetch({
				success: function(m, resp) {
					if (resp.count === 0) {
						that.trigger("entity:notFound");
					}
					if (that.collection.length === resp.clauses.length) {
						// Iterate over models and responses in tandem.
						_.map(_.zip(that.collection.models, resp.clauses), function(f) {
							f[0].set('constraints', f[1]);
						});
					} else {
						// Unknown error.
						that.trigger("entity:invalid");
					}
				},
				error: function(m, resp) {
					that.trigger("entity:invalid");
				}
			});
			
		}, 
		
		parse: function(result) {
			this.clear();
			// Utilize only the first result.
			_.each(result.records[0], function(val, key) {
				var existing = this.get(key);
				if (existing) {
					this.set(key, _.union(existing, val));
				} else {
					this.set(key, val);
				}
			}, this);
		},
		
		setNewEntity: function(entity) {
			var pref = this.collection.getPref();
			pref.set("identity", entity);
			pref.set("entity_name", entity);
			this.collection.prefs.urlSync.setEntityName(entity);
			pref.save();
			
			this.trigger("setEntityName");
			this.fetchAll();
		}
	});
});

