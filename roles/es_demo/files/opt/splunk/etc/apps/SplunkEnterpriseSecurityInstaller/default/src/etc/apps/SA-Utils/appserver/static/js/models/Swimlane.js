define([
    'jquery',
    'backbone',
    'underscore',
    'd3',
    'splunkjs/mvc/searchmanager',
    'splunkjs/mvc',
    'app/collections/Events',
    'splunkjs/mvc/tokenutils'
],
function(
    $,
    Backbone,
    _,
    d3,
    SearchManager,
    SJS,
    Events,
    tokenUtils
){
    return Backbone.Model.extend({
        defaults: {
            channel: {
                rect: {
                    className: 'channel_rect',
                    x: 190,
                    y: 0,
                    fill: 'transparent',
                    stroke: '#CCCCCC',
                    width: 840 
                }
           },
           label: {
                rect: {
                    className: 'lane_label_rect',
                    x: 0,
                    y: 0,
                    fill: '#6E6E6E',
                    width: 190 
                },
                text: {
                    className: 'lane_label_text',
                    dx: 20,
                    dy: 25,
                    fill: '#FFFFFF' 
                }
            },
            color: 'blue',
            disabled: false,
            height: 40,
            offset: 0,
            order: 0,
            span: '1h',
            timerange: {
                earliest_date: '-24h', 
                latest_date: 'now'
            },
            title: 'loading...',
            token: 'entity'
        },
        comparitor: 'offset',
        initialize: function(){
            this.pref = this.get('pref');
            this.sign_board = this.get('sign_board');
            this.time_range = this.get('time_range');

            this.set('entity_name', this.pref.get('entity_name'));
            this.tokens = SJS.Components.getInstance(this.id, {create: true});

            this.onRangeChange = _.debounce(this._onRangeChange, 500);

            // conventional change events
            this.on('change:color', _.bind(this.updateColorPref, this));
            this.on('change:selected', _.bind(this.onSelectedChange, this));
            
            this.on('change:earliest_epoch change:latest_epoch', _.bind(this.onTimeChange, this));

            // when drag coordinates are received
            this.on('drag:coordinates', _.bind(this.onDragCoordinates, this));
            
            // when lanes are reordered
            this.on('reorder:lane_order', _.bind(this.savePref, this));

            // when constraints are set
            this.on('change:constraints', _.bind(this.updateManager, this));

            // bind to time range changes to update search manager
            this.time_range.on('change:innerTimeRange', _.bind(this.onRangeChange, this));

            this.pref.on("change:entity_name", _.bind(this.updateEntityName, this));
        },
        updateManager: function() {
            this.setTokens();
            if (!this.manager && this.get('selected')) {
                this.updateDrilldown();
                this.manager = this.getNewManager();
                this.trigger('add:manager', this.manager);
            } else if (this.get('selected')) {
                this.updateDrilldown();
                this.trigger('update:manager', this.manager);
            }
        },
        /*
         * if this model has coordinates in the dragged y coordinates
         * select the events that are within the selected coordinates
         */
        onDragCoordinates: function(range_x, range_y, is_additive) {
            var label = this.get('label'),
                channel = this.get('channel'),
                width = channel.rect.width,
                x_offset = label.rect.width,
                events = this.get('events');

            if (this.isYIntersect(range_y)) {
                if (!events || events.length < 1) {
                    return;
                }
                events.each(function(evt) {
                    evt.trigger('click:coordinates', range_x, is_additive);
                }, this);
            }
        },
        /*
         * return true if there is any intersection between the
         * drag y coordinates and the model y coordinates
         */ 
        isYIntersect: function(range_y) {
            var height = this.get('height'),
                y1 = this.get('offset')*height,
                y2 = y1+height;

            // http://gamedev.stackexchange.com/questions/586/what-is-the-fastest-way-to-work-out-2d-bounding-box-intersection
            return !(range_y[0] > y2
                    || range_y[1] < y1);
        },
        updateDrilldown: function() {
            var drilldown = this.get('drilldown'),
                normalizedDrilldown;

            if (drilldown !== undefined){
                normalizedDrilldown = tokenUtils.replaceTokenNames(drilldown, this.tokens.attributes, {});
                this.set('normalizedDrilldown', normalizedDrilldown);
            }

        },
        getNewManager: function() {
            var innerTimeRange = this.time_range.get('innerTimeRange'),
                earliest_epoch = this.get('earliest_epoch') || innerTimeRange.earliest_date.getTime()/1000,
                latest_epoch = this.get('latest_epoch') || innerTimeRange.latest_date.getTime()/1000;

            return new SearchManager({
                autostart: false,
                id: _.uniqueId('channel_manager_'),
                earliest_time: earliest_epoch,
                latest_time: latest_epoch,
                search: this.get('search')
            }, {tokens: true, tokenNamespace: this.id});
        },
        onTimeChange: function() {
            if (this.manager) { 

                this.setTokens();

                this.manager.search.set({
                    earliest_time: this.get('earliest_epoch'),
                    latest_time: this.get('latest_epoch')
                });

                // trigger the time range change so that searches will re-dispatch
                this.manager.trigger('change:innerTimeRange', this.manager);

                this.sign_board.reset();
            }
        },
        _onRangeChange: function(model) {
            // don't update range if not selected
            if (!this.get('selected')) {
                return;
            }

            var innerTimeRange = this.time_range.get('innerTimeRange'),
                earliest_epoch = innerTimeRange.earliest_date.getTime()/1000,
                latest_epoch = innerTimeRange.latest_date.getTime()/1000;

            this.set({
                earliest_epoch: earliest_epoch,
                latest_epoch: latest_epoch
            });
        },
        updateEntityName: function(model, value) {
            this.set("entity_name", value);
        },
        savePref: function(model) {
            this.pref.save();
        },
        setTokens: function() {
            this.tokens
                .set('constraints', this.get('constraints'))
                .set('span', this.time_range.get('span') || this.get('span'));
        },
        updateColorPref: function() {
            var lane_prefs = this.pref.get('lane_prefs') || {},
                lane_pref = lane_prefs[this.id] || {};
            lane_pref.color = this.get('color');
            lane_prefs[this.id] = lane_pref;
            this.pref.save();
        },
        onSelectedChange: function(model) {
            var is_selected = model.get('selected'),
                group = this.pref.get('selected'),
                lane_orders = this.pref.get('lane_order') || {},
                lane_order = lane_orders[group] || [], 
                lane_prefs = this.pref.get('lane_prefs') || {},
                lane_pref = lane_prefs[this.id] || {};

            // on model instantiation, selected may be undefined
            if (is_selected===undefined) {
                return;
            }
            
            if (is_selected && !this.manager && this.get('constraints')) {
                this.updateManager(); 
            }

            // only allow adding/removing of lane order for 'Custom' group
            if (group==='Custom') {
                if (is_selected) {
                    lane_order.push(model.id);
                } else {
                    lane_order = _.without(lane_order, model.id);
                }
                lane_order = _.uniq(lane_order);
                lane_orders[group] = lane_order;
            }

            // update selected prefs for all groups
            lane_pref.selected = is_selected;
            lane_prefs[this.id] = lane_pref;
              
            this.pref.save({
                lane_prefs: lane_prefs,
                lane_order: lane_orders
            });
        }
    });
});
