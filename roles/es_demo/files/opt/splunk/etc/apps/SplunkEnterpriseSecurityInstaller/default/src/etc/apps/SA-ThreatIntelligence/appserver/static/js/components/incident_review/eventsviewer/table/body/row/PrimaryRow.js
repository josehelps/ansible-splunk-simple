define(
		[
		 'jquery',
		 'underscore',
		 'backbone',
		 'module',
		 'views/Base',
		 'splunk.util',
		 'app-components/incident_review/eventsviewer/IREventViewerUtils',
		 'views/shared/eventsviewer/shared/WorkflowActions'
		 ],
		 function(
				 $,
				 _,
				 Backbone,
				 module,
				 BaseView,
				 splunkUtil,
				 IRUtils,
				 WorkflowActionsView ){
			
			return BaseView.extend({
				moduleId: module.id,
				tagName: 'tr',
				/**
				 * @param {Object} options {
				 *      model: {
				 *         event: <models.services.search.job.ResultsV2.results[i]>,
				 *         result: <models.services.search.job.ResultsV2>,
				 *         state: <models.Base>,
				 *         summary: <models.services.searchjob.SummaryV2>,
				 *         report: <models.services.SavedSearch>,
				 *         searchJob: <models.Job>,
				 *         application: <models.Application>
				 *     },
				 *     collection: {
				 *         selectedRows: <collections.SelectedRows>,
				 *         eventRenderers: <collections.services.configs.EventRenderers>,
				 *         workflowActions: <collections.services.data.ui.WorkflowActions>
				 *     },
				 *     selectableFields: true|false,
				 *     primaryRowFields : Primary row fields (this be equal to number of columed defined in the table),
				 *     backboneEventMediator: backboneEventMediator to communicate between two views,
				 *     filedNameReplacementForActions : Action field mapping with display field
				 */
				initialize: function(){
					BaseView.prototype.initialize.apply(this, arguments);

					this.interaction  = 'i' + this.options.idx;
					this.rowExpanded  = 'r' + this.options.idx;
					this.showAllLines = 's' + this.options.idx;
					this.primaryRowFields = this.options.primaryRowFields;

					this.model.state.unset(this.showAllLines);

					this.model.renderer = this.collection.eventRenderers.getRenderer(this.model.event.get('eventtype'));
				},
				startListening: function() {
					this.listenTo(this.model.state, this.interaction, function() {
						if(!this.isExpanded()) {
							this.expand();
						}
					});

					/*
					 * Our bus for communication from our grandparent regarding clicks on the
					 * modalization mask.
					 */
					this.listenTo(this.model.state, 'change:' + this.rowExpanded, function(model, value, options){
						if(!value) {
							this.collapseState();
						}
					});


					this.listenTo(this.model.report.entry.content, 'change:display.prefs.events.offset', this.collapseState);
					//on change of the search string we should unmodalize
					this.listenTo(this.model.state, 'intentions-fetch', this.collapseState);
					
					this.options.backboneEventMediator.on("ir-remove-all-selected-row", function() {
						this.toggleCheckBox(false, true);
					}, this);
					
					this.options.backboneEventMediator.on("ir-select-all-row", function() {
						this.toggleCheckBox(true, false);
					},this);

					this.listenTo(this.model.result.results, 'reset',  this.collapseState);
				},

				events: {
					'click td.expands': function(e) {
						this.expand();
						e.preventDefault();
					},
					'click td.col-visibility label.checkbox a.btn.show': function(e) {
						this.toggleCheckBox(true, true);
					},
					'click ._time': function(e) {
						e.preventDefault();
						this.drilldown($(e.currentTarget), e);
					},
					'keyup ._time': function(e) {
						e.preventDefault();
						if(e.which === 13) {
							this.drilldown($(e.currentTarget), e);
						}
					},
					'click .ir-event-actions' : function(e) {
						e.preventDefault();
					},
					'mousedown .ir-event-actions' : function(e) {
						this.openEventActions(e, this.options.idx);
					},
					'keydown .ir-event-actions' : function(e) {
						if (e.keyCode === 13) {
							this.openEventActions(e, this.options.idx);
						}
					},
					'click .ir-row-field-actions' : function(e) {
						e.preventDefault();
					},
					'mousedown .ir-row-field-actions' : 'openRowFieldActions',
					'keydown .ir-row-field-actions' : function(e) {
						if (e.keyCode === 13) {
							this.openRowFieldActions(e);
						}
					}
				},
				openRowFieldActions : function(e) {
					var $target = $(e.currentTarget), fieldName = $target.attr('data-field-name'), fieldValue = $target.attr('data-field-value');

					if (this.children.fieldActions && this.children.fieldActions.shown) {
						this.children.fieldActions.hide();
						if (this.lastMenu === (fieldName + '-row-field-actions')) { return true ;}
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

					this.lastMenu = fieldName + "-row-field-actions";

					this.children.fieldActions.render().appendTo($('body')).show($target);
					e.preventDefault();
					return false;
				},
				openEventActions: function(e, idx) {
					var $target = $(e.currentTarget);
					if (this.children.rowActions && this.children.rowActions.shown) {
						this.children.rowActions.hide();
						if (this.lastMenu === (idx + '-event-actions')) { return true ;}
					}
					this.children.rowActions = new WorkflowActionsView(
							{
								model : this.model,
								collection : this.collection.workflowActions,
								mode : 'menu'
							});
					this.lastMenu = idx + '-event-actions';
					this.children.rowActions.render().appendTo( $('body') ).show($target);
					e.preventDefault();
					return false;
				},
				drilldown: function($target, e) {
					var data = $target.data(), timeIso, epoch;
					if (data.timeIso) {
						timeIso = data.timeIso;
						epoch = splunkUtil.getEpochTimeFromISO(timeIso);
						this.model.state.trigger('drilldown', {
							noFetch: true, 
							data: {
								'dispatch.earliest_time': epoch,
								'dispatch.latest_time': '' + (parseFloat(epoch) + 1)
							},
							event: e,
							_time: timeIso,
							idx: this.options.idx
						});
					}
				},
				expand: function(options) {
					if (this.options.allowRowExpand) {
						(this.isExpanded()) ? this.collapseState(): this.expandState();
					}
				},
				expandState: function() {
					if( this.model.searchJob.isRunning() && this.model.searchJob.isRealtime() ){
						alert("The search is still running; please finalize it first in order to view the details");
						return;
					} else if( this.model.searchJob.isRunning() ){
						alert("The search is still running; please finalize it or wait for it to complete in order to view the details");
						return;
					}
					this.model.state.set(this.rowExpanded, true);
					this.toggleArrow(true);
					// change background color and border of row
					this.$el.addClass("ir-splunk-offwhite-color");
					this.$el.addClass("ir-hide-bottom-border");
				},
				collapseState: function() {
					this.model.state.set(this.rowExpanded, false);
					this.toggleArrow(false);
					// change background color and border of row
					this.$el.removeClass("ir-splunk-offwhite-color");
					this.$el.removeClass("ir-hide-bottom-border");
				},
				isExpanded: function() {
					return this.model.state.get(this.rowExpanded);
				},
				toggleArrow: function(open) {
					var $arrow =  this.$('td.expands > a > i').removeClass('icon-triangle-right-small icon-triangle-down-small');
					$arrow.addClass((open) ? 'icon-triangle-down-small':  'icon-triangle-right-small');
				},
				/*
				 * @param addCheck : set it true if you want to remove the checkbox
				 * @param removeCheck: set it true if you want to add the checkbox
				 */
				toggleCheckBox : function(addCheck, removeCheck) {
					var checkIconElement = '<i class="icon-check ir-selected"></i>';
					var $checkIcon = this.$('td.col-visibility > label > a > i');
					var $label = this.$('td.col-visibility > label > a');
					var ruleid  = $.trim($label.attr("data-ruleid"));
					var status  = $.trim($label.attr("data-status"));
					if($checkIcon.length >= 1) {
						// remove
						if(removeCheck) {
							$label.empty();
							this.collection.selectedRows.remove(this.collection.selectedRows.find(function(model) {
								return  model.has('id') && model.get('id')===ruleid;
							}, this));
							this.options.backboneEventMediator.trigger("ir-remove-select-all-checkbox");
						}
					} else {
						// add
						if(addCheck) {
							this.collection.selectedRows.push({'id': ruleid, "status" : status});
							$label.append(checkIconElement);
						}
						if($('td.col-visibility .ir-selected').length === $('td.col-visibility .ir-label-checkbox').length) {
							this.options.backboneEventMediator.trigger("ir-add-select-all-checkbox");
						}
					}
					
				},
				render: function() {
					var iconVisible = _.find(this.collection.selectedRows.models, function(model) {
						return model.has('id') && model.get('id') === splunkUtil.fieldListToString(this.model.event.get("rule_id"));
					}, this);
					this.$el.html(this.compiledTemplate({
						$: $,
						event: this.model.event,
						application: this.model.application,
						expanded: this.isExpanded(),
						formattedTime: this.model.event.formattedTime(),
						_:_,
						primaryRowFields: this.options.primaryRowFields || [],
						getFieldValue : IRUtils.getFieldValue,
						convertFirstCharToUpperCase: IRUtils.convertFirstCharToUpperCase,
						splunkUtil : splunkUtil,
						iconVisible : iconVisible,
						filedNameReplacementForActions : this.options.filedNameReplacementForActions
					}));
					return this;
				},
				template: '\
					<td class="expands ir-veritcal-align">\
						<a><i class="icon-triangle-<%- expanded ? "down" : "right" %>-small"></i></a>\
					</td>\
					<td class="col-visibility ir-check-limited-width ir-veritcal-align"> \
						<label class="checkbox ir-label-checkbox">\
							<a data-ruleid=<%=splunkUtil.fieldListToString(event.get("rule_id"))%>  data-status=<%=splunkUtil.fieldListToString(event.get("status"))%> class="btn show">\
								<% if (iconVisible) { %>\
									<i class="icon-check ir-selected"></i> \
								<%}%> \
							</a>\
						</label>\
					</td>\
					<% _(primaryRowFields).each(function(field, i) { %>\
						<% if (field === "_time") { %>\
							<td class="_time ir-veritcal-align">\
						<% } else { %>\
							<td class="ir-veritcal-align">\
						<%}%>\
							<% var fieldlist = event.get(field) %> \
							<% if(fieldlist.length > 0) { %>\
								<%  _(fieldlist).each(function(mv_field, j) { %>\
									<% if (field === "_time") { %>\
										<%- formattedTime %>\
									<% } else if(field === "security_domain") { %>\
											<%=convertFirstCharToUpperCase(getFieldValue(event, mv_field))%>\
									<% } else { %>\
										<%if(field === "urgency") { %>\
												<% var value = getFieldValue(event, mv_field)%>\
												<% if(value==="info" || value==="informational") { %>\
													<div class="icon-info-circle ir-icon-info-circle-style ir-row-hover-field ir-row-float-left">\
												<%} else if(value==="low") { %>\
													<div class="icon-circle-filled ir-icon-circle-style ir-row-hover-field ir-row-float-left">\
												<%} else if(value==="medium") {%>\
													<div class="icon-warning ir-icon-alert-circle-med-style ir-row-hover-field ir-row-float-left">\
												<%} else if(value==="high") {%>\
													<div class="icon-warning ir-icon-alert-circle-high-style ir-row-hover-field ir-row-float-left">\
												<%} else if(value==="critical") {%>\
													<div class="icon-alert ir-icon-alert-style ir-row-hover-field ir-row-float-left">\
												<%}%>\
												<% var urgencyTooltip = getFieldValue(event, event.get("priority")) + " priority and " + getFieldValue(event,  event.get("severity")) + " severity"%>\
												<span title="<%-urgencyTooltip%>" class="ir-urgency-default-text-style"><%=convertFirstCharToUpperCase(value)%></span>\
												</div>\
										<%} else { %>\
											<div class="ir-row-hover-field ir-row-float-left"><%= getFieldValue(event, mv_field) %> </div>\
										<%}%>\
											<% var field_name = filedNameReplacementForActions.hasOwnProperty(field) ? filedNameReplacementForActions[field] : field %>\
											<% var field_value = filedNameReplacementForActions.hasOwnProperty(field) ? getFieldValue(event, event.get(filedNameReplacementForActions[field])) : getFieldValue(event, mv_field) %>\
											<div class="ir-row-show-on-hover ir-row-float-inherit">\
												<a class="ir-row-popdown-toggle ir-row-field-actions" data-field-name="<%- field_name %>" data-field-value="<%- field_value %>">\
													<span class="caret"></span>\
												</a>\
											</div>\
									<%}%>\
								<% }); %> \
							<% } %> \
						</td>\
					<% });%>\
					<td class="actions popdown ir-veritcal-align">\
						<a class="ir-popdown-toggle ir-event-actions ir-btn-pill">\
							<span class="caret"></span>\
						</a>\
					</td>'
			});
		}
);
