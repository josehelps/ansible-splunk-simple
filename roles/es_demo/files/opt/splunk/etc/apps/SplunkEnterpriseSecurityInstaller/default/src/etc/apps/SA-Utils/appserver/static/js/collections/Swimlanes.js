define([
    'jquery',
    'underscore',
    'backbone',
    'app/models/Pref',
    'app/models/Swimlane',
    'app/collections/SwimlaneGroups',
    'splunk.util',
    'backbone-mediator'
], function(
    $,
    _,
    Backbone,
    Pref,
    Swimlane,
    SwimlaneGroups
) {
    return Backbone.Collection.extend({
        default_groups: {
            'Custom': {
              id: 'Custom',
              lanes: [],
              title: 'Custom',
              sync_filter: null
            }
        },
        keys: {
            "action.swimlane.constraint_fields": "constraint_fields",
            "action.swimlane.constraint_method": "constraint_method",
            "action.swimlane.title": "title",
            "action.swimlane.color": "color",
            "search": "search",
            "action.swimlane.drilldown_search": "drilldown"
        },
        model: Swimlane,
        pref_id: 'swimlanes',
        initialize: function(models, options){
            this.app_name = options.app_name;
            this.groups = new SwimlaneGroups();
            this.managers = options.managers;
            this.prefs = options.prefs;
            this.sign_board = options.sign_board;
            this.time_range = options.time_range;
            this.user_name = options.user_name || 'nobody';
            this.view_name = options.view_name;
            this.sync_filter = options.sync_filter;
            
            if( !this.sync_filter ){
            	this.sync_filter = "swimlane AND display.page."+this.view_name;
            }

            this.prefs.on('reset', _.bind(this.onPrefReset, this));
            this.on('drag:selection', _.bind(this.onChannelDragSelection, this));
            this.on('add:manager', _.bind(this.onManagerAdd, this));
            this.on('update:manager', _.bind(this.onManagerUpdate, this));
        },
        /*
         * add manager to the managers collection
         */
        onManagerAdd: function(manager) {
            this.managers.add(manager);
        },
        /*
        manager already exists, tell this.managers to update
        */
        onManagerUpdate: function(manager) {
            this.managers.addToQueue(manager);
        },
        /*
         * given original and last coordinates as well as the 
         * offset y position of the channel that originated the drag,
         * fire events on models with the range of x and y coordinates 
         * between the first and last drag events, effectively delegating
         * to the models to determine if they have any events to select 
         */
        onChannelDragSelection: function(x1, x2, y1, y2, offset_y, is_additive) {
            var collection = this,
                range_x = this.getRange(x1, x2),
                range_y = this.getRange(y1, y2, offset_y);

            this.each(function(model){
                if (model.get('selected')===true) {
                    model.trigger('drag:coordinates', range_x, range_y, is_additive);
                }
            }, this);
        },
        /* 
         * given two y coordinates and an optional offset, 
         * create lowest and highest values, making sure to
         * reverse coordinates if the end coord < start coord
         */
        getRange: function(c1, c2, offset) {
            if (!offset) {
                offset = 0;
            }
            c1 = c1 + offset;
            c2 = Math.max(c2 + offset, 0);
            if (c2 < c1) {
                return [c2, c1];
            } else {
                return [c1, c2];
            }
        },
        onLaneOrderChange: function(model) {
            var changed = model.changedAttributes(),
                pref = this.getPref(),
                selected = pref.get('selected'),
                lane_order = pref.get('lane_order') || {};

            // only update prefs for Custom group
            if (selected==='Custom' && changed && changed.lanes) {
                 lane_order[selected] = changed.lanes; 
                 pref.set({'lane_order': lane_order});
                 pref.save();
            }
        },
        onLaneSelection: function(model) {
            var pref = this.getPref(),
                group_name = pref.get('selected'),
                group = this.groups.get(group_name),
                lane_order = group.get('lanes') || [],
                is_selected = model.get('selected'); 

            if (is_selected) {
                lane_order.push(model.id);
            } else {
                lane_order = _.without(lane_order, model.id);
            }

            lane_order = _.uniq(lane_order);

            group.set({'lanes': lane_order});
        },
        onGroupsReset: function() {
            var pref = this.getPref(),
                selected = pref.get('selected'),
                lane_order = pref.get('lane_order') || {};

            this.groups.each(function(model) {
                lane_order[model.id] = model.get('lanes');
            });

            pref.save({lane_order: lane_order});
        },
        onGroupSelection: function(model) {
            var collection = this,
                lanes = model.get('lanes'),
                title = model.get('title'),
                disabled = title !== 'Custom' ? true : false,
                pref = this.getPref();

            // must set prefs before the rest
            pref.save({
                selected: title
            });

            // When a new group is selected, we must update the lane selection
            collection.each(function(m) {
                var idx = _.indexOf(lanes, m.get('id'));

                if(idx > -1){
                    m.set({
                      'selected': true,
                      'disabled': disabled
                    });
                } else {
                    m.set({
                      'selected': false,
                      'disabled': disabled
                    });
                }
            });
        },
        /*
         * after prefs have been reset, we can safely fetch the swimlanes 
         */
        onPrefReset: function() {
            // add listener here in case something else resets groups before prefs are fetched
            this.groups.on('reset', _.bind(this.onGroupsReset, this));
            this.fetch({
                reset: true,
                success: _.bind(this.onFetch, this)
            }); 
        },
        getPref: function() {
            return this.prefs.getPref(this.pref_id);
        },
        /*
         * success callback for fetch of existing prefs 
         */
        onFetch: function() {
            var pref = this.getPref(),
                model;

            // try to find the model for the group selected in prefs
            if (pref) {
                model = this.groups.find(
                  function(m) {
                    return m.get('title')===pref.get('selected');
                  }
                );
            }

            // set selected group from prefs, use first group if no prefs
            if (model) {
                model.set('selected', true);
            } else if (this.groups.length > 0) {
                model = this.groups.at(0);
                model.set('selected', true); 
            } 

            this.onGroupSelection(model); 

            // bind here now that prefs are synced and group settings are current
            this.groups.on('change:selected', _.bind(this.onGroupSelection, this));
            this.groups.on('change:lanes', _.bind(this.onLaneOrderChange, this));
            this.on('change:selected', _.bind(this.onLaneSelection, this));
        },
        /*
         * each swimlane must have:
         *  - the requred k/v as defined in this.keys
         *  - a prefs collection containing the user's UI preferences
         *    - prefs override default settings for color, order, and lane_order
         *  - a groups collection containing the available swimlane groups
         *  - a sign board collection containing events that should be displayed on the signboard
         *  - a time range model containing the shared time state 
         */
        parse: function(resp, opt) {
            var view_name = this.view_name,
                flag = 'collection_name',
                groups = this.default_groups,
                keys = this.keys,
                sign_board = this.sign_board,
                time_range = this.time_range,
                pref = this.getPref(),
                group_prefs = pref.get('lane_order') || {},
                lane_prefs = pref.get('lane_prefs') || {},
                swimlanes = _.map(resp.entry, function(entry) {
                    var obj = {};
                    _.each(entry.content, function(val, key) {
                        if (_.contains(_.keys(keys), key)) {
                            obj[keys[key]] = val;
                        }
                        else if (key.indexOf(view_name) >- 1 && key.indexOf(flag) > -1) {
                            var order_key = key.replace(flag, "order"),
                                order = Number(entry.content[order_key]),
                                group = entry.content[key],
                                lane_order = group_prefs[group],
                                title = obj['title'];

                            if (lane_order && lane_order.length < 1) {
                                lane_order = undefined;
                            }

                            if (!groups[group]) {
                                groups[group] = {
                                  id: group,
                                  lanes: lane_order || [title],
                                  title: group
                                };
                            }
                            // noop if lane_order is already defined
                            else if (lane_order) {
                                null;
                            } else {
                                groups[group]['lanes'].splice(order, 0, title);
                            }
                        }
                    });
                    obj['id'] = obj['title'];
                    obj['pref'] = pref;
                    obj['sign_board'] = sign_board;
                    obj['time_range'] = time_range;
                    if (lane_prefs[obj['id']]) {
                        obj['color'] = lane_prefs[obj['id']].color || obj['color'];
                        obj['selected'] = lane_prefs[obj['id']].selected || false;
                    }
                    return obj;
            });
            groups['Custom'].lanes = group_prefs['Custom'] || [];
            this.groups.reset(_.map(groups, function(v){ return v; }));
            return swimlanes;
        },
        url: function() {
            if (this.app_name) {
                return Splunk.util.make_url(
                    "/splunkd/servicesNS/"+
                    this.user_name+
                    "/"+
                    this.app_name+
                    "/saved/searches?search="+
                    this.sync_filter+
                    "&output_mode=json"
                );
            }
            return Splunk.util.make_url(
                "/splunkd/services/saved/searches?search="+
                this.sync_filter+
                "&output_mode=json"
            );
        }
    });
});
