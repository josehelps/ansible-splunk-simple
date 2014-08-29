define(
		[
		 'jquery',
		 'underscore',
		 'backbone',
		 'module',
		 'app-components/incident_review/eventsviewer/table/body/row/IRBaseFields',
		 'splunk.util',
		 'css!app-components/incident_review/eventsviewer/css/IREventViewer.css',
		 'app-components/incident_review/eventsviewer/IREventViewerUtils'
		 ],
		 function(
				 $,
				 _,
				 Backbone,
				 module,
				 FieldsView,
				 SplunkUtil,
				 EventViewerCSS,
				 EventViewerUtils ){
			/*
			 *  Templates for Description and Additional Fields
			 */
			var _descriptionAdditionDetailsTemplate =
				'<table class="ir-table-no-row-border">\
					<tbody> \
					<tr><td><%=data.compiledDescriptionTemplate({m:data.m, _:data._, getFieldValue:data.getFieldValue}, {variable:"data"})%></td></tr>\
					<tr><td><%=data.compiledAdditionFieldsTemplate({m:data.m, _:data._, r:data.r,  fields:data.fields, displayFields:data.displayFields, getFieldValue:data.getFieldValue }, {variable:"data"})%></td></tr>\
					</tbody> \
				</table>';
			var compiledDescriptionAdditionDetailsTemplate = _.template(
					_descriptionAdditionDetailsTemplate, null, {
						variable : "data"
					});

			var _descriptionTemplate = '\
			<%if(data.m.has("rule_description")) { %>\
				<table class="ir-table-no-row-border">\
					<tbody> \
						<tr>\
							<td class="ir-header">Description:</td>\
						</tr>\
						<tr> \
							<% var fieldlist = data.m.get("rule_description") %>\
							<% if(fieldlist && fieldlist.length > 0) { %>\
								<td>\
								<%  data._(fieldlist).each(function(mv_field, j) { %>\
									<%- data.getFieldValue(data.m, mv_field) %>\
								<% }); %> \
								</td>\
							<% } %> \
						</tr> \
					</tbody> \
				</table> \
			<%}%>';
			var compiledDescriptionTemplate = _.template(_descriptionTemplate,
					null, {
						variable : "data"
					});

			var _additionFieldsTemplate = '\
				<table class="ir-table-no-row-border">\
					<thead>\
						<tr>\
							<td class="ir-header">Additional Fields</td>\
							<td class="ir-header">Value</td>\
							<td class="ir-header">Action</td>\
						</tr>\
					</thead> \
					<tbody> \
						<%  data._(data.fields).each(function(field, i) { %>\
							<% if(data.displayFields.hasOwnProperty(field)) { %>\
								<% var fieldlist = data.m.get(field) %>\
								<% if(fieldlist && fieldlist.length > 0) { %>\
									<% data._(fieldlist).each(function(mv_field, j) { %>\
										<tr>\
											<% if(j==0) { %> \
												<td rowspan="<%=fieldlist.length %>" class="ir-field-key"> <%= data.displayFields[field] %> </td>\
												<td class="ir-field-value"> <%- data.getFieldValue(data.m, mv_field) %>\
											<% } else { %>\
												<td class="ir-field-value ir-no-left-padding"> <%- data.getFieldValue(data.m, mv_field) %>\
											<%}%>\
											<% var tags = data.r.getTags(field, mv_field); %>\
											<% if (tags.length) { %>\
												(<% data._(tags).each(function(tag, idx){ %><span style="color:#999;" data-tagged-field-name="tag::<%- field %>" class="ir-tag"><%- tag %><%if(idx!=tags.length-1){%> <%}%></span><% }); %>)\
											<% } %>\
											</td>\
											<td  class="actions popdown">\
												<a class="ir-popdown-toggle ir-field-actions ir-btn-pill" data-field-name="<%- field %>" data-field-value="<%- data.getFieldValue(data.m, mv_field) %>">\
												<span class="caret"></span>\
												</a>\
											</td>\
										</tr> \
									<% }); %> \
								<% } %> \
							<% } %>\
						<% }); %>\
					</tbody> \
				</table>';
			var compiledAdditionFieldsTemplate = _.template(
					_additionFieldsTemplate, null, {
						variable : "data"
					});

			/*
			 * All templates apart from Description and Additional Fields views 
			 */
			var _otherInformationTemplate = '\
				<table class="ir-table-no-row-border">\
					<tbody> \
						<tr>\
							<td><%=data.compiledEventSourceTemplate({m:data.m, r:data.r, _:data._, getFieldValue: data.getFieldValue, appName: data.appName, SplunkUtil: data.SplunkUtil}, {variable : "data"} )%></td>\
						</tr>\
						<tr>\
							<td><%=data.compiledEventEditHistoryTemplate({m:data.m, r:data.r, _:data._, getFieldValue: data.getFieldValue, appName: data.appName, SplunkUtil: data.SplunkUtil}, {variable : "data"} )%></td>\
						</tr>\
						<tr>\
							<td><%=data.compiledEventDrillDownTemplate({m:data.m, r:data.r, _:data._, getFieldValue: data.getFieldValue, appName: data.appName, SplunkUtil: data.SplunkUtil}, {variable : "data"} )%></td>\
						</tr>\
						<tr> \
							<td><%=data.compiledEventLinkTemplate({m:data.m, r:data.r, _:data._, getFieldValue: data.getFieldValue, appName: data.appName, SplunkUtil: data.SplunkUtil}, {variable : "data"} )%></td>\
						</tr> \
						<tr>\
							<td><%=data.compiledOrgRawTemplate({m:data.m, r:data.r, _:data._, getFieldValue: data.getFieldValue, appName: data.appName, SplunkUtil: data.SplunkUtil, isRawNasty:data.isRawNasty}, {variable : "data"} )%></td>\
						</tr>\
					</tbody> \
				</table>';
			var compiledOtherInformationTemplate = _.template(
					_otherInformationTemplate, null, {
						variable : "data"
					});

			var _eventSourceTemplate = '\
			<%if(data.m.has("source")) { %>\
				<table class="ir-table-no-row-border">\
					<tbody> \
						<tr> <td class="ir-header">Correlation Search:</td></tr>\
						<tr> \
							<% var source = data.getFieldValue(data.m, data.m.get("source").toString()) %>\
							<% if(source) { %>\
								<td>\
									<%if (source !== "Manual Notable Event - Rule") { %>\
										<a href="<%=data.SplunkUtil.make_full_url("app/"+ data.appName + "/correlation_search_edit", {name: source})%>" target="_bank"><%-source%></a> \
									<% } else { %>\
										<%- "None (manually created)" %> \
									<% } %> \
								</td>\
							<% } %> \
						</tr> \
					</tbody> \
				</table> \
			<%}%>';
			var compiledEventSourceTemplate = _.template(_eventSourceTemplate,
					null, {
						variable : "data"
					});

			var _eventEditHistoryTemplate = '\
			<%if(data.m.has("rule_id") && data.m.get("rule_title")) { %>\
				<table class="history ir-table-no-row-border">\
					<tbody> \
						<tr> <td class="ir-header">History:</td></tr>\
						<% var ruleid = data.getFieldValue(data.m, data.m.get("rule_id").toString()) %>\
						<% var ruletitle = data.getFieldValue(data.m, data.m.get("rule_title").toString()) %> \
						<% if (data.m.has("last_comment")) { %>\
							<% var lastComment =data.getFieldValue(data.m, data.m.get("last_comment").toString()) %>\
							<% var reviewTime = data.getFieldValue(data.m, data.m.get("review_time").toString())%> \
							<% var reviewer = data.getFieldValue(data.m, data.m.get("reviewer_realname").toString())%> \
							<tr>\
								<td style="padding-top: 5px; padding-bottom: 5px; font-family: Consolas, Menlo, Monaco, Lucida Console, Liberation Mono, DejaVu Sans Mono, Bitstream Vera Sans Mono, Courier New, monospace, serif; font-size: 11px;">\
									<div style="padding: 5px; border: 1px solid #CCCCCC;">\
										<div style="float: right;"><%-reviewer%></div> \
										<div style="padding-bottom: 10px;"><%-reviewTime%></div> \
										<%-lastComment%>\
									</div>\
								</td> \
							</tr> \
						<% } %> \
						<tr> \
							<td>\
								<% var query = "|`incident_review` | search rule_id=\\""+ ruleid +"\\" | rename status_label as status | fields _time, rule_id, reviewer, urgency, status, owner, comment" %>\
								<a href="<%=data.SplunkUtil.make_full_url("app/"+ data.appName + "/flashtimeline", {q : query})%>" target="_blank">View all review activity for this Notable Event </a>\
							</td>\
						</tr> \
					</tbody> \
				</table> \
			<%}%>';
			var compiledEventEditHistoryTemplate = _.template(
					_eventEditHistoryTemplate, null, {
						variable : "data"
					});

			var _eventDrillDownTemplate = '\
			<%if(data.m.has("drilldown_name") && data.m.get("drilldown_search")) { %>\
				<% 	var drilldownName = data.getFieldValue(data.m,  data.m.get("drilldown_name").toString())  %> \
				<%	var drilldownSearch = data.getFieldValue(data.m,  data.m.get("drilldown_search").toString()) %> \
				<%	drilldownSearch = drilldownSearch.replace("\\"", "\\\"")%> \
				<%	if (!drilldownSearch.charAt(0) === "|") { %> \
				<%		drilldownSearch = "search " +  drilldownSearch%> \
				<%	}%> \
				<table class="drilldown ir-table-no-row-border"> \
					<tbody> \
						<tr>\
							<td class="ir-header">Contributing Events:</td>\
						</tr> \
						<tr> \
							<td>\
								<a href="<%=data.SplunkUtil.make_full_url("app/" + data.appName +"/flashtimeline", {q: drilldownSearch})%>" target="_blank"><%-drilldownName%></a>\
							</td>\
						</tr>\
					</tbody>\
				</table>\
			<%}%>';
			var compiledEventDrillDownTemplate = _.template(
					_eventDrillDownTemplate, null, {
						variable : "data"
					});

			var _eventLinkTemplate = '\
				<%if(data.m.has("drilldown_name") && data.m.get("drilldown_url")) { %>\
					<% 	var drilldownName = data.getFieldValue(data.m, data.m.get("drilldown_name").toString())  %> \
					<%	var drilldownUrl = data.getFieldValue(data.m,  data.m.get("drilldown_url").toString()) %> \
					<table class="drilldown ir-table-no-row-border"> \
						<tbody> \
							<tr>\
								<td class="ir-header">More details:</td>\
							</tr> \
							<tr> \
								<td>\
									<a href="<%=drilldownUrl%>" target="_blank"><%=drilldownName%></a>\
								</td>\
							</tr>\
						</tbody>\
					</table>\
				<%}%>';
			var compiledEventLinkTemplate = _.template(_eventLinkTemplate,
					null, {
						variable : "data"
					});

			var _orgRawTemplate = '\
			<% var orgRaw = data.m.get("orig_raw")%>\
			<% var nastyRaw = true %> \
			<%if(orgRaw) { nastyRaw = data.isRawNasty(orgRaw.toString()); }%>\
			<% if (data.m.has("orig_event_hash") || data.m.has("orig_cd") || (!nastyRaw) ) {%> \
				<table class="orig_raw ir-table-no-row-border"> \
					<tbody> \
						<tr>\
							<td class="ir-header">Original Event:</td>\
						</tr> \
						<%if (!nastyRaw){ %>\
							<tr>\
								<td>\
									<%  var value = orgRaw.toString(); \
										var lines = value.split("\\n"); \
										var limit = Math.min(10, lines.length); \
									%>\
									<div class="event ir-orig-raw-field">\
										<% for(var index=0; index < limit; index++) { %> \
											<% if (index==9 ||  index==lines.length-1) { %> \
												<%-lines[index]%> \
											<% } else { %>\
												<%-lines[index]%> <br/> \
											<% } %> \
										<% } %>\
									</div> \
									<% if(lines.length > 10 ) { %>\
										<% var id = Math.floor(Math.random() * 100000000); %> \
										<div style="display:none;" id=<%=id%> class="event ir-orig-raw-field"> \
											<% for(var index=10; index < lines.length; index++) { %> \
												<%-lines[index]%> <br/>\
											<% }%>\
										</div>\
										<a onclick="$(\'#<%=id%>\').toggle();$(\'#show_<%=id%>\').toggle(); $(\'#hide_<%=id%>\').toggle();return false;">\
											<span id="show_<%=id%>">Show all <%=lines.length%> lines</span> \
											<span style="display: none;" id="hide_<%=id%>">Collapse back to 10 lines</span>\
										</a> \
									<%}%> \
								</td>\
							</tr>\
						<%}%>\
						<%if(data.m.has("orig_event_hash") || data.m.has("orig_cd")) { %>\
							<tr>\
								<td>\
									<%  var origSearch; \
										if(data.m.has("orig_event_hash") ) { origSearch = " | `get_event_hash` | search event_hash=" + data.getFieldValue(data.m, data.m.get("orig_event_hash").toString()); }\
										if(data.m.has("orig_cd") ) { origSearch = " | search _cd=" + data.getFieldValue(data.m, data.m.get("orig_cd").toString()); }\
										if(data.m.has("orig_index") ) { origSearch = " index=" + data.getFieldValue(data.m, data.m.get("orig_index").toString()) + origSearch; }\
										if(data.m.has("orig_splunk_server") ) { origSearch = " splunk_server=" + data.getFieldValue(data.m, data.m.get("orig_splunk_server").toString()) + origSearch; }\
										if(data.m.has("orig_time") ) { origSearch = " _time=" + data.getFieldValue(data.m, data.m.get("orig_time").toString()) + origSearch; }\
										origSearch = origSearch + " | head 1";\
									%>\
									<% var query = data.SplunkUtil.addLeadingSearchCommand(origSearch) %>\
									<a href="<%=data.SplunkUtil.make_full_url("app/"+data.appName+"/flashtimeline", {q: query})%>" target="_blank">View original event</a>\
								</td>\
							</tr>\
						<%}%>\
					</tbody> \
				</table>\
			<%}%>';
			var compiledOrgRawTemplate = _.template(_orgRawTemplate, null, {
				variable : "data"
			});

			/*
			 * Meta information about event like event_hash, eventtype, event_id
			 */
			var _eventMetaInfoTemplate = '\
			<table class="ir-table-no-row-border" style="padding-left: 10px;"> \
				<tbody>\
					<tr> <td class="ir-header">Event Details:</td></tr>\
					<tr> \
						<% var event_id = data.m.get("event_id")?data.m.get("event_id").toString():"" %>\
						<td class="ir-field-key">event_id</td> \
						<td class="ir-field-value"><%=data.getFieldValue(data.m, event_id)%> </td> \
						<td> \
							<a class="ir-popdown-toggle ir-field-actions ir-btn-pill" data-field-name="event_id" data-field-value="<%- data.getFieldValue(data.m, event_id) %>">\
								<span class="caret"></span>\
							</a>\
						</td>\
					</tr>\
					<tr>\
						<% var event_hash = data.m.get("event_hash")?data.m.get("event_hash").toString():"" %>\
						<td class="ir-field-key">event_hash</td>\
						<td class="ir-field-value"><%=data.getFieldValue(data.m, event_hash)%> </td>\
						<td> \
							<a class="ir-popdown-toggle ir-field-actions ir-btn-pill" data-field-name="event_hash" data-field-value="<%- data.getFieldValue(data.m, event_hash) %>">\
								<span class="caret"></span>\
							</a>\
						</td>\
					</tr>\
					<% var eventtype = data.m.get("eventtype") %>\
					<% if(eventtype && eventtype.length > 0) { %>\
						<% data._(eventtype).each(function(mv_field, j) { %>\
							<tr>\
								<% if(j===0) { %> \
									<td rowspan="<%=eventtype.length%>" class="ir-field-key">eventtype</td> \
									<td class="ir-field-value"> <%- data.getFieldValue(data.m, mv_field) %>\
								<% } else { %>\
									<td class="ir-field-value ir-no-left-padding"> <%- data.getFieldValue(data.m, mv_field) %>\
								<%}%>\
								<% var tags = data.r.getTags(eventtype, mv_field); %>\
								<% if (tags.length) { %>\
										(<% data._(tags).each(function(tag, idx){ %><span style="color:#999;" data-tagged-field-name="tag::<%- eventtype %>" class="ir-tag"><%- tag %><%if(idx!=tags.length-1){%> <%}%></span><% }); %>)\
								<% } %>\
								</td>\
								<td> \
									<a class="ir-popdown-toggle ir-field-actions ir-btn-pill" data-field-name="eventtype" data-field-value="<%- data.getFieldValue(data.m, eventtype) %>">\
										<span class="caret"></span>\
									</a>\
								</td>\
							</tr>\
						<%})%>\
					<% } %>\
				</tbody> \
			</table> ';
			var compiledEventMetaInfoTemplate = _.template(
					_eventMetaInfoTemplate, null, {
						variable : "data"
					});

			return FieldsView.extend({
				moduleId: module.id,
				/**
				 * @param {Object} options {
				 *      model: {
				 *         event: <models.services.search.job.ResultsV2.result[i]>,
				 *         summary: <model.services.search.job.SummaryV2>,
				 *         application: <model.Application>,
				 *         searchJob: <models.Job>
				 *     }
				 *     collection: {
				 *         selectedRows: <collections.SelectedRows>
				 *     },
				 *     selectableFields: true|false,
				 *     swappingKey: The swap key to observe a loading event on
				 *     fieldNameMapping : Display field name map with actual field name
				 *
				 * }
				 */
				initialize: function(){
					FieldsView.prototype.initialize.apply(this, arguments);
					this.swappingKey  = this.options.swappingKey;
					this.showAllLines = this.options.showAllLines;
					this.rowExpanded  = 'r' + this.options.idx;
					this.fieldNameMapping = this.options.fieldNameMapping;
				},
				startListening: function() {
					FieldsView.prototype.startListening.apply(this, arguments);

					this.listenTo(this.model.event, 'change', function(model, options) {
						if (options.swap) {
							this.isSwapping = false;
						}
						this.render();
					});

					this.listenTo(this.model.result, 'tags-updated', this.render);

					this.listenTo(this.model.event, 'failed-swap', function() {
						this.$('.event-fields-loading').text(_('We were unable to provide the correct event').t());
					});

					this.listenTo(this.model.state, 'change:' + this.showAllLines, function() { this.isSwapping = true; });

					this.listenTo(this.model.result, this.swappingKey, function() { this.isSwapping = true; });
				},
				activate: function(options) {
					if (this.active) {
						return FieldsView.prototype.activate.apply(this, arguments);
					}
					this.isSwapping = true;
					return FieldsView.prototype.activate.apply(this, arguments);
				},
				setMaxWidth: function() {
					if (!this.el.innerHTML || !this.$el.is(":visible")) {
						return false;
					}

					var $stylesheet =  $("#"+this.cid+"-styles");
					$stylesheet && $stylesheet.remove();

					var $wrapper = this.$el.closest('table').parent(),
					wrapperWidth=$wrapper.width(),
					wrapperLeft=$wrapper.offset().left - $wrapper.scrollLeft(),
					margin=20,
					elLeft=this.$el.offset().left,
					maxWidth= wrapperWidth - (elLeft - wrapperLeft) - margin,
					maxWidthPx = (maxWidth > 500? maxWidth : 500) + "px";

					this.$('table').css('maxWidth', maxWidthPx);
					
					return true;
				},
				reflow: function() {
					this.setMaxWidth();
				},
				render: function() {
					this.$el.html(this.compiledTemplate({
						compiledDescriptionAdditionDetailsTemplate: compiledDescriptionAdditionDetailsTemplate,
						compiledDescriptionTemplate: compiledDescriptionTemplate,
						compiledAdditionFieldsTemplate: compiledAdditionFieldsTemplate,
						compiledEventSourceTemplate : compiledEventSourceTemplate,
						compiledEventEditHistoryTemplate : compiledEventEditHistoryTemplate,
						compiledOtherInformationTemplate : compiledOtherInformationTemplate,
						compiledEventDrillDownTemplate : compiledEventDrillDownTemplate,
						compiledEventMetaInfoTemplate : compiledEventMetaInfoTemplate,
						compiledOrgRawTemplate : compiledOrgRawTemplate,
						compiledEventLinkTemplate: compiledEventLinkTemplate,
						fields : this.model.event.strip(),
						displayFields:this.fieldNameMapping || {},
						getFieldValue : EventViewerUtils.getFieldValue,
						isRawNasty : EventViewerUtils.isRawNasty,
						r: this.model.result,
						m: this.model.event,
						isSwapping: false,
						_:_,
						appName : this.model.application.get('app'),
						SplunkUtil : SplunkUtil
					}));
					this.setMaxWidth();
					return this;
				},
				template:'\
					<% if (!isSwapping) { %>\
					<table class="table-condensed ir-table-no-row-border">\
						<tbody> \
							<tr> \
								<td><%=compiledDescriptionAdditionDetailsTemplate({m:m, r:r, _:_, fields:fields, displayFields:displayFields, compiledDescriptionTemplate: compiledDescriptionTemplate, compiledAdditionFieldsTemplate:compiledAdditionFieldsTemplate, getFieldValue: getFieldValue}, {variable : "data"})%></td>\
								<td style="vertical-align: top;"><%=compiledOtherInformationTemplate({m:m, r:r, _:_, getFieldValue: getFieldValue, appName: appName, SplunkUtil: SplunkUtil, isRawNasty: isRawNasty, compiledEventSourceTemplate:compiledEventSourceTemplate, compiledEventEditHistoryTemplate:compiledEventEditHistoryTemplate, compiledEventDrillDownTemplate:compiledEventDrillDownTemplate, compiledOrgRawTemplate:compiledOrgRawTemplate, compiledEventLinkTemplate:compiledEventLinkTemplate}, {variable : "data"} )%></td>\
							</tr> \
							<tr>\
								<td colspan=2>\
									<table class="ir-table-no-row-border">\
									<tbody> \
										<tr><td>\
											<%=compiledEventMetaInfoTemplate({m:m, getFieldValue:getFieldValue, r:r,  _:_ }, {variable : "data"})%>\
										</td></tr>\
									</tbody>\
									</table>\
								</td>\
							</tr>\
						</tbody> \
					</table> \
					<% } else { %>\
						<div class="event-fields-loading">Loading...</div>\
					<% } %>\
					'
			});
		}
);
