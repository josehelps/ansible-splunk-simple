/* Rules
 * Requires SOLNIncludeD3 module
 */

Splunk.Module.SOLNGauge = $.klass(Splunk.Module.DispatchingModule, {
	initialize : function($super, container) {
		$super(container);

		//Set up internal variables
		this.valueField = this.getParam("valueField") ? this.getParam("valueField") : "x";
		this.thresholdFieldsLength = Number(this.getParam("thresholdFieldsLength") ? this.getParam("thresholdFieldsLength") : 4);

		//Required
		this.height = this.getParam("height") ? this.getParam("height") : 230;
		this.height = parseInt(this.height, 10);

		// Required
		this.width = this.getParam("width") ? this.getParam("width") : 230;
		// Resize based upon container parent width
		this.width = Math.min(parseInt(this.width, 10), $(this.container).width());

		// Optional
		this.enableResize = this.getParam("enableResize") ? this.getParam("enableResize") : false;

		// Gauge type (optional)
		this.gaugeType = this.getParam("gaugeType") ? this.getParam("gaugeType") : "noelGauge";

		// ticks
		this.showTicks = this.getParam('showTicks');

		this.$container = $(this.container);

		if (!(this.gaugeType === 'noelGauge' || this.gaugeType === 'smileyGauge')) {
			// No supported Gauge type
			console.log('Not supported Gauge type.');
			var html = '<p class="resultStatusMessage empty_results">Not supported gauge type</p>';
			this.$container.html(html);
			return;
		}

		this.requireResize = false;

		// Windows resizing
		$(this.container).resize( function() {
			// Update svg element height or width, others child elements will be resized
			var curWidth = Math.max($('#' + this.moduleId).select('svg').width(), 60);
			var curHeight = Math.max($('#' + this.moduleId).select('svg').height(), 60);
			if (curWidth !== this.width || curHeight !== this.height) {
				this.requireResize = true;
			}

			if (Splunk.util.normalizeBoolean(this.requireResize)) {
				if (this.gaugeType === 'noelGauge') {
					this.resizeNoelGauge(curHeight, curWidth);
				} else {
					// other gauge resizing is not supported yet
					console.log("resizing is not supported for this type of Gauge.");
				}
				this.requireResize = false;
				this.height = curHeight;
				this.width = curWidth;
			}
		}.bind(this));

		// Resizing
		if (Splunk.util.normalizeBoolean(this.enableResize)) {
			this.enableResizable();
		}

		//Context flow gates
		this.doneUpstream = false;
		this.gettingResults = false;
		this.logger.info(this.moduleType, "Initialized module...");
	},

	onContextChange : function() {
		var context = this.getContext();
		if (context.get("search").job.isDone()) {
			this.getResults();
		} else {
			this.doneUpstream = false;
		}
	},

	onJobDone : function() {
		this.getResults();
	},

	getResultURL : function() {
		//Watch this one it has a lot of magic in it to make it
		//compatible with the paginator
		var context = this.getContext();
		var params = {};
		var url;
		var search = context.get("search");
		params['search'] = search.getPostProcess() || "";
		params['outputMode'] = "json";
		if (search.job.isDone()) {
			url = search.getUrl("results");
		} else {
			url = search.getUrl("results") + "_preview";
		}
		return url + "?" + Splunk.util.propToQueryString(params);
	},

	getResults : function($super) {
		this.doneUpstream = true;
		this.gettingResults = true;
		return $super();
	},

	initializeChartFormatterVar : function() {
		this.showValue = this.getContext().get("charting.chart.showValue") ? this.getContext().get("charting.chart.showValue") : true;
		this.showLabels = this.getContext().get("charting.chart.showLabels") ? this.getContext().get("charting.chart.showLabels") : true;
		this.chartColors = this.getContext().get('charting.gaugeColors');
		this.gaugeStyle = this.getContext().get('charting.chart.style') !== "shiny" ? false : true;
		this.displayField = this.getContext().get('charting.primaryAxisTitle.text');
		this.rangeValues = this.getContext().get('charting.chart.rangeValues');
		this.rangeStartAngle = this.getContext().get('charting.chart.rangeStartAngle');
		if (!(this.rangeStartAngle === null || this.rangeStartAngle === undefined)) {
			this.dStartAngle = Number(this.rangeStartAngle);
		} else {
			this.dStartAngle = 30;
		}
		this.rangeArcAngle = this.getContext().get('charting.chart.rangeArcAngle');
		if (!(this.rangeArcAngle === null || this.rangeArcAngle === undefined)) {
			this.dDiffAngle = Number(this.rangeArcAngle);
			this.dFinishAngle = this.dStartAngle + this.dDiffAngle;
		} else {
			this.dFinishAngle = 330;
			this.dDiffAngle = this.dFinishAngle - this.dStartAngle;
		}
		this.arcStart = Number(this.dStartAngle) / 180 * Math.PI;
		this.arcDiff = Number(this.dDiffAngle) / 180 * Math.PI;
		this.arcFinish = this.arcStart + this.arcDiff;

		this.usePercentageRange = this.getContext().get('charting.chart.usePercentageRange') ? this.getContext().get('charting.chart.usePercentageRange') : false;
		this.usePercentage = this.getContext().get('charting.chart.usePercentageValue') ? this.getContext().get('charting.chart.usePercentageValue') : false;
		this.valueStyle = this.getContext().get('charting.chart.valueStyle');
		if (this.valueStyle === null || this.valueStyle === undefined) {
			this.valueStyle = 'font-size :' + Math.max(Math.round(Math.min(this.width, this.height)/8)-2, 17).toString() + 'px;font-weight : bold;font-family : "Helvetica Neue", Arial; fill : #686868 ; color : #686868';
		}
		this.labelStyle = this.getContext().get('charting.chart.labelStyle');
		if (this.labelStyle === null || this.labelStyle === undefined) {
			this.labelStyle = "font-size : 14px; font-family : Helvetica, Arial; color : #686868; fill : #686868; font-weight : normal";
		}
	},

	renderResults : function(jsonRsp) {
		var data = SOLN.parseResults(jsonRsp);
		// No search results
		if(data.length === 0){
			var html = SOLN.replaceVariables('<p class="resultStatusMessage empty_results">No results found, sad face :( <span class="resultStatusHelp"><a href="#" onclick="Splunk.window.openJobInspector(\'$search.sid$\');return false;" class="resultStatusHelpLink">Inspect ...</a></span></p><p style="display:none;">sad face :(</p>', this.getContext());
			this.$container.html(html);
			return;
		}
		// Note gauge removes field from row if undefined is specified in the result, For example
		// | stats count|  eval test = round(0/0, 2) | gauge test 0 5 90 100  return 4 fields instead of 5
		if (this.gaugeType === 'noelGauge' && Object.keys(data[0]).length !== this.thresholdFieldsLength + 1) {
			// No true X value need to set
			this.noData = true;
		} else {
			this.noData = false;
		}
		//Set the freshness to true to indicate this data is just rendered
		// Hold to pushContext to the children
		this.freshness = true;

		// Hidden chart values
		this.initializeChartFormatterVar();

		//Get thresholdFields either from param or search. If param is not defined then value is taken from search
		if (this.getParam("thresholdFields")) {
			var context = this.getContext();
			this.thresholdFields = SOLN.replaceVariables(this.getParam("thresholdFields"), context).split(",");
		} else {
			var row = data[0];
			var fields = Object.keys(row);
			var re = new RegExp("^y(\\d\\d?)$", "");
			this.thresholdFields = [];
			for (var ii = 0; ii < fields.length; ii++) {
				var match = re.exec(fields[ii]);
				if (match) {
					this.thresholdFields[match[1] - 1] = match[0];
				}
			}
		}

		if (this.thresholdFields.length <= 0) {
			this.logger.error(this.moduleType, "ThresholdFields are not defined.");
		}
		// get Max field name
		if (!this.maxField) {
			var row1 = data[0];
			var max = 0;
			this.maxField = this.thresholdFields[0];
			for (var iii = 0; iii < this.thresholdFields.length; iii++) {
				if (max < row1[this.thresholdFields[iii]]) {
					max = row1[this.thresholdFields[iii]];
					this.maxField = this.thresholdFields[iii];
				}
			}
		}

		//Set up the data to be bound to svg
		var valList = [];
		for (var i = 0; i < data.length; i++) {
			var rowData = data[i];
			var tmpList = [];
			for (var jj = 0; jj < this.thresholdFields.length; jj++) {
				tmpList.push(rowData[this.thresholdFields[jj]]);
			}

			// over write ranges value
			if (this.rangeValues !== null || this.rangeValues !== undefined) {
				this.rangeValues = JSON.parse(this.rangeValues);
				for (var kk = 0; kk < this.rangeValues; kk++) {
					tmpList[kk] = this.rangeValues[kk];
				}
			}

			var d = {
				fillVal : Number(rowData[this.valueField]),
				thresholdList : tmpList,
				splRow : rowData,
				totalVal : Number(rowData[this.maxField])
			};
			d.fillGaugeVal = this.getFillVal(d);
			// Height and width of container
			d.width = this.width;
			d.height = this.height;
			valList.push(d);
		}

		// colors
		if (this.chartColors) {
			// charting.gaugeColors string is bounded with [colorx, colory], so remove [ ] from string. Also replace oX to # so we get d3 compatible string
			var colorString = this.chartColors.replace(/\]$/g, '').replace(/^\[/g, '').replace(/0x/g, '#');
			this.colors = d3.scale.ordinal().domain(d3.range(this.thresholdFields.length + 1)).range(colorString.split(','));
		} else if (this.gaugeType === 'smileyGauge' && this.getParam('colors')) {
			// override if colors param is passed for smiley gauge
			this.colors = d3.scale.ordinal().domain(d3.range(this.thresholdFields.length + 1)).range(this.getParam('colors').split(','));
		} else {
			this.colors = d3.scale.category20();
		}

		// Utility function
		var colors = this.colors;
		this.getColorScale = function(d) {
			var index;
			for ( index = 0; index < d.thresholdList.length - 1; index++) {
				if (Number(d.fillVal) < Number(d.thresholdList[index + 1])) {
					break;
				}
			}
			return colors(index);
		};

		if (this.gaugeType === 'noelGauge') {
			this.createNoelGauge(valList);
		} else if (this.gaugeType === 'smileyGauge') {
			this.createSmileyGauge(valList);
		} else {
			console.log("Not supported gauge type..");
		}

		// Done with results
		this.gettingResults = false;
	},

	enableResizable : function() {
		this.$container.resizable({
			autoHide : true,
			overflow : "auto", // fix for safari
			helper : "ui-resizable-helper",
			handles : "s",
			stop : this.onResizeStop.bind(this)
		});
		this.$container.mouseup(function(event) {
			$(this).width('100%');
		});
	},

	onResizeStop : function(event, ui) {
		this.$container.height(ui.size.height);
		console.log("Height " + ui.size.height + " Width:" + ui.size.width);
		//resizeNoelGauge(ui.size.height, this.width);
		this.$container.resize();
		// fire resize event
	},

	resizeNoelGauge : function(curHeight, curWidth) {
		if (this.svg === null || this.svg === undefined) {
			// Gauge is not yet initialized
			console.log("Gauge is not yet initialized ...");
			return;
		}
		// reset SVG element height or width
		this.svg.attr("height", curHeight);
		this.svg.attr("width", curWidth);
		this.vis.attr("transform", "translate(" + curWidth / 2 + "," + curHeight / 2 + ") rotate(180 0 0)");
		var emptyArc = this.arc;
		var fillArc = this.arcFill;

		// tween functions
		function fillArcTween(b) {
			return function(a) {
				var i = d3.interpolate(a, b);
				var keys = Object.keys(b);
				for (var keyIndex=0; keyIndex < keys.length ; keyIndex++) {
					a[keys[keyIndex]] = b[keys[keyIndex]];
				}
				return function(t) {
					return fillArc(i(t));
				};
			};
		}

		function emptyArcTween(b) {
			return function(a) {
				var i = d3.interpolate(a, b);
				var keys = Object.keys(b);
				for (var keyIndex=0; keyIndex < keys.length ; keyIndex++) {
					a[keys[keyIndex]] = b[keys[keyIndex]];
				}
				return function(t) {
					return emptyArc(i(t));
				};
			};
		}

		// Empty arc path updates
		this.emptyClipPath.selectAll("path").transition().attrTween("d", emptyArcTween({
			width : curWidth,
			height : curHeight
		}));
		this.vis.selectAll("path#arcEmpty").transition().attrTween("d", emptyArcTween({
			width : curWidth,
			height : curHeight
		}));
		// Fill arc updates
		this.colorClipPath.selectAll("path").transition().attrTween("d", fillArcTween({
			width : curWidth,
			height : curHeight
		}));
		this.vis.selectAll("path#arcFill").transition().attrTween("d", fillArcTween({
			width : curWidth,
			height : curHeight
		}));

		// text update
		if (Splunk.util.normalizeBoolean(this.showValue)) {
			this.vis.selectAll("text#gauge_center_text").attr('dy', function(d) {
				return Math.max(Math.round(Math.min(curWidth, curHeight)/8)-2, 17) / 2;
			}).attr('dx', function(d) {
				return (-1 * Math.min(d3.select(this).node().getComputedTextLength(), (Math.min(curWidth, curHeight) / 3 - 0.1 * Math.min(curWidth, curHeight)) * 2) / 2);
			}).attr("transform", "rotate(-180 0 0)");
		}

		// label update
		if (Splunk.util.normalizeBoolean(this.showLabels)) {
			this.vis.selectAll("text#gauge_under_text").attr("dx", function(d) {
				return (-1 * Math.min(d3.select(this).node().getComputedTextLength(), Math.min(curWidth, curHeight)) / 2);
			}).attr("dy", function(d) {
				return Math.min(curWidth, curHeight) / 3 + 20;
			}).attr("transform", "rotate(-180 0 0)");
		}

		// ticks updates
		if (Splunk.util.normalizeBoolean(this.showTicks)) {
			for (var i = 0; i < this.thresholdFields.length; i++) {
				if (this.vis.selectAll("path#sticks_path_" + i) !== null && this.vis.selectAll("path#sticks_path_" + i) !== undefined &&
				// check if return select array actual has value or not (replace this if you find a better way)
				this.vis.selectAll("path#sticks_path_" + i).length > 0 && this.vis.selectAll("path#sticks_path_"+i)[0].length > 0) {
					var data = this.vis.selectAll("path#sticks_path_"+i).data()[0];
					var thresholdList = data && data.thresholdList;
					var newLineCords = [Math.min(curWidth, curHeight) / 3 - 0.1 * Math.min(curWidth, curHeight), Math.min(curWidth, curHeight) / 3];
					// remove line
					this.vis.selectAll("path#sticks_path_" + i).remove();
					// redraw line
					this.vis.append("path").attr("id", "sticks_path_" + i).attr("transform", "rotate(-180 0 0) rotate(" + Math.min(this.dStartAngle + (this.dDiffAngle * Number(thresholdList[i])), this.dFinishAngle) + " 0 0)").attr("stroke", this.getThresholdColor(thresholdList, thresholdList[i])).attr("stroke-width", '2').attr('d', this.svgline(newLineCords));
				}
			}
		}
	},

	createNoelGauge : function(valList) {
		var mod_selector = "#" + this.moduleId;
		var modname = this.moduleId;

		// Copy width and height for D3
		var tempWidth = this.width;
		var tempHeight = this.height;

		// Create empty arc
		this.arc = d3.svg.arc().innerRadius(function(d) {
			return Math.min(d.width, d.height) / 3 - 0.1 * Math.min(d.width, d.height);
		}).outerRadius(function(d) {
			return Math.min(d.width, d.height) / 3;
		}).startAngle(this.arcStart).endAngle(this.arcFinish);

		// Creating SVG element
		this.svg = d3.select('#' + this.moduleId).append("svg").attr("id", (this.moduleId + "_stage")).attr("width", this.width).attr("height", this.height);

		// Create filters
		var defs = this.svg.append("defs");
		if (Splunk.util.normalizeBoolean(this.gaugeStyle)) {
			defs.append('filter').attr("id", "softfill_" + modname).append('feGaussianBlur').attr('stdDeviation', "6");
			defs.append('filter').attr("id", "softfillinner_" + modname).append('feGaussianBlur').attr('stdDeviation', "3");
			// Gauge Drop Shadow Filter
			var gaugeDropShadowFilter = defs.append('filter').attr("id", "GaugeDropShadow_" + modname);
			gaugeDropShadowFilter.append('feGaussianBlur').attr('stdDeviation', "1").attr('in', "SourceAlpha");
			gaugeDropShadowFilter.append('feOffset').attr('result', "offsetblur").attr('dx', '0').attr('dy', '0');
			gaugeDropShadowFilter.append('feflood').attr('flood-opacity', '0.5');
			gaugeDropShadowFilter.append('feComposite').attr('in2', 'offsetblur').attr('operator', 'in');
			var feMerge = gaugeDropShadowFilter.append('feMerge');
			feMerge.append('feMergeNode');
			feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
			// Gauge Text Drop Shadow Filter
			var gaugeTextDropShadowFilter = defs.append('filter').attr("id", "GaugeTextDropShadow_" + modname);
			gaugeTextDropShadowFilter.append('feGaussianBlur').attr('stdDeviation', "2").attr('in', "SourceAlpha");
			gaugeTextDropShadowFilter.append('feOffset').attr('result', "offsetblur").attr('dx', '0').attr('dy', '0');
			gaugeTextDropShadowFilter.append('feflood').attr('flood-opacity', '0.3');
			gaugeTextDropShadowFilter.append('feComposite').attr('in2', 'offsetblur').attr('operator', 'in');
			var textFeMerge = gaugeTextDropShadowFilter.append('feMerge');
			textFeMerge.append('feMergeNode');
			textFeMerge.append('feMergeNode').attr('in', 'SourceGraphic');
		}

		// Clippath
		this.emptyClipPath = defs.selectAll("clipPath").data(valList).enter().append("clipPath").attr("id", function(d, ii) {
			return "emptyinnershadow_" + modname + ii;
		});
		this.emptyClipPath.append("path").attr("d", this.arc);

		// Enter
		this.vis = this.svg.selectAll('g').data(valList);
		var tempVis = this.vis.enter().append('g');

		//Update section
		tempVis.attr("cursor", "pointer").on("click", this.onRowClick.bind(this));
		tempVis.attr("id", function(d, ii) {
			return (modname + "_stage" + "_datagroup" + ii);
		}).attr("transform", "translate(" + this.width / 2 + "," + this.height / 2 + ") rotate(180 0 0)");

		// Create empty gauge
		tempVis.append("path").attr("id", "arcEmpty").attr("d", this.arc).attr("fill", '#FFFFFF').attr("stroke", '#CDCDCD').attr('stroke-width', 1).attr("filter", 'url(#GaugeDropShadow_' + modname + ')');

		tempVis.append("path").attr("id", "arcEmpty").attr("d", this.arc).attr("fill", '#FFFFFF').attr("stroke", '#CDCDCD').attr('stroke-width', 8).attr("filter", 'url(#softfill_' + modname + ')').attr('clip-path', function(d, ii) {
			return 'url(#emptyinnershadow_' + modname + ii + ')';
		});

		// For d3
		var getColor = this.getColorScale;

		this.arcFill = d3.svg.arc().innerRadius(function(d) {
			return Math.min(d.width, d.height) / 3 - 0.1 * Math.min(d.width, d.height);
		}).outerRadius(function(d) {
			return Math.min(d.width, d.height) / 3;
		}).startAngle(this.arcStart).endAngle(function(d) {
			return d.fillGaugeVal;
		});

		// For copy variable for d3
		var drawFillArc = this.arcFill;

		// Clip path
		this.colorClipPath = defs.selectAll("clipPath#colorinnershadow").data(valList).enter().append("clipPath").attr("id", function(d, ii) {
			return "colorinnershadow_" + modname + ii;
		});
		this.colorClipPath.append("path").attr("d", function(d) {
			return drawFillArc(d);
		});

		// Draw Fill draw
		tempVis.append("path").attr("id", "arcFill").attr("d", function(d) {
			return drawFillArc(d);
		}).attr("fill", function(d) {
			return getColor(d);
		}).attr("stroke", '#CDCDCD').attr('stroke-width', 1);

		tempVis.append("path").attr("id", "arcFill").attr("d", function(d) {
			return drawFillArc(d);
		}).attr("fill", function(d) {
			return getColor(d);
		}).attr("stroke", "black").attr('stroke-width', 3).attr("filter", 'url(#softfillinner_' + modname + ')').attr('clip-path', function(d, ii) {
			return 'url(#colorinnershadow_' + modname + ii + ')';
		});

		var isPercentage = this.usePercentage;
		var perCentText = "%";
		var noData = this.noData;
		// Show gauge value if showValue flag is set
		if (Splunk.util.normalizeBoolean(this.showValue)) {
			tempVis.append("text").attr("id", "gauge_center_text").attr('style', this.valueStyle).text(function(d) {
				if(noData) {
					// No data
					return "No Data";
				} else {
					if (isPercentage) {
						return SOLN.roundNumber(Number(d.fillVal) * 100) + perCentText;
					} else {
						return SOLN.roundNumber(Number(d.fillVal));
					}
				}
			}).attr('dy', function(d) {
				return Math.max(Math.round(Math.min(d.width, d.height)/8)-2, 17) / 2;
			}).attr('dx', function(d) {
				return (-1 * Math.min(d3.select(this).node().getComputedTextLength(), (Math.min(d.width, d.height) / 3 - 0.1 * Math.min(d.width, d.height)) * 2) / 2);
			}).attr("transform", "rotate(-180 0 0)");
		}

		// show labels only when showLabels is set
		if (Splunk.util.normalizeBoolean(this.showLabels)) {
			var label = this.displayField ? this.displayField : "FillValue";
			var style = this.labelStyle;
			tempVis.append("text").attr("id", "gauge_under_text").attr("style", style).text(label).attr("dx", function(d) {
				return (-1 * Math.min(d3.select(this).node().getComputedTextLength(), Math.min(d.width, d.height)) / 2);
			}).attr("dy", function(d) {
				return Math.min(d.width, d.height) / 3 + 20;
			}).attr("transform", "rotate(-180 0 0)");
		}

		// show ticks
		if (Splunk.util.normalizeBoolean(this.showTicks)) {
			var colors = this.colors;
			this.getThresholdColor = function(tList, value) {
				var index;
				for ( index = 0; index < tList.length; index++) {
					if (Number(value) === Number(tList[index])) {
						break;
					}
				}
				return colors(index);
			};
			var startAngle = this.dStartAngle;
			var endAngle = this.dFinishAngle;
			var diffAngle = this.dDiffAngle;
			this.svgline = d3.svg.line().x(function(d) {
				return 0;
			}).y(function(d) {
				return d;
			}).interpolate("basis");
			var line = this.svgline;
			var tempGetThresholdColor = this.getThresholdColor;
			var drawLines = function(d) {
				var rad = Math.min(d.width, d.height) / 3;
				// Width of circle is 10% of rad
				var lineCords = [rad - 0.1 * Math.min(d.width, d.height), rad];
				for (var i = 0; i < d.thresholdList.length; i++) {
					// Number(d.thresholdList[i]) === Number(d.fillVal) && i === 0 is special condition for empty arc, we need to show all levels
					if (!(Number(d.thresholdList[i]) === Number(d.fillVal) && i === 0) && (Number(d.thresholdList[i]) <= Number(d.fillVal))) {
						continue;
					}
					d3.select(this).append("path").attr("id", "sticks_path_" + i).attr("transform", "rotate(-180 0 0) rotate(" + Math.min(startAngle + (diffAngle * Number(d.thresholdList[i])), endAngle) + " 0 0)").attr("stroke", tempGetThresholdColor(d.thresholdList, d.thresholdList[i])).attr("stroke-width", '2').attr('d', line(lineCords));
				}
			};
			tempVis.each(drawLines);
		}

		this.vis.exit().remove();
	},

	getFillVal : function(d) {
		if (Splunk.util.normalizeBoolean(this.usePercentageRange)) {
			return Math.min(this.arcStart + (this.arcDiff * Number(d.fillVal) / 100), this.arcFinish);
		} else {
			return Math.min(this.arcStart + (this.arcDiff * Number(d.fillVal)), this.arcFinish);
		}
	},

	createSmileyGauge : function(valList) {
		/** Note : This code is copied from Smiley Gauge **/
		var getColor = this.getColorScale;

		//Time for some d3ngineering...
		var margin = {
			top : 20,
			right : 20,
			bottom : 20,
			left : 20
		};
		var smileRadius = 190 / 2;
		var width = margin.left + margin.right + smileRadius * 2;
		var fontSize = 14;
		var height = margin.top + margin.bottom + 2 * smileRadius + fontSize;
		var mod_selector = "#" + this.moduleId;
		var modname = this.moduleId;

		var vis = d3.select(mod_selector).append("svg").attr("id", (this.moduleId + "_stage")).attr("width", width).attr("height", height).append("g").attr("id", (this.moduleId + "_stage" + "_datagroup")).attr("transform", "translate(" + margin.left + "," + margin.top + ")");

		//Make the filters unashamedly stolen from brian.
		var defs = d3.select(mod_selector).select("svg").append("defs");
		defs.append('filter').attr("id", "softfill_" + modname).append('feGaussianBlur').attr('stdDeviation', "6");
		defs.append('filter').attr("id", "softfillinner_" + modname).append('feGaussianBlur').attr('stdDeviation', "6");

		defs.selectAll("clipPath").data(valList).enter().append("clipPath").attr("id", function(d, ii) {
			return "emptyinnershadowfill_" + modname + ii;
		}).append("circle").attr("r", smileRadius).attr("stroke-width", 2).attr("cx", (smileRadius)).attr("cy", (smileRadius));

		//Make the smiley container g
		var smileG = vis.selectAll("g.smile").data(valList).enter().append("g").attr("class", "row").attr("cursor", "pointer").on("click", this.onRowClick.bind(this));

		//Make the basic face
		var face = smileG.append("circle").attr("r", smileRadius).attr("stroke", "black").attr("stroke-width", 2).attr("fill", function(d) {
			return getColor(d);
		}).attr("cx", smileRadius).attr("cy", smileRadius).attr("filter", "url(#softfillinner_" + modname + ")").attr("clip-path", function(d, ii) {
			return "url(#emptyinnershadowfill_" + modname + ii + ")";
		});

		var eyeSpace = 45;
		var leftEye = smileG.append("ellipse").attr("rx", 7).attr("ry", 20).attr("stroke", "black").attr("fill", "black").attr("cx", (smileRadius - eyeSpace / 2)).attr("cy", smileRadius / 2 + 10);

		var rightEye = smileG.append("ellipse").attr("rx", 7).attr("ry", 20).attr("stroke", "black").attr("fill", "black").attr("cx", (smileRadius + eyeSpace / 2)).attr("cy", smileRadius / 2 + 10);

		//Draw the smile according to the data, in other words turn that frown upside down :)
		//ideally this should be the extents of data, hardcoding it for percent
		var smileScale = d3.scale.linear().domain([valList[0].thresholdList[0], valList[0].thresholdList[1], 1]).range([-1 * smileRadius / 3, 0, smileRadius / 3]);
		var scaledVal = smileScale(valList[0].fillVal);
		var smileCorners = [scaledVal, scaledVal / 1.5, scaledVal / 2, scaledVal / 3, scaledVal / 4, scaledVal / 4, scaledVal / 3, scaledVal / 2, scaledVal / 1.5, scaledVal];
		var smileLength = smileRadius;
		var smileStep = (smileLength) / smileCorners.length;
		var smileLine = d3.svg.line().x(function(d, i) {
			return smileStep * i;
		}).y(function(d) {
			return d;
		}).interpolate("basis");
		var mouth = smileG.append("g").attr("transform", "translate(" + (smileRadius - ((smileLength) / 2) + smileStep / 2) + "," + (smileRadius + smileRadius / 2.5) + ")").attr("class", "mouth");
		var smile = mouth.append("path").attr("d", smileLine(smileCorners)).attr("stroke", "black").attr("stroke-width", 5).attr("fill", "none");

		var dimpleData = [{
			x : 0,
			y : scaledVal
		}, {
			x : (smileLength - smileStep),
			y : scaledVal
		}];
		var dimple = mouth.selectAll("circle.dimple").data(dimpleData).enter().append("circle").attr("r", 6).attr("cx", function(d) {
			return d.x;
		}).attr("cy", function(d) {
			return d.y;
		}).attr("fill", "black");

		//Place Labels
		var label = this.getParam("label") ? this.getParam("label") : "SMILEY!";
		var labelText = smileG.append("svg:text").attr("style", "font-size : 12px; font-family : Helvetica, Arial; color : #686868; fill : #686868;").attr("font-weight", "bold").text(label).attr("dx", function(d) {
			return 0;
		}).attr("dy", 14).attr("class", "chartElement").attr("transform", "translate(" + (0 - 3) + "," + (2 * smileRadius + 5) + ")");

		var valText = smileG.append("svg:text").attr("style", "font-size : 14px; font-family : Helvetica, Arial; color : #686868; fill : #686868;").attr("font-weight", "normal").text((valList[0].fillVal * 100) + "%").attr("dx", function(d) {
			return (-1 * (d3.select(this).node().getComputedTextLength()));
		}).attr("dy", 14).attr("class", "chartElement").attr("transform", "translate(" + (2 * smileRadius) + "," + (2 * smileRadius + 5) + ")");
	},
	//on a click of a row we want to push context with all vars
	onRowClick : function(d) {
		//ew this data has been touched and is now used, so not fresh
		this.freshness = false;
		var context = this.getContext();
		var row = d.splRow;
		var fields = Object.keys(row);
		for (var jj = 0; jj < fields.length; jj++) {
			var field = fields[jj];
			context = SOLN.storeVariable("click", field, row[field], context);
		}
		//push with the explicit context set here by the row click
		this.pushContextToChildren(context);
	},

	getModifiedContext : function() {
		//think about moving all the context logic here instead of opushing an explicit context
		//(prolly only needs to be done if we want to disable the drilldown)
		return this.getContext();
	},

	onBeforeJobDispatched : function(search) {
		search.setMinimumStatusBuckets(1);
		search.setRequiredFields(this.requiredFields);
	},

	pushContextToChildren : function($super, explicitContext) {
		this.withEachDescendant(function(module) {
			module.dispatchAlreadyInProgress = false;
		});
		return $super(explicitContext);
	},

	isReadyForContextPush : function($super) {
		if (!(this.doneUpstream)) {
			return Splunk.Module.DEFER;
		}
		if (this.gettingResults) {
			return Splunk.Module.DEFER;
		}
		if (this.freshness) {
			//If the results were just rendered we stop all context propagation until a user clicks on something
			return Splunk.Module.DEFER;
		}
		return $super();
	},

	resetUI : function() {
	} //Just so splunk stops bitching at me
});
