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
        defaults: function(){
        },
        initialize: function(options){
            this.prefs = options.prefs;
            this.baseUrl = Splunk.util.make_url("app", "SplunkEnterpriseSecuritySuite", "ess_notable_event_create");
            this.collection = options.collection;
            this.url = "#";
            this.collection.on('add remove reset', function(){
                this.update();
            }, this);
        },
        update: function(selectedEvents){
            var url = this.baseUrl,
                qs,
                drilldown_url,
                currentPath;
            
            // Determine if we are on the asset_investigator or the entity_investigator
            var view_name = "asset_investigator";
            
            if(document.location.pathname.indexOf("identity_investigator") > 0){
            	view_name = "identity_investigator";
            }
            
            currentPath = Splunk.util.make_url("app", "SplunkEnterpriseSecuritySuite", view_name);
            drilldown_url = currentPath + '?' + this.prefs.serializeToURL({fullUrl:false});

            qs = Splunk.util.propToQueryString({
                drilldown_name: "View in entity investigator",
                drilldown_url: drilldown_url
            });

            url += "?" + qs;

            this.set('url', url);
        }
    });
});


