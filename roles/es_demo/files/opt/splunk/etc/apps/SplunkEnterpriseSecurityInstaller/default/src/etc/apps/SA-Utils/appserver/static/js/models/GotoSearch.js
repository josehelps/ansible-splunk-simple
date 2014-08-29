define([
    'jquery',
    'backbone',
    'underscore',
    'd3'
],
function(
    $,
    Backbone,
    _,
    d3
){
    return Backbone.Model.extend({
        initialize: function(options){
            this.baseUrl = Splunk.util.make_url("app", "SplunkEnterpriseSecuritySuite", "search");
            this.url = "#"; // noop at first
            this.collection = options.collection;
            this.swimlanes = options.swimlanes;

            this.update = _.debounce(this._update, 50);

            this.collection.on('add remove reset', function(){
                this.update();
            }, this);
        },
        _update: function(){
            var earliest, latest,
                mergedSearch = "",
                i = 0,
                url,
                currentSearch,
                queryData = {},
                drilldowns = {};

            if(this.collection.models.length > 0){
                earliest = this.collection.min(function(model) {
                    return model.get('meta').earliest_time;
                }).get('meta').earliest_time;
                
                latest = this.collection.max(function(model) {
                    return model.get('meta').latest_time;
                }).get('meta').latest_time;

                _.each(this.collection.models, function(model){
                    var meta,
                        laneName;
                    meta = model.get('meta');
                    laneName = meta.lane_name;

                    if(drilldowns[laneName] === undefined){
                        currentSearch = "";
                        drilldowns[laneName] = meta.drilldown;

                        if(meta.drilldown) {
                            if (meta.drilldown[0] !== "|"){
                                currentSearch = "search "+meta.drilldown;
                            } else {
                                currentSearch = meta.drilldown;
                            }

                            if(i > 0){
                                mergedSearch += " | append [" + currentSearch + "]";
                            } else {
                                mergedSearch += currentSearch;
                            }

                            i += 1;
                        }
                    }
                });

                queryData = {
                    q: mergedSearch,
                    earliest: earliest.getTime()/1000,
                    latest: latest.getTime()/1000
                };

                url = this.baseUrl + "?" + Splunk.util.propToQueryString(queryData);

                this.set('url', url);
            }
        }
    });
});
