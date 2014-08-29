define(function(require, exports, module) {
	var $ = require("jquery");
	var _ = require("underscore");
	var SplunkUtil = require("splunk.util");
	var SelectedRowsCollection = require("app-components/incident_review/eventsviewer/IRSelectedRowsCollection");
	var EventRenderersCollection = require("collections/services/configs/EventRenderers");
	var WorkflowActionsCollection = require("collections/services/data/ui/WorkflowActions");
	var SearchJobModel = require("models/search/Job");
	var ResultModel = require("models/services/search/jobs/Result");
	var splunkConfig = require('splunk.config');
	var SummaryModel = require("models/services/search/jobs/Summary");
	var console = require("util/console");
	var EventsViewerMaster = require("app-components/incident_review/eventsviewer/IRTableView");
	var EditLinkView = require("app-components/incident_review/eventsviewer/EditLinkView");
	var BaseSplunkView = require("splunkjs/mvc/basesplunkview");
	var Messages = require("splunkjs/mvc/messages");
	var mvc = require("splunkjs/mvc/mvc");
	var PaginatorView = require("splunkjs/mvc/paginatorview");
	var Utils = require("splunkjs/mvc/utils");
	var sharedModels = require('splunkjs/mvc/sharedmodels');
	var GeneralUtils = require('util/general_utils');
	var TokenAwareModel = require('splunkjs/mvc/tokenawaremodel');
	var ReportModel = require('models/search/Report');
	// report model
	var Drilldown = require('splunkjs/mvc/drilldown');
	var Backbone = require('backbone');

	require("css!splunkjs/css/events-viewer");

	// This regex will take a space or comma separated list of fields, with
	// quotes
	// for escaping strings with spaces in them, and match each individual
	// field.
	var fieldSplitterRegex = /(["'].*?["']|[^"',\s]+)(?=\s*|\s*,|\s*$)/g;

	// This regex will take a string that may or may not have leading quotes,
	// and strip them.
	var quoteStripperRegex = /^["']|["|']$/g;

	var EventsViewerView = BaseSplunkView.extend({

		className: "incident-events-viewer",

		options: {
			"managerid": null,
			"data": "events",
			"showPager": true,
			"pagerPosition": "top",
			"maxCount" : 100,
			// TableHeader and TableHeaderfieldName has to be in sync
			"tableHeaderLabels" :['Time', 'Security Domain', 'Title', 'Urgency', 'Status', 'Owner'],
			"tableHeaderFieldNames" : ['_time', 'security_domain', 'rule_title', 'urgency', 'status_label', 'owner_realname'],
			// some of fields are different in display and field actions
			// for example : we need to show "owner_realname" field for the display value, and the "owner" field value for the "owner" value
			"filedNameReplacementForActions" :  {
				"rule_title" : "rule_name",
				"owner_realname" :  "owner"
			},
			"fieldNameMapping" :{
				'action'                    : 'Action',
				'app'                       : 'Application',
				'bytes_in'                  : 'Bytes In',
				'bytes_out'                 : 'Bytes Out',
				'category'                  : 'Category',
				'change_type'               : 'Change Type',
				'channel'                   : 'Channel',
				'command'                   : 'Command',
				'cpu_load_percent'          : 'CPU Load (%)',
				'cve'                       : 'CVE',
				'decoration'                : 'Decoration',
				'desc'                      : 'Description',
				'dest'                      : 'Destination',
				'dest_threatlist_category'   : 'Destination Threat List Category',
				'dest_threatlist_description': 'Destination Threat List Description',
				'dest_threatlist_name'       : 'Destination Threat List Name',
				'dest_bunit'                : 'Destination Business Unit',
				'dest_category'             : 'Destination Category',
				'dest_city'                 : 'Destination City',
				'dest_country'              : 'Destination Country',
				'dest_dns'                  : 'Destination DNS',
				'dest_ip'                   : 'Destination IP Address',
				'dest_is_expected'          : 'Destination Expected',
				'dest_lat'                  : 'Destination Latitude',
				'dest_long'                 : 'Destination Longitude',
				'dest_mac'                  : 'Destination MAC Address',
				'dest_nt_domain'            : 'Destination NT Domain',
				'dest_nt_host'              : 'Destination NT Hostname',
				'dest_owner'                : 'Destination Owner',
				'dest_pci_domain'           : 'Destination PCI Domain',
				'dest_port'                 : 'Destination Port',
				'dest_record'               : 'Destination Record',
				'dest_should_timesync'      : 'Destination Should Time Synchronize',
				'dest_should_update'        : 'Destination Should Update',
				'dest_requires_av'          : 'Destination Requires Antivirus',
				'dest_translated_ip'        : 'Destination Translated IP Address',
				'dest_translated_port'      : 'Destination Translated Port',
				'dest_zone'                 : 'Destination Zone',
				'dhcp_pool'                 : 'DHCP Pool',
				'direction'                 : 'Direction',
				'dns'                       : 'DNS',
				'duration'                  : 'Duration',
				'dvc'                       : 'Device',
				'dvc_bunit'                 : 'Device Business Unit',
				'dvc_category'              : 'Device Category',
				'dvc_city'                  : 'Device City',
				'dvc_country'               : 'Device Country',
				'dvc_dns'                   : 'Device DNS',
				'dvc_ip'                    : 'Device IP Address',
				'dvc_is_expected'           : 'Device Expected',
				'dvc_lat'                   : 'Device Latitude',
				'dvc_long'                  : 'Device Longitude',
				'dvc_mac'                   : 'Device MAC Address',
				'dvc_nt_host'               : 'Device NT Hostname',
				'dvc_owner'                 : 'Device Owner',
				'dvc_pci_domain'            : 'Device PCI Domain',
				'dvc_should_timesync'       : 'Device Should Time Synchronize',
				'dvc_should_update'         : 'Device Should Update',
				'dvc_requires_av'           : 'Device Requires Antivirus',
				'end_time'                  : 'End Time',
				'file_access_time'          : 'File Access Time',
				'file_create_time'          : 'File Creation Time',
				'file_hash'                 : 'File Hash',
				'file_modify_time'          : 'File Modify Time',
				'file_name'                 : 'File Name',
				'file_path'                 : 'File Path',
				'file_permission'           : 'File Permission',
				'file_size'                 : 'File Size',
				'FreeMBytes'                : 'Free Megabytes',
				'gap'                       : 'Gap',
				'gid'                       : 'GID',
				'hash'                      : 'Hash',
				'http_content_type'         : 'HTTP Content Type',
				'http_method'               : 'HTTP Method',
				'http_referrer'             : 'HTTP Referrer',
				'http_user_agent'           : 'HTTP User Agent',
				'ids_type'                  : 'Intrusion Detection Type',
				'iin_issuer'                : 'Issuer Identification Number (IIN)',
				'ip'                        : 'IP Address',
				'ip_version'                : 'Internet Protocol Version',
				'is_interactive'            : 'Interactive',
				'is_lockout'                : 'Is Lockout',
				'is_privileged'             : 'Is Privileged',
				'isdir'                     : 'Is Directory',
				'length'                    : 'Length',
				'location'                  : 'Location',
				'log_level'                 : 'Log Level',
				'mac'                       : 'MAC Address',
				'mem'                       : 'Total Memory',
				'mem_committed'             : 'Committed Memory',
				'mem_free'                  : 'Free Memory',
				'mem_used'                  : 'Used Memory',
				'mode'                      : 'Mode',
				'modtime'                   : 'Modification Time',
				'mount'                     : 'Mount',
				'name'                      : 'Name',
				'note'                      : 'Note',
				'nt_host'                   : 'NT Hostname',
				'object_handle'             : 'Object Handle',
				'object_name'               : 'Object Name',
				'object_type'               : 'Object Type',
				'orig_host'                 : 'Host',
				'orig_host_bunit'           : 'Host Business Unit',
				'orig_host_category'        : 'Host Category',
				'orig_host_city'            : 'Host City',
				'orig_host_country'         : 'Host Country',
				'orig_host_dns'             : 'Host DNS',
				'orig_host_ip'              : 'Host IP Address',
				'orig_host_is_expected'     : 'Host Expected',
				'orig_host_lat'             : 'Host Latitude',
				'orig_host_long'            : 'Host Longitude',
				'orig_host_mac'             : 'Host MAC Address',
				'orig_host_nt_host'         : 'Host NT Hostname',
				'orig_host_owner'           : 'Host Owner',
				'orig_host_pci_domain'      : 'Host PCI Domain',
				'orig_host_should_timesync' : 'Host Should Time Synchronize',
				'orig_host_should_update'   : 'Host Should Update',
				'orig_host_requires_av'     : 'Host Requires Av',
				'os'                        : 'Operating System',
				'os_name'                   : 'Operating System Name',
				'os_release'                : 'Operating System Release',
				'outbound_interface'        : 'Outbound Interface',
				'package'                   : 'Package',
				'package_title'             : 'Package Title',
				'packets_in'                : 'Packets In',
				'packets_out'               : 'Packets Out',
				'path'                      : 'Path',
				'PercentFreeSpace'          : 'Free Space (%)',
				'PercentProcessorTime'      : 'Processor Time (%)',
				'pid'                       : 'Process Identifier',
				'pii'                       : 'Personally Identifiable Information (PII)',
				'port'                      : 'Port',
				'process'                   : 'Process',
				'product'                   : 'Product',
				'product_version'           : 'Product Version',
				'proto'                     : 'Internet Protocol',
				'reason'                    : 'Reason',
				'recipient'                 : 'Recipient',
				'record_class'              : 'Record Class',
				'record_type'               : 'Record Type',
				'result'                    : 'Result',
				'rule_number'               : 'Rule Identifier',
				'selinux'                   : 'SELinux',
				'selinuxtype'               : 'SELinux Type',
				'sender'                    : 'Sender',
				'session_id'                : 'Session Identifier',
				'setlocaldefs'              : 'Set Local Definitions',
				'severity_id'               : 'Severity Identifier ',
				'signature'                 : 'Signature',
				'signature_id'              : 'Signature Identifier',
				'signature_version'         : 'Signature Version',
				'size'                      : 'Size',
				'src'                       : 'Source',
				'src_threatlist_category'    : 'Source Threat List Category',
				'src_threatlist_description' : 'Source Threat List Description',
				'src_threatlist_name'        : 'Source Threat List Name',
				'src_bunit'                 : 'Source Business Unit',
				'src_category'              : 'Source Category',
				'src_city'                  : 'Source City',
				'src_country'               : 'Source Country',
				'src_dns'                   : 'Source DNS',
				'src_ip'                    : 'Source IP Address',
				'src_is_expected'           : 'Source Expected',
				'src_lat'                   : 'Source Latitude',
				'src_long'                  : 'Source Longitude',
				'src_mac'                   : 'Source MAC Address',
				'src_nt_domain'             : 'Source NT Domain',
				'src_nt_host'               : 'Source NT Hostname',
				'src_owner'                 : 'Source Owner',
				'src_pci_domain'            : 'Source PCI Domain',
				'src_port'                  : 'Source Port',
				'src_record'                : 'Source Record',
				'src_should_timesync'       : 'Source Should Time Synchronize',
				'src_should_update'         : 'Source Should Update',
				'src_requires_av'           : 'Source Requires Antivirus',
				'src_translated_ip'         : 'Source Translated IP Address',
				'src_translated_port'       : 'Source Translated Port',
				'src_user'                  : 'Source User',
				'src_user_group'            : 'Source User Group',
				'src_user_group_id'         : 'Source User Group Identifier',
				'src_user_id'               : 'Source User Identifier',
				'src_user_privilege'        : 'Source User Privilege',
				'src_zone'                  : 'Source Zone',
				'sshd_protocol'             : 'SSHD Protocol',
				'ssid'                      : 'Service Set Identifier (SSID)',
				'storage'                   : 'Total Storage',
				'storage_free'              : 'Free Storage',
				'storage_free_percent'      : 'Free Storage (%)',
				'storage_used'              : 'Used Storage',
				'storage_used_percent'      : 'Used Storage (%)',
				'start_mode'                : 'Start Mode',
				'start_time'                : 'Start Time',
				'StartMode'                 : 'Start Mode',
				'subject'                   : 'Subject',
				'syslog_facility'           : 'Syslog Facility',
				'syslog_priority'           : 'Syslog Priority',
				'SystemUpTime'              : 'System Uptime',
				'tcp_flags'                 : 'TCP Flags',
				'threat_ip'                 : 'Threat IP',
				'tos'                       : 'Type Of Service',
				'TotalMBytes'               : 'Total Megabytes',
				'transaction_id'            : 'Transaction Identifier',
				'transport'                 : 'Transport Protocol',
				'ttl'                       : 'Time To Live',
				'uid'                       : 'UID',
				'uptime'                    : 'Uptime',
				'url'                       : 'URL',
				'UsedMBytes'                : 'Used Megabytes',
				'user'                      : 'User',
				'user_group'                : 'User Group',
				'user_group_id'             : 'User Group Identifier',
				'user_id'                   : 'User Identifier',
				'user_privilege'            : 'User Privilege',
				'validity'                  : 'Validity',
				'vendor'                    : 'Vendor',
				'vendor_product'            : 'Vendor/Product',
				'view'                      : 'View',
				'vlan_id'                   : 'VLAN Identifier',
				'vlan_name'                 : 'VLAN Name'
			}
		},

		reportDefaults: {
			"display.events.fields": '["host", "source", "sourcetype"]',
			"display.events.type": "list",
			"display.prefs.events.count": 20,
			"display.events.maxLines": "5"
		},

		omitFromSettings: ["el", "id", "name", "manager",
		"reportModel", "displayRowNumbers", "segmentation",
		"softWrap"],

		normalizeOptions: function(settings, options) {
			if (!options.hasOwnProperty("count") && !settings.has("count")) {
				settings.set("count", this.reportDefaults['display.prefs.events.count']);
			}

			if (!options.hasOwnProperty("maxLines") && !settings.has("maxLines")) {
				settings.set("maxLines", this.reportDefaults['display.events.count'].toString());
			} else {
				settings.set("maxLines", settings.get('maxLines').toString());
			}
		},

		initialize: function(options) {
			this.configure();
			this.model = this.options.reportModel || TokenAwareModel._createReportModel(this.reportDefaults);
			this.settings._sync = Utils.syncModels({
				source: this.settings,
				dest: this.model,
				prefix: "display.events.",
				include: ["fields", "type", "count", "rowNumbers", "maxLines"],
						 exclude: ["drilldownRedirect", "managerid", "tableHeaderLabels", "tableHeaderFieldName", "fieldNameMapping", "filedNameReplacementForActions"],
						 auto: true,
						 alias: {
							 count: 'display.prefs.events.count'
						 }
				});
				this.settings.on("change", this.onSettingsChange, this);

				this.normalizeOptions(this.settings, options);

				this.resultModel = new ResultModel();

				this.summaryModel = new SummaryModel();

				this.searchJobModel = new SearchJobModel();

				this.reportModel = new ReportModel();
				this.reportModel._syncPush = Utils.syncModels({
					source: this.model,
					dest: this.reportModel.entry.content,
					tokens: false,
					auto: 'push'
				});
				this.reportModel._syncPull = Utils.syncModels({
					source: this.model,
					dest: this.reportModel.entry.content,
					tokens: false,
					auto: 'pull'
				});
				this.listenTo(this.reportModel, 'eventsviewer:drilldown', this.handleMiscDrilldown);

				this.applicationModel = sharedModels.get("app");

				this.selectedRowsCollection = new SelectedRowsCollection();

				this.workflowActionsCollection = new WorkflowActionsCollection();
				this.workflowActionsCollection.fetch({
					data: {
						app: this.applicationModel.get("app"),
						owner: this.applicationModel.get("owner"),
						count: -1,
						sort_key: "name"
					},
					success: _.bind(function() {
						this._isWorkflowActionsCollectionReady = true;
						this.render();
					}, this)
				});


				this.eventRenderersCollection = new EventRenderersCollection();
				this.eventRenderersCollection.fetch({
					success: _.bind(function() {
						this._isEventRenderersCollectionReady = true;
						this.render();
					}, this)
				});

				this._lastJobFetched = null;

				this.bindToComponentSetting('managerid', this.onManagerChange, this);
				
				this.backboneEventMediator = _.extend({}, Backbone.Events);

				this.editLinkView = new EditLinkView({
					model: {
						result: this.resultModel,  // <models.services.search.jobs.Results>
						summary: this.summaryModel,  // <models.services.search.jobs.Summary>
						report: this.reportModel,  // <models.services.SavedSearch>
						application: this.applicationModel // <models.Application>
					},
					collection: {
						selectedRows: this.selectedRowsCollection  // <collections.SelectedRow>
					},
					backboneEventMediator : this.backboneEventMediator // If events needs to be trigger to other views
				});
				
				this.eventsViewer = new EventsViewerMaster({
					model: {
						result: this.resultModel,  // <models.services.search.jobs.Results>
						summary: this.summaryModel,  // <models.services.search.jobs.Summary>
						searchJob: this.searchJobModel,  // <models.Job>
						report: this.reportModel,  // <models.services.SavedSearch>
						application: this.applicationModel // <models.Application>
					},
					collection: {
						selectedRows: this.selectedRowsCollection,  // <collections.SelectedRow>
						workflowActions: this.workflowActionsCollection,  // <collections.services.data.ui.WorkflowActions>
						eventRenderers: this.eventRenderersCollection  // <collections/services/configs/EventRenderers>
					},
					selectableFields: false,  // true|false
					headerMode: "none",  // dock|none (eventually
					// this will have static
					// mode)
					allowRowExpand: true,  // true|false
					defaultDrilldown: false,
					tableHeaderLabels :  this.options.tableHeaderLabels,
					tableHeaderFieldNames : this.options.tableHeaderFieldNames,
					fieldNameMapping : this.options.fieldNameMapping,
					backboneEventMediator : this.backboneEventMediator,
					filedNameReplacementForActions : this.options.filedNameReplacementForActions
				});
				this.listenTo(this.eventsViewer, 'drilldown', this.emitDrilldownEvent);

				// If we don't have a manager by this point,
				// then we're going to
				// kick the manager change machinery so that it
				// does whatever is
				// necessary when no manager is present.
				if (!this.manager) {
					this.onManagerChange(mvc.Components, null);
				}
			},

			onManagerChange: function(ctxs, manager) {
				if (this.manager) {
					this.manager.off(null, null, this);
					this.manager = null;
				}
				if (this.eventData) {
					this.eventData.off();
					this.eventData.destroy();
					this.eventData = null;
				}
				if (this.summaryData) {
					this.summaryData.off();
					this.summaryData.destroy();
					this.summaryData = null;
				}

				this._searchStatus = null;
				this._eventCount = 0;
				this._isSummaryModelReady = false;
				this._isSearchJobModelReady = false;
				this._lastJobFetched = null;

				this.resultModel.setFromSplunkD({});
				this.summaryModel.setFromSplunkD({});

				if (!manager) {
					this._searchStatus = { state: "nomanager" };
					this.render();
					return;
				}

				// Clear any messages, since we have a new
				// manager.
				this._searchStatus = { state: "start" };

				this.manager = manager;
				this.manager.on("search:start", this.onSearchStart, this);
				this.manager.on("search:progress", this.onSearchProgress, this);
				this.manager.on("search:done", this.onSearchDone, this);
				this.manager.on("search:cancelled", this.onSearchCancelled, this);
				this.manager.on("search:refresh", this.onSearchRefreshed, this);
				this.manager.on("search:error", this.onSearchError, this);
				this.manager.on("search:fail", this.onSearchFailed, this);

				this.eventData = this.manager.data("events", {
					autofetch: false,
					output_mode: "json",
					truncation_mode: "abstract"
				});
				this.eventData.on("data", this.onEventData, this);
				this.eventData.on("error", this.onSearchError, this);

				this.summaryData = this.manager.data("summary", {
					autofetch: false,
					output_mode: "json",
					top_count: 10,
					output_time_format: "%d/%m/%y %l:%M:%S.%Q %p"
				});
				this.summaryData.on("data", this.onSummaryData, this);
				this.summaryData.on("error", this._onSummaryError, this);

				// Handle existing job
				var content = this.manager.get("data");
				if (content && content.eventAvailableCount) {
					this.onSearchStart(content);
					this.onSearchProgress({ content: content });
					if (content.isDone) {
						this.onSearchDone({ content: content });
					}
				} else {
					this.render();
				}
				manager.replayLastSearchEvent(this);
			},

			_fetchJob: function(job) {
				this._isRealTimeSearch = job.isRealTimeSearch;
				if(this._lastJobFetched !== job.sid) {
					this._lastJobFetched = job.sid;
					this.searchJobModel.set("id", job.sid);
				}
				var state = this.manager.job.state();
				if (_(state).size() === 0) {
					return;
				}
				this.searchJobModel.setFromSplunkD({ entry: [state] });
				if (!this._isSearchJobModelReady) {
					this._isSearchJobModelReady = true;
					this.render();
				}
			},

			onSearchStart: function(job) {
				this._searchStatus = { state: "running" };
				this._eventCount = 0;
				this._statusBuckets = undefined;
				this._lastJobFetched = null;
				this._isSummaryModelReady = false;
				this._isSearchJobModelReady = false;

				this.resultModel.setFromSplunkD({});
				this.summaryModel.setFromSplunkD({});
				this._fetchJob(job);

				this.render();
			},

			onSearchProgress: function(properties) {
				this._searchStatus = { state: "running" };
				properties = properties || {};
				var job = properties.content || {};
				var eventCount = job.eventAvailableCount || 0;
				var statusBuckets = this._statusBuckets = job.statusBuckets || 0;
				var searchString = properties.name;
				var isRealTimeSearch = job.isRealTimeSearch;
				this._fetchJob(job);

			   // If we have a search string, then we set it on
			   // the report model,
			   // otherwise things like the intentions parser
			   // don't work. We do it
			   // silently however to ensure that nobody picks
			   // it up until they
			   // need it.
			   if (searchString) {
				   // Since this search comes from the API, we
				   // need to strip away
				   // the leading search command safely.
					searchString = SplunkUtil.stripLeadingSearchCommand(searchString);
					this.reportModel.entry.content.set('search', searchString, {silent: true});
				}

				this._eventCount = eventCount;

				if (eventCount > 0) {
					this.updateEventData();
				}

			   // (Continuously request realtime summaries,
			   // even if there are
			   // no status buckets, as some kind of summary
			   // data - even blank
			   // data - is required for the EventsViewerView
			   // to display anything.
			   // Non-realtime jobs will eventually complete
			   // and get summary data
			   // at that time even if statusBuckets is 0
			   // because we ask for
			   // summary data when the search is done.)
				if (statusBuckets > 0 || isRealTimeSearch) {
					this.updateSummaryData();
				}

				this.render();
			},

			onSearchDone: function(properties) {
				this._searchStatus = { state: "done" };

				properties = properties || {};
				var job = properties.content || {};
				var eventCount = job.eventAvailableCount || 0;
				this._fetchJob(job);

				this._eventCount = eventCount;

				this.updateEventData();
				this.updateSummaryData();
				this.render();
			},

			onSearchCancelled: function() {
				this._searchStatus = { state: "cancelled" };
				this.render();
			},

			onSearchRefreshed: function() {
				this._searchStatus = { state: "refresh" };
				this.render();
			},

			onSearchError: function(message, err) {
				var msg = Messages.getSearchErrorMessage(err) || message;
				this._searchStatus = { state: "error", message: msg };
				this.render();
			},

			onSearchFailed: function(state) {
				var msg = Messages.getSearchFailureMessage(state);
				this._searchStatus = { state: "error", message: msg };
				this.render();
			},

			onEventData: function(model, data) {
				this.resultModel.setFromSplunkD(data);
				this.render();
			},

			onSummaryData: function(model, data) {
				this.summaryModel.setFromSplunkD(data);
				if (!this._isSummaryModelReady) {
					this._isSummaryModelReady = true;
					this.render();
				}
			},

			_onSummaryError: function(message, err) {
				this.onSearchError(message, err);
			},

			onSettingsChange: function(model) {
				if (model.hasChanged("showPager") ||
						model.hasChanged("pagerPosition") ||
						model.hasChanged("count") ||
						model.hasChanged("fields")) {
					this.render();
				}
				if (model.hasChanged("showPager") ||
						model.hasChanged("type") ||
						model.hasChanged("count") ||
						model.hasChanged("maxLines") ||
						model.hasChanged("list.drilldown")) {
					this.updateEventData();
				}
			},

			emitDrilldownEvent: function(e, defaultDrilldown) {
				var displayType = this.model.get('display.events.type');
				var drilldownMode = this.settings.get(displayType + '.drilldown');
				if (drilldownMode === 'none' ||
						(displayType === 'table' && SplunkUtil.normalizeBoolean(drilldownMode) === false)) {
					return;
				}
				var field = e.data.field;
				var value = e.data.value;
				if (field === undefined && e.data.action === 'addterm') {
					field = '_raw';
				} else if (field === undefined && e._time) {
					field = '_time';
					value = SplunkUtil.getEpochTimeFromISO(e._time);
				}
				var data = {
						'click.name': field,
						'click.value': value,
						'click.name2': field,
						'click.value2': value
				};
				var idx = e.idx;
				if (idx !== undefined && idx >= 0) {
					var event = this.resultModel.results.at(idx).toJSON();
					if (event) {
						_.each(event, function(value, field) {
							data['row.' + field] = value.length > 1 ? value.join(',') : value[0];
						});
						var earliest = SplunkUtil.getEpochTimeFromISO(event._time);
						data.earliest = earliest;
						data.latest = String(parseFloat(earliest) + 1);
					}
				}

				var defaultDrilldownCallback = _.bind(this._onIntentionsApplied, this, e);
				var reportModel = this.model;
				var payload = Drilldown.createEventPayload({
					field: field,
					data: data,
					event: e
				}, function() {
					var searchAttributes = _.pick(reportModel.toJSON({ tokens: true }),
							'search', 'dispatch.earliest_time', 'dispatch.latest_time');
					defaultDrilldown().done(defaultDrilldownCallback).always(function() {
						// Restore search settings on the report
						// model
						reportModel.set(searchAttributes, { tokens: true, silent: true });
					});
				});
				this.trigger('drilldown click', payload, this);
				if (this.settings.get("drilldownRedirect") && !payload.defaultPrevented()) {
					payload.drilldown();
				}
			},

			_onIntentionsApplied: function(e) {
				var model = this.reportModel.entry.content;
				var search = model.get("search");
				var timeRange = {
						earliest: model.get("dispatch.earliest_time"),
						latest: model.get("dispatch.latest_time")
				};
				if (timeRange.earliest === this.manager.get('earliest_time') &&
						timeRange.latest === this.manager.get('latest_time')) {
					timeRange = Drilldown.getNormalizedTimerange(this.manager);
				}
				var data = _.extend({ q: search }, timeRange);
				var preventRedirect = false;
				this.trigger('drilldown:redirect', { data: data, preventDefault: function() { preventRedirect = true; }});
				if (!preventRedirect) {
					var drilldownFunction = splunkConfig.ON_DRILLDOWN || Drilldown.redirectToSearchPage;
					drilldownFunction(data, e.event.ctrlKey || e.event.metaKey);
				}
			},

			// Handle clicks on links in the field info dropdown
			// ("Top values over time", etc)
			handleMiscDrilldown: function() {
				var drilldownFunction = splunkConfig.ON_DRILLDOWN || Drilldown.redirectToSearchPage;
				var data = {
						q: this.reportModel.entry.content.get('search'),
						earliest: this.reportModel.entry.content.get('dispatch.earliest_time') || '',
						latest: this.reportModel.entry.content.get('dispatch.latest_time') || ''
				};
				drilldownFunction(data);
			},

			onPageChange: function() {
				this.updateEventData();
			},

			updateEventData: function() {
				if (this.eventData) {
					var pageSize = this.paginator ? parseInt(this.paginator.settings.get("pageSize"), 10) : 0;
					var page = this.paginator ? parseInt(this.paginator.settings.get("page"), 10) : 0;
					var type = this.settings.get("type");
					var offset = pageSize * page;
					var count = parseInt(this.settings.get("count"), 10) || this.reportDefaults['display.prefs.events.count'];
					var postProcessSearch = _.isFunction(this.manager.query.postProcessResolve)? this.manager.query.postProcessResolve():"";
					if (this._isRealTimeSearch && !postProcessSearch) {
						// For real-time searches we want the
						// tail of available events, therefore
						// we set a negative offset
						// based on the currently selected page
						offset = 0 - count - offset;
					}
					var maxLines = this.settings.get("maxLines").toString();
					var listDrilldown = this.settings.get("list.drilldown");
					var segmentation = listDrilldown;
					var search = null;

					// if user explicitly sets count over 100,
					// it will display the default
					count = (count > this.options.maxCount || count < 1) ? this.reportDefaults['display.prefs.events.count'] : count;

					// Ensuring segmentation is one of "inner",
					// "outer", or "full".
					// Although "none" is a valid value for
					// segmentation,
					// and segmentation is an optional parameter
					// for the events endpoint,
					// either case causes the Result model to
					// throw errors.
					segmentation = segmentation ? segmentation.toLowerCase() : null;
					switch (segmentation) {
					case "inner":
					case "outer":
					case "full":
					case "none":
						break;
					default:
						segmentation = "full";
					break;
					}

					// add in fields required for events viewer
					// note that we store the fields internally
					// as JSON strings, so
					// we need to parse them out.
					var fields = JSON.parse(this.settings.get("fields"));
					fields = _.union(fields, ['_raw', '_time', '_audit', '_decoration', 'eventtype', 'linecount', '_fulllinecount']);
					if (this._isRealTimeSearch) {
						fields = _.union(fields, ['_serial', 'splunk_server']);
					}

					// fetch events
					this.eventData.set({
						offset: offset,
						count: count,
						max_lines: maxLines,
						segmentation: segmentation,
						search: search,
						fields: fields
					});

					this.eventData.fetch();
				}
			},

			updateSummaryData: function() {
				if (this.summaryData) {
					this.summaryData.fetch();
				}
			},

			render: function() {
				var searchStatus = this._searchStatus || null;
				var eventCount = this._eventCount || 0;
				var hasStatusBuckets = this._statusBuckets === undefined || this._statusBuckets > 0;
				var isSummaryModelReady = (this._isSummaryModelReady === true);
				var isSearchJobModelReady = (this._isSearchJobModelReady === true);
				var isWorkflowActionsCollectionReady = (this._isWorkflowActionsCollectionReady === true);
				var isEventRenderersCollectionReady = (this._isEventRenderersCollectionReady === true);
				var areModelsReady = (isSummaryModelReady && isSearchJobModelReady && isWorkflowActionsCollectionReady && isEventRenderersCollectionReady);
				var showPager = SplunkUtil.normalizeBoolean(this.settings.get("showPager"));
				var pagerPosition = this.settings.get("pagerPosition");
				var count = parseInt(this.settings.get("count"), 10) || this.reportDefaults['display.prefs.events.count'];

				// if user explicitly sets count over 100, it
				// will display the default
				count = (count > this.options.maxCount || count < 1) ? this.reportDefaults['display.prefs.events.count'] : count;

				// render message
				var message = null;
				if (searchStatus) {
					switch (searchStatus.state) {
					case "nomanager":
						message = "no-search";
						break;
					case "start":
						message = "empty";
						break;
					case "running":
						if (eventCount === 0 || !areModelsReady) {
							message = "waiting";
						}
						break;
					case "cancelled":
						message = "cancelled";
						break;
					case "refresh":
						message = "refresh";
						break;
					case "done":
						if (eventCount === 0) {
							message = "no-events";
						}
						break;
					case "error":
						message = {
							level: "error",
							icon: "warning-sign",
							message: searchStatus.message
					};
						break;
					default:
						message = "unknown";
						break;
					}
				}

				if (message) {
					if (!this.messageElement) {
						this.messageElement = $('<div class="msg"></div>');
					}

					Messages.render(message, this.messageElement);

					this.$el.append(this.messageElement);
				} else {
					if (this.messageElement) {
						this.messageElement.remove();
						this.messageElement = null;
					}
				}

				// render eventsViewer
				if (areModelsReady && searchStatus && !message) {
					if (this.eventsViewer && !this._eventsViewerRendered) {
						this._eventsViewerRendered = true;
						this.eventsViewer.render();
						this.$el.append(this.eventsViewer.el);
						// edit link
						this.editLinkView.render();
						this.$el.prepend(this.editLinkView.el);
					}
					this.eventsViewer.activate({deep: true}).$el.show();
					this.editLinkView.activate({deep: true}).$el.show();
					
				} else {
					if (this.eventsViewer) {
						this.editLinkView.deactivate({deep: true}).$el.hide();
						this.eventsViewer.deactivate({deep: true}).$el.hide();
					}
				}

				// render paginator
				if (areModelsReady && searchStatus && !message && showPager) {
					if (!this.paginator) {
						this.paginator = new PaginatorView({
							id: _.uniqueId(this.id + "-paginator")
						});
						this.paginator.$el.addClass("ir-pagination-right");
						this.paginator.settings.on("change:page", this.onPageChange, this);
					}

					this.paginator.settings.set({
						pageSize: count,
						itemCount: eventCount
					});

					if (pagerPosition === "top") {
						this.$el.prepend(this.paginator.el);
					} else {
						this.$el.append(this.paginator.el);
					}
				} else {
					if (this.paginator) {
						this.paginator.settings.off("change:page", this.onPageChange, this);
						this.paginator.remove();
						this.paginator = null;
					}
				}

				this.trigger('rendered', this);

				return this;
			},
			remove: function() {
				if (this.eventsViewer) {
					this.eventsViewer.deactivate({deep: true});
					this.eventsViewer.remove();
					this.eventsViewer = null;
				}

				if (this.paginator) {
					this.paginator.settings.off("change:page", this.onPageChange, this);
					this.paginator.remove();
					this.paginator = null;
				}

				if (this.eventData) {
					this.eventData.off();
					this.eventData.destroy();
					this.eventData = null;
				}

				if (this.summaryData) {
					this.summaryData.off();
					this.summaryData.destroy();
					this.summaryData = null;
				}

				if (this.settings) {
					this.settings.off();
					if (this.settings._sync) {
						this.settings._sync.destroy();
					}
				}

				if (this.reportModel) {
					this.reportModel.off();
					if (this.reportModel._syncPush) {
						this.reportModel._syncPush.destroy();
					}
					if (this.reportModel._syncPull) {
						this.reportModel._syncPull.destroy();
					}
				}
				if(this.editLinkView) {
					this.editLinkView.deactivate({deep: true});
					this.editLinkView.remove();
					this.editLinkView = null;
				}
				BaseSplunkView.prototype.remove.call(this);
			}

	});

	return EventsViewerView;

});
