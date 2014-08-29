define(
		[
		 'module',
		 'underscore',
		 'views/Base',
		 'app-components/incident_review/eventsviewer/table/body/row/IREventFields',
		 'splunk.util'
		 ],
		 function(module, _, BaseView, EventFields, util) {
			return BaseView.extend({
				moduleId: module.id,
				tagName: 'tr',
				className: 'field-row',
				/**
				 * @param {Object} options {
				 *      model: {
				 *         result: <models.services.search.job.ResultsV2>,
				 *         event: <models.services.search.job.ResultsV2.result[i]>,
				 *         summary: <model.services.search.job.SummaryV2>
				 *         state: <models.Base>,
				 *         application: <models.Application>
				 *     }
				 *     collection: {
				 *         selectedRows: <collections.SelectedRows>
				 *         workflowActions: <collections.services.data.ui.WorkflowActions> 
				 *     },
				 *     selectableFields: true|false,
				 *     fieldNameMapping : Display field name map with actual field name
				 *     colSpan : column size
				 * } 
				 */
				initialize: function(){
					BaseView.prototype.initialize.apply(this, arguments);
					// add gray background color
					this.$el.addClass("ir-splunk-offwhite-color");
					this.rowExpanded  = 'r' + this.options.idx;
					this.showAllLines = 's' + this.options.idx;
					
					this.children.eventFields = new EventFields({
						model: { 
							event: this.model.event,
							report: this.model.report,
							summary: this.model.summary,
							result: this.model.result,
							state: this.model.state,
							application: this.model.application,
							searchJob: this.model.searchJob
						},
						collection: {
							workflowActions: this.collection.workflowActions,
							selectedRows: this.collection.selectedRows
						},
						selectableFields: this.options.selectableFields,
						idx: this.options.idx,
						fieldNameMapping : this.options.fieldNameMapping
					});

				},
				startListening: function() {
					this.listenTo(this.model.state, 'change:' + this.rowExpanded, this.visibility);

				},
				visibility: function() {
					if (this.model.state.get(this.rowExpanded)) {
						this.$el.show();
						this.children.eventFields.activate().$el.show();
					} else {
						this.$el.hide();
						this.children.eventFields.deactivate().$el.hide();
					}
				},
				getCalculatedColSpan: function() {
					// info field + check box + action field
					return this.options.colSpan + 3;
				},
				collapseState: function() {
					this.model.state.unset(this.rowExpanded);
				},
				render: function() {
					this.$el.append(this.compiledTemplate({
						cspan: this.getCalculatedColSpan()
					}));
					this.children.eventFields.render().appendTo(this.$('.event'));
					this.visibility();
					return this;
				},
				template: '\
					<td class="event" colspan="<%- cspan %>" style=" padding-top:20px;"></td>\
					'
			});
		}
);
