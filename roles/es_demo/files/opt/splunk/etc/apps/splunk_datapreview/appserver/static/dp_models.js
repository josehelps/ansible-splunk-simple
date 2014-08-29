//
// Data input preview models
//
// These represent the model objects used to manage the source preview process.
// The organization looks like:
//      Sample
//          |
//          + Settings
//          |
//          + SearchJob
//          |
//          + Metadata
//



Splunk.namespace("Splunk.preview");


//
// Preview sample objects
//


/**
 * Main object that represents a specific set of ingested source data
 */
Splunk.preview.Sample = function(id) {
    this.settings = new Splunk.preview.Settings();
    this.id = id;
    this.searchJob = null;
    this._service = null;
    this.SYSTEM_FIELDS = [
        'punct', 
        'meta',
        'timestamp', 
        'timestartpos',
        'timeendpos',
        'date_second', 
        'date_minute', 
        'date_hour', 
        'date_mday', 
        'date_wday', 
        'date_month', 
        'date_year', 
        'date_zone',
        'linecount',
        'host',
        'source',
        'sourcetype'
        ];
};

Splunk.preview.Sample.prototype = {

    DEFAULT_EVENT_COUNT: 200,

    initSearchJob: function() {
        if (!this.searchJob) {
            // TODO: figure out svc scoping
            this.searchJob = new splunk.service.Job(this.id, null, null, svc);
        }
        return this.searchJob;
    },



    /**
     * Returns a dict of metadata about the current sample
     *
     * Data returned:
     *  timeline buckets
     *  total number of events
     *  min/max/avg linecount per event
     *
     */
    fetchMetadata: function() {
        if (!this.id) {
            throw new Error('No ID found, cannot fetch job');
        }
        
        this.initSearchJob();

        return $.when(
                this.searchJob.fetchTimeline(),
                this.searchJob.fetchShallowResults({
                    search: 'chart count by linecount | eventstats sum(count) as total | eval perc = count / total',
                    count: 0
                })

            ).pipe($.proxy(function(timeline, stats) {

                // normalize times
                var buckets = timeline.buckets;
                var i,L;
                for (i=0,L=buckets.length; i<L; i++) {
                    buckets[i].earliest_time = str2datetime(buckets[i].earliest_time);
                    buckets[i].latest_time = str2datetime(buckets[i].latest_time);
                }

                // clean up the data and composite into a single data structure
                output = {
                    buckets: buckets,
                    stats: {
                        linecount_table: stats.data,
                        count: (stats.data[0] ? stats.data[0][3] : -1)
                    },
                    file: {
                        size: parseInt(this.searchJob.get('dataPreviewBytesInSource') || 0, 10),
                        read: parseInt(this.searchJob.get('dataPreviewBytesRead') || 0, 10),
                        isCompressed: !!(parseInt(this.searchJob.get('dataPreviewRequiredDecompress'), 10)),
                        isComplete: !!(parseInt(this.searchJob.get('dataPreviewReachedEof'), 10))
                    }
                };

                return output;
            }, this));

    },


    fetchEvents: function(offset, count) {
        var that = this;
        if (!this.id) {
            throw new Error('No ID found, cannot fetch job');
        }

        offset = offset || 0;
        count = count || this.DEFAULT_EVENT_COUNT;

        this.initSearchJob();

        var handleData = function(results) {
            var events = [];

            var i,L,event;
            for (i=0,L=results.data.length; i<L; i++) {
                event = new Splunk.preview.SampleEvent();
                event.fromDataset(results.fieldList, results.data[i]);
                events.push(event);
            }

            return {'events': events,
                    'fields': that.getExtractedFieldList(results.fieldList)};
        };

        return this.searchJob.fetchFullResults({
                offset: offset,
                count: count,
                time_format: '%s.%Q',
                max_lines: 100,
                truncation_mode: 'truncate'
                })
            .pipe(handleData);
    },
    
    getExtractedFieldList: function(fieldList) {
        return $.grep(fieldList, function(key,i) {
            // only pick keys that are not system fields
            return key.indexOf('_') != 0 && this.SYSTEM_FIELDS.indexOf(key) == -1;
            // TODO: need to handle case when field is an array (duplicating name)
        }.bind(this));
    }

};


