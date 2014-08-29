define([
    'jquery',
    'backbone',
    'underscore',
    'd3',
    'splunkjs/mvc/tokenutils',
    'splunkjs/mvc/searchmanager'
],
function(
    $,
    Backbone,
    _,
    d3,
    tokenUtils,
    SearchManager
){
    return Backbone.Model.extend({
        initialize: function(options){
            this.managers = options.managers;
            this.timeRange = options.timeRange;
            this.swimlanes = options.swimlanes;

            // constraint changes happen all at once on page load
            this.onConstraintChange = _.debounce(this._onConstraintChange, 1200);
            this.onSelectedChange = _.debounce(this._onSwimlaneChange, 200);

            this.swimlanes.on('change:constraints', _.bind(this.onConstraintChange, this));
        },
        _onConstraintChange: function(){
            this.timeRange.on('change:outerTimeRange', _.bind(this.onSelectedChange, this));
            this.swimlanes.on('change:selected', _.bind(this.onSelectedChange, this));
            this._onSwimlaneChange();
        },
        _onSwimlaneChange: function(){
            var selected = this.getSelectedLanes(),
                search = this.createMergedSearch(selected);

            if (!selected || selected.length < 1 || !search) {
                return;
            }

            this.set('mergedSearch', search);
            this.runSearch();
        },
        onSearchStart: function(){
            this.set('loading', true);
        },
        onSearchDone: function(state, job){
            this.set('loading', false);
        },
        onData: function(){
            var collection = this._data.collection(),
                min,
                max,
                earliest,
                latest;

            if(collection.models.length){
                collection.each(function(m){
                    var time,
                        numEvents;

                    time = m.get('_time');
                    m.set('_time', new Date(time));

                    numEvents = m.get('numEvents');
                    m.set('numEvents', Number(numEvents));
                });

                min = collection.min(function(m){
                    return m.get('numEvents');
                });

                max = collection.max(function(m){
                    return m.get('numEvents');
                });

                this.set({
                    'earliest': this.timeRange.get('outerTimeRange').earliest_date,
                    'latest': this.timeRange.get('outerTimeRange').latest_date,
                    'min': min.get('numEvents'),
                    'max': max.get('numEvents')
                });

            }
            // Ensure that everything is ready by the time data is set
            this.set('data', collection);
        },
        createMergedSearch: function(selected){
            var mergedSearch = "";

            _.each(selected, function(swimlane, i){
                if (!swimlane.get('constraints')) {
                    return;
                }

                var tokens = _.extend({}, swimlane.attributes, {span: this.timeRange.get('outerSpan')}), 
                    search = tokenUtils.replaceTokenNames(swimlane.get('search'), tokens, {});

                if(search[0] !== "|"){
                    search = "search "+search;
                }

                if(i > 0){
                    mergedSearch += " | append [" + search + "]";
                } else {
                    mergedSearch += search;
                }

            }, this);

            if (mergedSearch.length > 0) {
                mergedSearch += " | stats sum(count) as numEvents by _time";
            } else {
                mergedSearch = undefined;
            }

            return mergedSearch;
        },
        runSearch: function(){
            var outerTimeRange = this.timeRange.get('outerTimeRange');

            if (this.manager) {
                this.manager.trigger('search:cancel', undefined, this.manager.job);
                this.manager.off('search:start');
                this.manager.off('search:done');
                this._data.off('data');
                this.manager.cancel();
            }

            this.manager = new SearchManager({
                autostart: false,
                id: _.uniqueId('timerange_linegraph_'),
                earliest_time: outerTimeRange.earliest_date.getTime()/1000,
                latest_time: outerTimeRange.latest_date.getTime()/1000,
                search: this.get('mergedSearch')
            }, {tokens: false});
 
            this.managers.add(this.manager);

            this.manager.on('search:start', this.onSearchStart, this);
            this.manager.on('search:done', this.onSearchDone, this);

            this._data = this.manager.data('preview');
            this._data.on('data', _.bind(this.onData, this));
        },
        getSelectedLanes: function(){
            return this.swimlanes.filter(function(swimlane){
                return swimlane.get('selected');
            });
        }
    });
});
