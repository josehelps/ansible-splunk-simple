define([
    'jquery',
    'underscore',
    'backbone'
], function(
    $,
    _,
    Backbone
) {
    return Backbone.Collection.extend({
        pref_id: 'swimlanes',
        initialize: function(model, options) {
            this.options = options || {};
            this.prefs = this.options.prefs;

            // a count of values by key
            this.values = new Backbone.Model();
            // the aggregated signboard data
            this.data = new Backbone.Model();
            // the clicked event id by lane name
            this.clicked = new Backbone.Model();

            this.dateFormatter = d3.time.format('%a %b %e');
            this.timeFormatter = d3.time.format('%X');
            this.zoneFormatter = d3.time.format('%Z');

            this.onHeaderData = _.debounce(this._onHeaderData, 300);
            this.onBodyData = _.debounce(this._onBodyData, 500);

            this.prefs.on('reset', _.bind(this.onPrefsReset, this));

            this.on('add', _.bind(this.onAdd, this));
            this.on('remove', _.bind(this.onRemove, this));
            this.on('reset', _.bind(this.onReset, this));
        },
        onPrefsReset: function() {
            var pref = this.prefs.getPref(this.pref_id),
                lane_prefs = pref.get('lane_prefs') || {};

            _.each(lane_prefs, function(value, key){
                var clicked = value.clicked || [];
                this.clicked.set(key, clicked, {silent: true}); 
            }, this);
 
            this.onClickedChange = _.debounce(this._onClickedChange, 1000);
            this.clicked.on('change', _.bind(this.onClickedChange, this));
        },
        _onClickedChange: function() {
            var pref = this.prefs.getPref(this.pref_id),
                lane_prefs = pref.get('lane_prefs') || {};

            _.each(lane_prefs, function(val, key) {
                var clicked = this.clicked.get(key) || [];
                lane_prefs[key].clicked = clicked;
            }, this);
             
            pref.save({lane_prefs: lane_prefs}); 
        },
        onAdd: function(model) {
            var meta = model.get('meta'),
                earliest_time = meta.earliest_time,
                latest_time = meta.latest_time,
                count = Number(model.get('count')),
                search = meta.search,
                title = meta.lane_name,
                metadata = this.data.get('meta') || {},
                metacount = metadata.count || 0,
                searches = metadata.searches || [],
                titles = metadata.titles || [];

            this.setClicked(title, meta.id);

            if (!metadata.earliest_time || earliest_time < metadata.earliest_time) {
                metadata.earliest_time = earliest_time;
                metadata.startDate = this.dateFormatter(earliest_time);
                metadata.startTime = this.timeFormatter(earliest_time);
                metadata.timeZone = this.zoneFormatter(earliest_time);
            }

            if (!metadata.latest_time || latest_time > metadata.latest_time) {
                metadata.latest_time = latest_time;
                metadata.endDate = this.dateFormatter(latest_time);
                metadata.endTime = this.timeFormatter(latest_time);
            }

            metadata.count = metacount+count;
 

            metadata.titles = _.union(titles, [title]); 
            if (metadata.titles.length > 1) {
                metadata.title = 'Events';
            } else {
                metadata.title = metadata.titles[0];
            }

            metadata.searches = _.union(searches, [search]);

            this.data.set('meta', metadata);

            // trigger debounced header data ready
            this.onHeaderData();
           
            this.mergeModelAttributes(model);

            // trigger debounced body data ready
            this.onBodyData();
            
        },
        onRemove: function(model) {
            // treat emptying remove like a reset
            if (this.length < 1) {
                this.onReset(this);
                return;
            }
            var meta = model.get('meta'),
                earliest_time = meta.earliest_time,
                latest_time = meta.latest_time,
                count = Number(model.get('count')),
                search = meta.search,
                title = meta.lane_name,
                metadata = this.data.get('meta') || {},
                metacount = metadata.count || 0,
                searches = _.uniq(this.map(
                  function(m) {
                    if (meta.id===m.get('meta').id) {
                        return;
                    }
                    return m.get('meta').search;
                  })
                ),
                titles = _.uniq(this.map(
                  function(m) {
                    if (meta.id===m.get('meta').id) {
                        return;
                    }
                    return m.get('meta').lane_name;
                  })
                );

            this.unsetClicked(title, meta.id);

            if (earliest_time===metadata.earliest_time) {
                var next_earliest_time = this.min(
                    function(m) {
                      if (meta.id===m.get('meta').id) {
                          return;
                      }
                      return m.get('meta').earliest_time;
                    }).get('meta').earliest_time;

                if (earliest_time!==next_earliest_time) {
                    metadata.earliest_time = next_earliest_time;
                    metadata.startDate = this.dateFormatter(next_earliest_time);
                    metadata.startTime = this.timeFormatter(next_earliest_time);
                }
            }

            if (latest_time===metadata.latest_time) {
                var next_latest_time = this.max(
                    function(m) {
                      if (meta.id===m.get('meta').id) {
                          return;
                      }
                      return m.get('meta').latest_time;
                    }).get('meta').latest_time;

                if (latest_time!==next_latest_time) {
                    metadata.latest_time = next_latest_time;
                    metadata.endDate = this.dateFormatter(next_latest_time);
                    metadata.endTime = this.timeFormatter(next_latest_time);
                }
            }

            metadata.count = metacount-count;
            metadata.titles = titles;

            if (metadata.titles.length > 1) {
                metadata.title = 'Events';
            } else {
                metadata.title = metadata.titles[0];
            }

            metadata.searches = searches;
            this.data.set('meta', metadata);

            // trigger debounced header data ready
            this.onHeaderData();
           
            this.pruneModelAttributes(model);

            // trigger debounced body data ready
            this.onBodyData();
        },
        onReset: function(collection) {
            this.data.clear();
            this.values.clear();
            if (collection.length < 1) {
                this._onClearAll();
                return;
            }
            this.resetClicked(collection);
            var earliest_time = collection.min(
                  function(model) {
                    return model.get('meta').earliest_time;
                  }).get('meta').earliest_time,
                latest_time = collection.max(
                  function(model) {
                    return model.get('meta').latest_time;
                  }).get('meta').latest_time,
                startDate = this.dateFormatter(earliest_time),
                startTime = this.timeFormatter(earliest_time),
                endDate = this.dateFormatter(latest_time),
                endTime = this.timeFormatter(latest_time),
                timeZone = this.zoneFormatter(earliest_time),
                count = collection.reduce(
                  function(memo, model) {
                    return memo + Number(model.get('count'));
                  }, 0),
                title = _.uniq(collection.map(
                  function(model) {
                    return model.get('meta').lane_name;
                  })),
                searches = _.uniq(collection.map(
                  function(model) {
                    return model.get('meta').search;
                })),
                keys, titles;
   
            if (title.length > 1) {
                titles = title; 
                title = 'Events';
            }   
    
            this.data.set({
              meta: {
                count: count,
                earliest_time: earliest_time,
                endDate: endDate,
                endTime: endTime,
                latest_time: latest_time,
                searches: searches,
                startDate: startDate,
                startTime: startTime,
                timeZone: timeZone,
                title: title,
                titles: titles
              }
            });

            // trigger header data ready
            this._onHeaderData();

            // delay processing to allow DOM processing
            _.delay(_.bind(function() {
                collection.each(function(model){
                    var meta = model.get('meta');
                    this.mergeModelAttributes(model);
                    this.setClicked(meta.lane_name, meta.id);
                }, this); 
                // trigger body data ready
                this._onBodyData();
            }, this), 150);
        },
        /*
         * prunes one occurance of given values for given
         * keys in the the values model, and returns
         * a boolean if the value still exists
         */
        existsAfterPrune: function(obj, elm, key) {
            var count = obj[elm] || 1,
                exists = false;

            count -= 1;

            if (count< 1) {
                if (obj[elm]) {
                    delete obj[elm];
                }
            } else { 
                obj[elm] = count;
                exists = true;
            }

            this.values.set(key, obj); 
            return exists;
        },
        /*
         * the values model is a hash of keys which yield 
         * hashes of values and counts of their occurence
         */
        incrementValues: function(key, val) {
            var obj = this.values.get(key) || {};

            _.each(val, function(elm) {
                existing = obj[elm] || 0;
                obj[elm] = existing + 1;
            }, this);

            this.values.set(key, obj); 
        },
        /*
         * merges all arbitrary model attributes in 
         * the collection into the aggregate data model
         */
        mergeModelAttributes: function(model) {
            _.each(model.attributes, function(vals, key) {
                if (key==='meta' || key==='_time' || key==='count') {
                    return;
                }
                var existing = this.data.get(key);

                vals = _.flatten([vals]);
 
                // adds these vals to the values model 
                this.incrementValues(key, vals);

                if (existing) {
                    vals = _.union(existing, vals);
                    this.data.set(key, vals);
                } else {
                    this.data.set(key, vals);
                }    
            }, this); 
        },
        /* for each attribute in the model
         * look in the values model under the given key
         * if the value was unique, it can be removed
         */
        pruneModelAttributes: function(model) {
            _.each(model.attributes, function(val, key) {
                if (key==='_time' || key==='meta' || key==='count') {
                    return;
                }
                var obj = this.values.get(key),
                    data = this.data.get(key) || [];

                if (!obj) {
                    return;
                }
                
                _.each(val, function(elm) {
                    if (!this.existsAfterPrune(obj, elm, key)) {
                        data = _.without(data, elm);
                    }
                }, this);

                this.data.set({key: data});
            }, this);
        },
        _onClearAll: function() {
            this.data.trigger('clearAll');
            this.clicked.clear();
        },
        _onHeaderData: function() {
            this.data.trigger('ready:headerData', this.data);
        },
        _onBodyData: function() {
            this.data.trigger('ready:bodyData', this.data);
        },
        resetClicked: function(collection) {
            this.clicked.clear();
            collection.forEach(function(model) {
                var meta = model.get('meta'),
                    lane_name = meta.lane_name,
                    id = meta.id, 
                    clicked = this.clicked.get(lane_name) || [];
                clicked.push(id);
                this.clicked.set(lane_name, clicked);
            }, this);
        },
        setClicked: function(lane_name, id) {
            var clicked = this.clicked.get(lane_name) || []; 
            clicked = _.union(clicked, [id]);
            this.clicked.set(lane_name, clicked);
        },
        unsetClicked: function(lane_name, id) {
            var clicked = this.clicked.get(lane_name) || []; 
            clicked = _.without(clicked, id);
            this.clicked.set(lane_name, clicked);
        }
    });
});