/**
 * Define the splunk path for objects
 */
Splunk.preview.Sample.entry_path = '/indexing/preview';


/**
 * Creates a preview sample from a file that exists on the server
 *
 * @param {splunk.service.Service} svc The working instance of a Splunk
 *          service connection.
 * @param {String} server_filepath The filepath of the file to preview
 * @param {Splunk.preview.Settings} settings The set of props that are to be
 *          used in processing the preview.
 *
 */
Splunk.preview.createSample = function(server_filepath, settings) {

    var payload = (settings ? settings.toQueryParams() : {});
    payload['input.path'] = server_filepath;

    // first send the path over to the server to get a SID
    var url = svc.buildUri(Splunk.preview.Sample.entry_path);
    var addSample = svc.request(url, {
        type: 'POST',
        data: payload
    });

    // get SID and get the sample properties
    var handleCreate = $.proxy(function(odata) {
        if (!odata.messages || odata.messages.length == 0) {
            var errorMessage = _('splunkd did not pass a valid search ID');
            var dfd = new $.Deferred();
            dfd.reject({
                statusCode: 500,
                errorThrown: errorMessage,
                messages: [{text: errorMessage}]
            });
            return dfd;
        }
        return svc.fetchEntry(Splunk.preview.Sample.entry_path, odata.messages[0].text);
    }, this);


    
    // finally get sample details and create Sample() object
    // note the closure to 'settings' here
    var handleDetails = function(entry) {

        var output = new Splunk.preview.Sample(entry.__name);
        output.settings = settings;
        
        // assign server-set
        output.settings.setBase(entry);

        return output;
    };

    return addSample
            .pipe(handleCreate)
            .pipe(handleDetails);
            
};


/**
 * quick and dirty object factory; to be replaced by a proper collection
 * manager in next iteration
 */
Splunk.preview.fetchSampleById = function(svc, id) {
    var fetchSample = svc.fetchEntry(Splunk.preview.Sample.entry_path, id);
    return fetchSample.pipe(Splunk.preview._handleDetails);
};


/**
 * Internal. Converts the generic entry to Sample()
 */
Splunk.preview._handleDetails = function(entry) {

    var output = new Splunk.preview.Sample(entry.__name);

    // assign server-set
    output.settings.setBase(entry);
    
    return output;
};


/**
 * Get list of all currently available samples
 */
Splunk.preview.fetchSamples = function(svc) {
    throw new Error('Not implemented');
};


/**
 * Represents a single parsed event from the preview system
 *
 */
Splunk.preview.SampleEvent = function() {
    this._fields = {};
};


