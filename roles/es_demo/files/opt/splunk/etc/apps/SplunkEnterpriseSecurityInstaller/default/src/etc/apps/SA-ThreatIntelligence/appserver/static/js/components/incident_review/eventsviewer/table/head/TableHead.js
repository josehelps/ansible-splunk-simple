define(
		[
		 'underscore',
		 'jquery',
		 'module',
		 'views/Base',
		 'helpers/user_agent',
		 'splunk.util'
		 ],
		 function(
				 _,
				 $,
				 module,
				 BaseView,
				 user_agent,
				 splunkUtil
		 )
		 {
			return BaseView.extend({
				moduleId: module.id,
				tagName: 'thead',
				/**
				 * @param {Object} options {
				 *     model: {
				 *         result : <models.services.search.job.ResultsV2>
				 *     },
				 *     collection: {
				 *        selectedRows: this.collection.selectedRows
				 *     },
				 *     labels: <Array>,
				 *     backboneEventMediator: backboneEventMediator to communicate between two views
				 * }
				 */
				initialize: function() {
					BaseView.prototype.initialize.apply(this, arguments);
				},
				startListening: function() {
					this.options.backboneEventMediator.on("ir-remove-select-all-checkbox", function() {
						this.toggleSelectAll(false, true, false);
					}, this);
					this.options.backboneEventMediator.on("ir-add-select-all-checkbox", function() {
						this.toggleSelectAll(true, false, false);
					}, this);
				},
				events : {
					'click th.col-visibility label.checkbox a.btn.show': function(e) {
						this.toggleSelectAll(true, true, true);
						e.preventDefault();
					}
				},
				/**
				 * @param addCheck : set it true if you want to add check box
				 * @param removeCheck : set it true if you want to remove check box
				 * @param isTriggerEvent: set it true if trigger needs to be fired when any check or uncheck option is happened
				 */
				toggleSelectAll : function(addCheck, removeCheck, isTriggerEvent) {
					var checkIconElement = '<i class="icon-check ir-selected"></i>';
					var $checkIcon = this.$('th.col-visibility > label > a > i');
					var $label = this.$('th.col-visibility > label > a');
					if($checkIcon.length >= 1) {
						// remove
						if (removeCheck) {
							$label.empty();
							if(isTriggerEvent) {
								this.options.backboneEventMediator.trigger("ir-remove-all-selected-row");
							}
						}
					} else {
						// add
						if (addCheck) {
							$label.append(checkIconElement);
						}
						if(isTriggerEvent) {
							this.options.backboneEventMediator.trigger("ir-select-all-row");
						}
					}
				},
				updateLabels: function(labels) {
					this.options.labels = labels;
					this.render();
				},
				render: function() {
					this.$el.html(this.compiledTemplate({
						_: _,
						is_ie7: (user_agent.isIE7() || (user_agent.isIE() && user_agent.isInIE7DocumentMode())) ? 'ie7': '',
								is_ie8: user_agent.isIE8() ? 'ie8': '',
										labels: this.options.labels || [],
										isSelectAllChecked : false
					}));
					return this;
				},
				template: '\
					<tr>\
						<th class="col-info"><i class="icon-info"></i></th>\
						<th class="col-visibility" title="SelectAll">\
							<label class="checkbox ir-label-checkbox"> <a class="btn show"> \
								<% if(isSelectAllChecked) {%>\
									<i class="icon-check ir-selected"></i>\
								<%}%>\
							</a></label>\
						</th>\
						<% _.each(labels, function(label, index) { %>\
								<th class="col-<%- index %> <%- is_ie7 %>"><%- _(label).t() %></th>\
						<% }) %>\
						<th class="col-<%- labels.length %> <%- is_ie7 %> <%- is_ie8 %>"><%- _("Actions").t() %></th>\
					</tr>\
					'
			});
		 }
);
