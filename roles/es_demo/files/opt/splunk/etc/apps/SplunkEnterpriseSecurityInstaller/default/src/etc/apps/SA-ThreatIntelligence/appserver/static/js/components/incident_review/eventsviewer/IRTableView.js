define(
		[
		 'jquery',
		 'underscore',
		 'module',
		 'models/Base',
		 'models/services/search/jobs/Result',
		 'models/services/search/IntentionsParser',
		 'views/Base',
		 'app-components/incident_review/eventsviewer/table/Master'
		 ],
		 function($, _, module, BaseModel, ResultModel, IntentionsParser, BaseView, EventsTableView){
			var ROW_EXPAND_REX = /r\d+/; 
			return BaseView.extend({
				moduleId: module.id,
				/**
				 * @param {Object} options {
				 *     model: {
				 *         result: <models.services.search.jobs.ResultsV2>,
				 *         summary: <model.services.search.jobs.SummaryV2>,
				 *         searchJob: <models.Job>,
				 *         report: <models.services.SavedSearch>,
				 *         application: <models.Application>,
				 *         state: <models.BaseV2> (optional)
				 *     },
				 *     collection: {
				 *         selectedRows: <collections.SelectedRows>
				 *         eventRenderers: <collections.services.configs.EventRenderers>,
				 *         workflowActions: <collections.services.data.ui.WorkflowActions>,
				 *     },
				 *     selectableFields: true|false,
				 *     sortableFields: true|false (default true),
				 *     headerMode: dock|static|none (default),
				 *     headerOffset: integer (only applicable with headerMode=dock),
				 *     allowRowExpand: true|false,
				 *     tableHeaderLabels : list of table labels
				 *     tableHeaderFiledNames : list of table header fields,
				 *     fieldNameMapping : display field and actual fields mapping,
				 *     backboneEventMediator : backboneEventMediator to communicate event between different views,
				 *     filedNameReplacementForActions : Action field mapping with display field
				 * }
				 */
				initialize: function(){
					BaseView.prototype.initialize.apply(this, arguments);

					this.options = $.extend(true, {
						selectableFields: true,
						sortableFields: true,
						headerMode: 'dock',
						headerOffset: 0,
						allowRowExpand: true,
						scrollToTopOnPagination: false,
						defaultDrilldown: true
					}, this.options);

					this.rendered = {
							listraw: false
					};


					//CLONE RESULTS 
					this.model._result      = new ResultModel();
					this.model.state        =  this.model.state || new BaseModel();
					this.model.listrawState =  new BaseModel();
					this.model.intentions   =  new IntentionsParser();


					/*
					 * Due to mediation of info to/from the row level views regarding 
					 * row expansion we need to store a rex that matches the structure
					 * of the rows expand key. 
					 */
					this.model.state.ROW_EXPAND_REX        = ROW_EXPAND_REX;
					this.model.listrawState.ROW_EXPAND_REX = ROW_EXPAND_REX;

					this.children.listraw = new EventsTableView({
						model: { 
							result: this.model._result,
							summary: this.model.summary,
							searchJob: this.model.searchJob,
							report: this.model.report,
							application: this.model.application,
							state: this.model.listrawState
						},
						collection: {
							selectedRows: this.collection.selectedRows,
							eventRenderers: this.collection.eventRenderers,
							workflowActions: this.collection.workflowActions
						},
						selectableFields: this.options.selectableFields,
						headerMode: this.options.headerMode,
						headerOffset: this.options.headerOffset,
						allowRowExpand: this.options.allowRowExpand,
						tableHeaderLabels :  this.options.tableHeaderLabels,
						tableHeaderFieldNames : this.options.tableHeaderFieldNames,
						fieldNameMapping : this.options.fieldNameMapping,
						backboneEventMediator : this.options.backboneEventMediator,
						filedNameReplacementForActions : this.options.filedNameReplacementForActions
					});

					/*
					 * This is called in initialize purely for backwards compatibility. Eventually,
					 * this views activate should be slave to its parent invoking it. 
					 */
					 this.activate({stopRender: true});
				},
				startListening: function() {
					this.listenTo(this.model.result.results, 'reset', function() {
						if (this.model.state.get('isModalized')) {
							this.model.state.set('pendingRender', true);
						} else {
							var responseText = this.model.result.responseText ? JSON.parse(this.model.result.responseText) : {};
							this.model._result.setFromSplunkD(responseText, {skipStoringResponseText: true});
						}
					});

					/*
					 * Proxy modalize state information up to the top-level state model
					 * to inform eventspane controls of the state change.
					 */
					//Drilldown related handlers.
					this.listenTo(this.model.intentions, 'change', function() {
						this.model.report.entry.content.set('search', this.model.intentions.fullSearch());
					});

					this.listenTo(this.model.listrawState, 'drilldown', this.drilldownHandler);

					this.listenTo(this.model.report.entry.content, 'change:display.prefs.events.offset', function() {
						if (this.options.scrollToTopOnPagination) {
							var containerTop = this.$el.offset().top,
							currentScrollPos = $(document).scrollTop(),
							headerHeight = this.$el.children(':visible').find('thead:visible').height(),
							eventControlsHeight = $('.events-controls-inner').height();
							if (currentScrollPos > containerTop) {
								$(document).scrollTop(containerTop - (headerHeight + eventControlsHeight));
							}
						}
					});
				},
				activate: function(options) {
					var clonedOptions = _.extend({}, (options || {}));
					delete clonedOptions.deep;

					if (this.active) {
						return BaseView.prototype.activate.call(this, clonedOptions);
					}

					this.model._result.setFromSplunkD(this.model.result.responseText ? JSON.parse(this.model.result.responseText) : {});

					BaseView.prototype.activate.call(this, clonedOptions);

					this.manageStateOfChildren(clonedOptions);

					return this; 
				},
				deactivate: function(options) {
					if (!this.active) {
						return BaseView.prototype.deactivate.apply(this, arguments);
					}

					BaseView.prototype.deactivate.apply(this, arguments);

					//clear any stale attrs
					this.model._result.clear();
					this.model.intentions.clear();
					this.model.listrawState.clear();
					return this;
				},
				drilldownHandler: function(drilldownInfo) {
					var drilldown = this.getDrilldownCallback(drilldownInfo.data, drilldownInfo.noFetch);

					if(this.options.defaultDrilldown) {
						drilldown();
					}

					this.trigger('drilldown', drilldownInfo, drilldown);
				},
				getDrilldownCallback: function(data, noFetch) {
					var that = this;
					return function() {
						if(noFetch) {
							that.model.report.entry.content.set(data);
							return $.Deferred().resolve();   
						} else {
							return that.model.intentions.fetch({ data: data });
						}
					};
				},

				handlePendingRender: function() {
					if (this.model.state.get('pendingRender')) {
						var responseText = this.model.result.responseText ? JSON.parse(this.model.result.responseText) : {};
						this.model._result.setFromSplunkD(responseText, {clone: true});
						this.model.state.set('pendingRender', false);
					}
				},
				getType: function() {
					return 'listraw';
				},
				manageStateOfChildren: function(options) {
					options || (options = {});
					var type = this.getType();
					if(!options.stopRender) {
						this._render(type);
					}
					this.children.listraw.activate({deep: true}).$el.show();
				},

				updateContainerHeight: function(height) {
					// use this during 'static' header mode to update vertical scroll bars.
					// If no height argument set, this maxes out wrapper height to available window size
					this.children[this.getType()].updateContainerHeight(height);
				},
				_render: function(type) {
					if(!this.rendered[type]) {
						this.children[type].render().appendTo(this.$el);
						this.rendered[type] = true;
					}
				},
				render: function() {
					this._render(this.getType());
					return this;
				}
			});
		}
);