Splunk.preview.SampleEvent.prototype = {

    /**
     * Populates the event with standard info from a Splunk search result.
     *
     * @param fieldList Ordered array of field names that serve as the offset
     *                  for the event array parameter.
     *
     * @param event The deep event data structure coming back from the search
     *              result set. This encodes multi-value fields and tags
     *              (though there are no fields here).
     */
    fromDataset: function(fieldList, event) {
        var i,L;
        for (i=0,L=fieldList.length; i<L; i++) {
            this._fields[fieldList[i]] = event[i];
        }
    },


    /**
     * Returns a field value from the event. Return type is either a simple
     * string or a deep search result data structure.
     *
     * @param field Name of the field to retrieve.
     *              Supported keys are:
     *                  raw
     *                  time
     *                  host
     *                  source
     *                  sourcetype
     *                  message_codes
     *                  message_strings
     *                  time_extract_start
     *                  time_extract_end
     */
    get: function(field) {
        var mappedField = Splunk.preview.SampleEvent.fieldMapping[field];

        // if we just need to retrieve the text value, then grab the first
        // value from the multi-value field
        if (mappedField) {
            var fullField = this._fields[mappedField];
            if (fullField && fullField.length) {
                return fullField[0].value;
            } else {
                return null;
            }

        // otherwise, what we want involves a bit of munging
        } else {
            switch (field) {
                
                // the raw field has segmentation encoded, so we flatten
                case 'raw':
                    if (this._fields._raw) {
                        return this._fields._raw[0].value.toString();
                    } else {
                        return '';
                    }

                case 'time':
                    if (this._fields._time) {
                        var epoch = this._fields._time[0].value;
                        return str2datetime(epoch);
                    }
                    return null;

                case 'time_extract_start':
                    if (this._fields._timestartpos) {
                        return parseInt(this._fields._timestartpos[0].value, 10);
                    }
                    return null;

                case 'time_extract_end':
                    if (this._fields._timelen && this._fields._timestartpos) {
                        return parseInt(this._fields._timelen[0].value, 10)
                            + this.get('time_extract_start');
                    }
                    return null;
    
                case 'messages':
                    output = [];
                    
                    // get server messages
                    if (this._fields._message_codes) {
                        var i,L;
                        for (i=0,L=this._fields._message_codes.length; i<L; i++) {
                            output.push({
                                code: this._fields._message_codes[i].value,
                                text: this._fields._message_texts[i].value
                            });
                        }
                    }

                    return output;

                default:
                    break;

            }
        }
    }
    
};


/**
 * Defines the list of normalized field names that map one-to-one on the base
 * search result event field list. Format is:
 *      <FRIENDLY_FIELD_NAME>: <API_FIELD_NAME>
 */
Splunk.preview.SampleEvent.fieldMapping = {
    'host': 'host',
    'source': 'source',
    'sourcetype': 'sourcetype'
};



//
// Model definition of the preview settings
//


/**
 * Object for holding the various indexing options
 */
Splunk.preview.Settings = function() {
    this._props = {};
    this._baseprops_explicit =  {};
    this._baseprops_inherited = {};
    this._baseprops_preset = {};

    this.setDefaults();
};

