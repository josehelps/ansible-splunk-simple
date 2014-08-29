define(
		[
		 'module',
		 'underscore',
		 'views/Base',
		 'app-components/incident_review/eventsviewer/table/body/row/PrimaryRow',
		 'app-components/incident_review/eventsviewer/table/body/row/SecondaryRow',
		 'util/console'
		 ],
		 function(module, _, BaseView, PrimaryRow, SecondaryRow, console){
			return BaseView.extend({
				moduleId: module.id,
				tagName: 'tbody',
				/**
				 * @param {Object} options {
				 *     model: {
				 *         result: <models.services.search.job.ResultsV2>,
				 *         summary: <model.services.search.job.SummaryV2>
				 *         state: <models.BaseV2>,
				 *         searchJob: <models.Job>,
				 *         report: <models.services.SavedSearch>,
				 *         application: <models.Application>
				 *     },
				 *     collection: {
				 *         selectedRows: <collections.SelectedRows>,
				 *         eventRenderers: <collections.services.configs.EventRenderers>,
				 *         workflowActions: <collections.services.data.ui.WorkflowActions>
				 *     },
				 *     selectableFields: true|false,
				 *     fieldNameMapping : Display field name map with actual field name
				 *     primaryRowFields : Primary row fields,
				 *     backboneEventMediator: backboneEventMediator to communicate between two views,
				 *     filedNameReplacementForActions : Action fields name mapping with display field
				 */
				//TODO: Define and passed actual value of options
				initialize: function(){
					BaseView.prototype.initialize.apply(this, arguments);
					this.fieldNameMapping = this.options.fieldNameMapping;
					this.primaryRowFields = this.options.primaryRowFields;
				},
				startListening: function() {
					this.listenTo(this.model.result.results, 'reset', function() {
						if (!this.model.state.get('isModalized')) {
							this.debouncedCleanupAndRender();
						}
					});
				},
				activate: function(options) {
					var clonedOptions = _.extend({}, (options || {}));
					delete clonedOptions.deep;

					if (this.active) {
						return BaseView.prototype.activate.call(this, clonedOptions);
					}

					BaseView.prototype.activate.call(this, clonedOptions);

					this.synchronousCleanupAndDebouncedRender();

					return this;
				},
				synchronousCleanupAndDebouncedRender: function() {
					if (this.active) {
						this.cleanup();
						this.debouncedRender();
					}
				},
				debouncedCleanupAndRender: _.debounce(function() {
					if (this.active) {
						this.cleanup();
						this.render();
					}
				}, 0),
				cleanup: function() {
					this.trigger('rows:pre-remove');
					this.eachChild(function(child){
						child.deactivate({deep: true});
						child.debouncedRemove({detach: true});
					}, this);
					this.children = {};
				},
				render: function() {
					if (_.isEmpty(this.children)) {
						var fragment = document.createDocumentFragment(),
						isRT = this.model.searchJob.entry.content.get('isRealTimeSearch'),
						results = isRT ? this.model.result.results.reverse({mutate: false}) : this.model.result.results.models;

						console.debug('Events Lister: rendering', results.length, 'events', isRT ? 'in real-time mode' : 'in historical mode');
						_.each(results, function(event, idx) {
							var lineNum,
							id = 'row_' + idx;
							if (isRT) {
								lineNum = this.model.result.endOffset() - idx;
							} else {
								lineNum = this.model.result.get('init_offset') + idx + 1;
							}

							this.children['masterRow_' + idx] = new PrimaryRow({ 
								model: { 
									event : event, 
									report: this.model.report,
									application: this.model.application,
									searchJob: this.model.searchJob,
									result: this.model.result,
									state: this.model.state
								}, 
								collection: {
									eventRenderers: this.collection.eventRenderers,
									selectedRows: this.collection.selectedRows,
									workflowActions: this.collection.workflowActions
								},
								lineNum: lineNum,
								idx: idx,
								allowRowExpand: this.options.allowRowExpand,
								primaryRowFields : this.primaryRowFields,
								backboneEventMediator: this.options.backboneEventMediator,
								filedNameReplacementForActions: this.options.filedNameReplacementForActions
							});
							this.children['masterRow_'+idx].render().appendTo(fragment);
							this.children['masterRow_' + idx].activate({deep: true});

							this.children['fieldRow_' + idx] = new SecondaryRow({
								model: { 
									event : event,
									report: this.model.report,
									result: this.model.result,
									summary: this.model.summary,
									state: this.model.state,
									application: this.model.application,
									searchJob: this.model.searchJob
								}, 
								collection: {
									workflowActions: this.collection.workflowActions,
									selectedRows: this.collection.selectedRows
								},
								idx: idx,
								selectableFields: this.options.selectableFields,
								fieldNameMapping : this.fieldNameMapping,
								colSpan : this.primaryRowFields.length
							});
							this.children['fieldRow_'+idx].render().appendTo(fragment);
							this.children['fieldRow_' + idx].activate({deep: true});
						},this);
						this.el.appendChild(fragment);

						//bulk purge of remove mutex
						_(this.model.state.toJSON()).each(function(value, key) {
							if(key.indexOf('pendingRemove') === 0) {
								this.model.state.unset(key);
							}
						},this);

						this.trigger('rows:added');
					}
					/**
					 * !!! Hack
					 * Check if all rows are select and set select all button
					 * It would have done with better way if we could have design model in better way
					 */
					if($('td.col-visibility .ir-label-checkbox').length !==0 && $('td.col-visibility .ir-selected').length === $('td.col-visibility .ir-label-checkbox').length) {
						this.options.backboneEventMediator.trigger("ir-add-select-all-checkbox");
					} else {
						this.options.backboneEventMediator.trigger("ir-remove-select-all-checkbox");
					}
					return this;
				}
			});
});
