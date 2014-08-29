Splunk.Module.SOLNAppVarSetter = $.klass(Splunk.Module, {

	initialize : function($super, container) {
		$super(container);
		this.childEnforcement = Splunk.Module.ALWAYS_REQUIRE;
		this.logger = Splunk.Logger.getLogger("SOLNAppVarSetter.js");
		this.messenger = Splunk.Messenger.System.getInstance();
		this.key = this.getParam("key");

		this._allTime = {};
		this._default = {};
		this._minRange = null;
		this._ranges = {};
		this._rt = {};
		this._setRanges();
	},

	/*
	 * receive a new context and act upon it
	 * if the current time range is real time, use this._rt
	 * otherwise, we will need to call the module controller to times
	 * @return undefined
	 */
	getModifiedContext : function() {
		var timeRange = this.getContext().get("search").getTimeRange();
		var context;
		if (timeRange.isRealTime()) {
			context = this._setSOLNVar(this._rt);
		} else if (timeRange.isAllTime()) {
			context = this._setSOLNVar(this._allTime);
		} else {
			var duration = this._parseRange(timeRange);
			context = this._varsRouter(duration);
		}
		return context;
	},

	/*
	 * routes to _setSOLNVar based on duration
	 * @param duration {Number} the duration of the search
	 * @return context {Object} the new context
	 */
	_varsRouter : function(duration) {
		if (duration <= this._minRange) {
			return this._setSOLNVar(this._default);
		} else {
			for (first in this._ranges){
				break;
			}
			
			var match = first;
			for (range in this._ranges) {
				if ((+range) >= duration) {
					break;
				}
				match = range;
			}
			return this._setSOLNVar(this._ranges[match]);
		}
	},

	/*
	 * swaps out the current search with either a search string or saved search
	 * @param _search {Object} contains either a 'search' or 'savedsearch' key
	 * @return context {Object} the new context
	 */
	_setSOLNVar : function(_setter) {
		var context = this.getContext();
		var targetsetter = _setter['setter'];
		SOLN.storeVariable(this.key, 'setter', targetsetter, context);
		return context;
	},

	/*
	 * internal function to parse the time range into an absolute duration
	 * @param timeRange {Object} Splunk time range object
	 * @return duration {number} the range between earliest and latest
	 */
	_parseRange : function(timeRange) {
		var earliest = timeRange.getEarliestTimeTerms();
		var latest = timeRange.getLatestTimeTerms();
		if (latest === undefined || latest === null || latest === "") {
			latest = "now";
		}
		var url = Splunk.util.make_url('/util/time/parser?ts=' + encodeURIComponent(earliest) + '&ts=' + encodeURIComponent(latest));
		var Iso = {};
		this.ParseXHR = $.ajax({
			async : false,
			type : 'GET',
			url : url,
			complete : function(data) {
				this.logger.debug('response OK from server');
				Iso['earliest'] = JSON.parse(data.responseText)[earliest].iso;
				Iso['latest'] = JSON.parse(data.responseText)[latest].iso;
			}.bind(this),
			error : function() {
				this.messenger.send('error', 'splunk.search', _('Unable to parse times'));
				this.logger.debug('response ERROR from server');
				return null;
			}.bind(this)
		});
		return parseInt(Splunk.util.getEpochTimeFromISO(Iso['latest']), 10) - parseInt(Splunk.util.getEpochTimeFromISO(Iso['earliest'], 10), 10);
	},

	/*
	 * convert a relative time string to number of seconds
	 * @param relativeTime {String} a relative time value (e.g 1h, 1d, 1w, 1mon)
	 * @return seconds {Integer}
	 */
	_convertToSeconds : function(relativeTime) {
		var _rangeMap = {
			's' : 1,
			'm' : 60,
			'h' : 3600,
			'd' : 86400,
			'w' : 86400 * 7,
			'mon' : 86400 * 28,
			'y' : 86400 * 365
		};
		var regex = /^(\d+)(\w+)/;
		var match = regex.exec(relativeTime);
		var seconds = _rangeMap[match[2]] * parseInt(match[1], 10);
		return seconds;
	},

	/*
	 * tie ranges to searches 
	 * operates on the modules given _params (usually from the view XML
	 * mutables this._default, this._rt, and this._ranges are operated upon
	 */
	_setRanges : function() {
		var rtMissing;
		for (i in this._params['rangeMap'] ) {
			if (i === 'default') {
				if ('setter' in this._params['rangeMap'][i]) {
					this._default = {
						'setter' : this._params['rangeMap'][i]['setter']
					};
				} else {
					this.logger.error('Config error: no default setter set for this module.rangeMap');
					this.messenger.send('error', 'splunk.search', _('Config error: no default setter set for module.rangeMap'));
					return;
				}
			} else if (i === 'rt') {
				if ('setter' in this._params['rangeMap'][i]) {
					this._rt = {
						'setter' : this._params['rangeMap'][i]['setter']
					};
				} else {
					this.logger.warn('Config warning: no real time setter set for this module.rangeMap, using default search');
					rtMissing = true;
				}
			} else {
				var seconds = this._convertToSeconds(i);
				if ((!this._minRange) || (this._minRange && (seconds < this._minRange))) {
					this._minRange = seconds;
				}
				if ('setter' in this._params['rangeMap'][i]) {
					this._ranges[seconds] = {
						'setter' : this._params['rangeMap'][i]['setter']
					};
				} else {
					this.logger.error('Config error: no setter specified for range "' + i + '"');
					this.messenger.send('error', 'splunk.search', _('Config error: no setter specified for range "' + str(i) + '"'));
					return;
				}
			}
		}
		if (rtMissing) {
			this._rt = this._default;
		}
		this._ranges = this._sortObj(this._ranges);
	},

	/*
	 * sort an object
	 * @param o       {Object}  the object to be sorted
	 * @param reverse {Boolean} reverse sort if true
	 * @return sorted {Object}  the sorted object
	 */
	_sortObj : function(o, reverse) {
		var sorted = {};
		var a = [];
		for (key in o) {
			if (o.hasOwnProperty(key)) {
				a.push(key);
			}
		}
		if (!reverse) {
			a.sort(function(a, b) {
				return a - b;
			});
		} else {
			a.sort(function(a, b) {
				return b - a;
			});
		}
		for ( key = 0; key < a.length; key++) {
			sorted[a[key]] = o[a[key]];
			this._allTime = sorted[a[key]];
		}
		return sorted;
	}
});