Splunk.preview.Settings.prototype = {

    /**
     * Define prefix for all props.conf settings that are passed into the
     * preview REST handler
     */
    FORM_KEY_PREFIX: 'props.',

    setDefaults: function() {
        this._props.NO_BINARY_CHECK = 1;
    },

    /**
     * Internal method used to set the base prop value, as returned by the
     * server.
     */
    setBase: function(entry) {
        this._baseprops_explicit = {};
        this._baseprops_inherited = {};
        this._baseprops_preset = {};
        
        var k;
        for (k in entry.explicit) {
            this._baseprops_explicit[k] = entry.explicit[k].value;
        }

        for (k in entry.inherited) {

            // pull out the keys that are set by any auto-detected sourcetype
            if (entry.inherited[k].stanza == this._baseprops_explicit['PREFERRED_SOURCETYPE']) {
                this._baseprops_preset[k] = entry.inherited[k].value;
            } else if (entry.inherited[k].value !== '' && entry.inherited[k].value !== null) {
                this._baseprops_inherited[k] = entry.inherited[k].value;
            }
        }
    },
    
    /**
     * Sets a specific prop.conf setting.
     *
     * @param {String} key The props key value. Valid values are defiend in
     *                      Splunk.preview.Settings.properties dict.
     *
     * @param {Object} value The value for the key.
     *
     */
    set: function(key, value) {
        if (value == null) {
            delete this._props[key];
        } else {
            this._props[key] = value;
        }
    },


    /**
     * Returns a props.conf setting.
     *
     */
    get: function(key) {
        
        // get either user set or default value;
        var val = this._props[key];
        if (val === undefined) {
            val = this._baseprops_explicit[key];
            if (val === undefined) {
                val = this._baseprops_preset[key];
                if (val === undefined) {
                    val = this._baseprops_inherited[key];
                }
            }
        }

        if (key in Splunk.preview.Settings.properties) {
            switch (Splunk.preview.Settings.properties[key]) {
                case 'bool':
                    return Splunk.util.normalizeBoolean(val);
                case 'int':
                    return isNaN(val) ? '' : parseInt(val, 10);
                default:
                    break;
            }
        }
        return val;
    },

    clear: function() {
        var sourcetype = this._props['sourcetype'];
        this._props = {};
        this._props['sourcetype'] = sourcetype;
        this.setDefaults();
    },
    
    /**
     * Returns a hash of settings that is ready to be passed to the preview 
     * endpoint.
     */
    toQueryParams: function() {
        var output = {};
        var k;
        for (k in this._props) {
            output[this.FORM_KEY_PREFIX + k] = this._props[k];
        }
        return output;
    },

    /**
     * Returns a hash of settings that is ready to be committed to a sourcetype
     * type: [explicit, inhertied, merged]
     */
    toSourcetypeSettings: function(type) {

        if (type === undefined || !type.length) {
            type = 'merged';
        }
        
        var settings;
        if (type == 'explicit') {
            settings = $.extend({}, this._baseprops_explicit);
        } else if (type == 'inherited') {
            settings = $.extend({}, this._baseprops_inherited);
        } else if (type == 'preset') {
            settings = $.extend({}, this._baseprops_preset);
        } else if (type == 'merged') {
            settings = $.extend({}, this.baseprops_explicit, this._baseprops_preset, this._props);
        }
        
        // filter blacklisted props
        var k;
        for (k in settings) {
            if (Splunk.preview.Settings.blacklist.indexOf(k) >= 0) {
                delete settings[k];
            }
        }
        
        return settings;
    }
    
 

};

/**
 * List of supported properties
 *
 * TODO: generalize this to support both Sample and Sourcetype
 */
Splunk.preview.Settings.properties = {
    'ANNOTATE_PUNCT': 'bool',
    'AUTO_SOURCETYPE': 'str',
    'BREAK_ONLY_BEFORE': 'str',
    'BREAK_ONLY_BEFORE_DATE': 'bool',
    'CHARSET': 'str',
    'DATETIME_CONFIG': 'str',
    'FIELD_DELIMITER': 'str',
    'FIELD_HEADER_REGEX': 'str',
    'FIELD_QUOTE': 'str',
    'FIELD_NAMES': 'str',
    'HEADER_MODE': 'str',
    'HEADER_FIELD_DELIMITER': 'str',
    'HEADER_FIELD_QUOTE': 'str',
    'HEADER_FIELD_LINE_NUMBER': 'str',
    'INDEXED_EXTRACTIONS': 'str',
    'LEARN_SOURCETYPE': 'bool',
    'LINE_BREAKER': 'str',
    'LINE_BREAKER_LOOKBEHIND': 'int',
    'MAX_DAYS_AGO': 'int',
    'MAX_DAYS_HENCE': 'int',
    'MAX_DIFF_SECS_AGO': 'int',
    'MAX_DIFF_SECS_HENCE': 'int',
    'MAX_EVENTS': 'int',
    'MAX_TIMESTAMP_LOOKAHEAD': 'int',
    'MUST_BREAK_AFTER': 'str',
    'MUST_NOT_BREAK_AFTER': 'str',
    'MUST_NOT_BREAK_BEFORE': 'str',
    'PREAMBLE_REGEX': 'str',
    'TIMESTAMP_FIELDS': 'str',
    'SEGMENTATION': 'str',
    'SEGMENTATION-all': 'str',
    'SEGMENTATION-inner': 'str',
    'SEGMENTATION-outer': 'str',
    'SEGMENTATION-raw': 'str',
    'SEGMENTATION-standard': 'str',
    'SHOULD_LINEMERGE': 'bool',
    'TIME_FORMAT': 'str',
    'TIME_PREFIX': 'str',
    'TRANSFORMS': 'str',
    'TRUNCATE': 'int',
    'TZ': 'str',
    'maxDist': 'int',
    'sourcetype': 'str'
};

