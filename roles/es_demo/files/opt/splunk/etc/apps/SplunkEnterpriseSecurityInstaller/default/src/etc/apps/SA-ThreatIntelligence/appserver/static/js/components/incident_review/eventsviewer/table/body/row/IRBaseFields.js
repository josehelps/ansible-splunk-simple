define(
		[ 'jquery', 'underscore', 'backbone', 'module',
				'keyboard/SearchModifier', 'views/Base',
				'views/shared/eventsviewer/shared/WorkflowActions' ],
		function($, _, Backbone, module, KeyboardSearchModifier, BaseView,
				WorkflowActionsView) {
			return BaseView.extend({
					
						/**
						 * @param {Object} options {
						 *      model: {
						 *         event: <models.services.search.job.ResultsV2.result[i]>,
						 *         summary: <model.services.search.job.SummaryV2>,
						 *         application: <model.Application>,
						 *         report: <models.services.SavedSearch>,
						 *         searchJob: <models.Job>
						 *     }
						 *     collection: {
						 *         selectedRows: <collections.SelectedRows>
						 *         workflowActions: <collections.services.data.ui.WorkflowActions>
						 *     },
						 *     selectableFields: true|false
						 * }
						 */
						initialize : function() {
							BaseView.prototype.initialize.apply(this, arguments);
							this.rowExpanded = 'r' + this.options.idx;
							this.keyboardSearchModifier = new KeyboardSearchModifier();
						},
						startListening : function() {
							this.listenTo(this.model.event, 'change',
									this.render);
						},
						events : {
							'click .ir-field-actions' : function(e) {
								e.preventDefault();
							},
							'mousedown .ir-field-actions' : 'openFieldActions',
							'keydown .ir-field-actions' : function(e) {
								if (e.keyCode === 13) {
									this.openFieldActions(e);
								}
							}
						},
						openFieldActions : function(e) {
							var $target = $(e.currentTarget), fieldName = $target.attr('data-field-name'), fieldValue = $target.attr('data-field-value');

							if (this.children.fieldActions && this.children.fieldActions.shown) {
								this.children.fieldActions.hide();
								if (this.lastMenu === (fieldName + '-field-actions')) { return true ;}
							}

							this.children.fieldActions = new WorkflowActionsView(
									{
										model : this.model,
										collection : this.collection.workflowActions,
										field : {
											'name' : fieldName,
											'value' : fieldValue
										},
										mode : 'menu',
										fieldName : fieldName,
										fieldValue : fieldValue
									});

							this.lastMenu = fieldName + "-field-actions";

							this.children.fieldActions.render().appendTo(
									$('body')).show($target);
							e.preventDefault();
							return false;
						}
					});
		});
