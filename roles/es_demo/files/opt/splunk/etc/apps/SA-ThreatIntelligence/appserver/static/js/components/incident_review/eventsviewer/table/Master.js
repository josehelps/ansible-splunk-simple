define(
		[
		 'underscore',
		 'module',
		 'views/Base',
		 'app-components/incident_review/eventsviewer/table/head/TableHead',
		 'app-components/incident_review/eventsviewer/table/body/Master',
		 'splunk.util'
		 ],
		 function(_, module, BaseView, TableHeadView, TableBodyView, util){
			return BaseView.extend({
				moduleId: module.id,
				/**
				 * @param {Object} options {
				 *     model: {
				 *         result: <models.services.search.job.ResultsV2>,
				 *         summary: <model.services.search.job.SummaryV2>,
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
				 *     headerMode: dock|static|none (default),
				 *     headerOffset: integer (only applicable with headerMode=dock),
				 *     allowRowExpand: true|false
				 *     fieldNameMapping : name value mapping with actual field name with display field name
				 *     tableHeaderLabels : table header labels
				 *     tableHeaderFieldNames: table header fields names,
				 *     backboneEventMediator : backboneEventMediator to communicate event between different views,
				 *     filedNameReplacementForActions : Action field name mapping with display field
				 */
				className: 'scrolling-table-wrapper table',
				initialize: function(){
					BaseView.prototype.initialize.apply(this, arguments);

					this.tableId = this.cid + '-table';

					/*
					 * Based on the state of the report, customize thead columns 
					 * to contain contain time. 
					 *
					 */
					this.tableHeadlabels = this.options.tableHeaderLabels;
					this.children.head = new TableHeadView({
						model:{
							result : this.model.result
						},
						collection: {
							selectedRows: this.collection.selectedRows
						},
						labels:this.tableHeadlabels,
						backboneEventMediator: this.options.backboneEventMediator
					});

					this.children.body = new TableBodyView({
						model: { 
							result: this.model.result,
							summary: this.model.summary,
							state: this.model.state,
							searchJob: this.model.searchJob,
							report: this.model.report,
							application: this.model.application
						},
						collection: {
							selectedRows: this.collection.selectedRows,
							eventRenderers: this.collection.eventRenderers,
							workflowActions: this.collection.workflowActions
						},
						selectableFields: this.options.selectableFields,
						allowRowExpand: this.options.allowRowExpand,
						primaryRowFields : this.options.tableHeaderFieldNames,
						fieldNameMapping : this.options.fieldNameMapping,
						backboneEventMediator: this.options.backboneEventMediator,
						filedNameReplacementForActions: this.options.filedNameReplacementForActions
					});

				},

				activate: function(options) {
					if (this.active) {
						return BaseView.prototype.activate.apply(this, arguments);
					}

					this.children.head.updateLabels(this.tableHeadlabels);

					return BaseView.prototype.activate.apply(this, arguments);
				},
				startListening: function() {
					this.listenTo(this.children.body, 'rows:pre-remove', function() { this.$el.css('minHeight', this.$el.height()); });
					this.listenTo(this.children.body, 'rows:added', function() { this.$el.css('minHeight', ''); });
				},
				deactivate: function(options) {
					if (!this.active) {
						return BaseView.prototype.deactivate.apply(this, arguments);
					}


					BaseView.prototype.deactivate.apply(this, arguments);
					return this;
				},

				updateTableHead: function() {
					_.defer(function() {
						this.updateContainerHeight();
					}.bind(this));
				},
				updateContainerHeight: function(height) {
					// use this during 'static' header mode to update vertical scroll bars.
					// If no height argument set, this maxes out table wrapper height to available window size
					if (height) {
						this.$('> .vertical-scrolling-table-wrapper').css('height', height);
					} else {
						this.$('> .vertical-scrolling-table-wrapper').css('max-height', $(window).height() - this.$el.offset().top);
					}
				},
				render: function() {
					this.$el.html(this.compiledTemplate({
						tableId: this.tableId
					}));
					this.children.head.render().appendTo(this.$('#' + this.tableId));
					this.children.body.render().appendTo(this.$('#' + this.tableId));
					return this;
				},
				reflow: function() {
					this.updateTableHead();
					return this;
				},
				template: '\
				<table class="table table-chrome table-row-expanding events-results events-results-table" id="<%= tableId %>"></table>\
					'
			});
		}
);