Splunk.preview.Settings.blacklist = [
    'sourcetype',
    'PREFERRED_SOURCETYPE'
];

//
// Sourcetype object management
//


Splunk.preview.Sourcetype = function(namespace, owner, props) {
    this._props = {};
    this._baseprops_explicit =  {};
    this._baseprops_inherited = {};
    if (props) {
        var k;
        for (k in props) {
            this.set(k, props[k]);
        }
    }

    this.namespace = namespace || null;
    this.owner = owner || null;
    this.id = null;
};

Splunk.preview.Sourcetype.entry_path = '/saved/sourcetypes';

Splunk.preview.Sourcetype.fetchNames = function() {
    var deferred = svc.fetchCollection('/saved/sourcetypes', null, null, {search: 'pulldown_type=1'});

    var handleList = function(results) {
        return $.map(results, function(item) {
            return item.__name;
        });
    };

    return deferred.pipe(handleList);
};
        
Splunk.preview.Sourcetype.prototype = {

    get: function(key) {
        // get either user set or default value;
        var val = this._props[key];
        if (val === undefined) {
            val = this._baseprops_explicit[key];
            if (val === undefined) {
                val = this._baseprops_inherited[key];
            }
        }

        if (key in Splunk.preview.Settings.properties) {
            switch (Splunk.preview.Settings.properties[key]) {
                case 'bool':
                    return Splunk.util.normalizeBoolean(val);
                case 'int':
                    return parseInt(val, 10);
                default:
                    break;
            }
        }
        return val;
    },

    set: function(key, value) {
        this._props[key] = value;
    },

    setBase: function(entry) {
        this._baseprops_explicit = {};
        this._baseprops_inherited = {};

        var k;
        for (k in entry.explicit) {
            this._baseprops_explicit[k] = entry.explicit[k].value;
        }
        for (k in entry.inherited) {
            this._baseprops_inherited[k] = entry.inherited[k].value;
        }
    },
    
    isNew: function() {
        return !(this.id);
    },

    save: function(new_id) {

        var logger = Splunk.Logger.getLogger("Splunk.Datapreview");

        if (!this.isNew()) {
            logger.error('Updating existing source type not currently supported');
            return false;
        }

        if (!new_id) {
            logger.error('cannot save without a name');
            return false;
        }

        if (!this.namespace || !this.owner) {
            logger.error('cannot save without namespace and owner set');
            return false;
        }

        return svc.createEntry(
                Splunk.preview.Sourcetype.entry_path, 
                new_id, 
                this.namespace, 
                this.owner, 
                this._props)
            .pipe($.proxy(function(new_props) {
                // update model with server response
                if (new_props) {
                    this.setBase(new_props);
                    this.id = new_props.__name;
                }
                return this;
            }, this));
    },

    toJSON: function(use_merged) {
        if (use_merged) {
            return $.extend(true, {}, this._baseprops_explicit, this._props);
        }
        return $.extend(true, {}, this._props);
    }

};
    
/**
 * Parses an epoch-time string into a splunk.i18n.DateTime() object
 * This supports milliseconds.
 */
function str2datetime(timestring) {
    if (typeof timestring === 'undefined') {
        return timestring;
    }
    if (typeof timestring === 'number') {
        timestring = timestring.toString();
    }
    var parts = timestring.split('.');
    var time = new Date(parseInt(parts[0], 10) * 1000);
    time = new DateTime(time);
    if (parts.length > 1) {
        time.microsecond = parseInt(parts[1], 10) * 1000;
    }
    return time;
}
