define([
    'jquery',
    'backbone',
    'underscore'
],
function(
    $,
    Backbone,
    _
){
    /*
    The `id` param is optional
    If not specified, we can only read, not save
    todo: enforce that behavior
    */
    return function(componentId, id, fieldName){
        var router = new Backbone.Router();

        function parseQueryString(){
            var queryBreak = window.location.href.indexOf('?'),
                query;

            if(queryBreak > -1){
                query = window.location.href.slice(queryBreak);
                return Splunk.util.queryStringToProp(query);
            }

            return false;    
        }

        function setCurrentData(data, current, id){
            var currentData;

            if(!current){
                current = {};
            }

            if(current[componentId] === undefined){
                current[componentId] = {};
                current[componentId][id] = data;
                current[componentId] = JSON.stringify(current[componentId]);
                return current;
            }

            if(current[componentId] !== undefined){
                currentData = JSON.parse(current[componentId]);
                currentData[id] = data;
                current[componentId] = JSON.stringify(currentData);
            }

            return current;
        }

        function makeNewURL(data){
            var current = parseQueryString(),
                newQuery;

            current = setCurrentData(data, current, id);
            newQuery = Splunk.util.propToQueryString(current);
            return newQuery;
        }

        function relativeNav(query){
            if(query[0] !== '?'){
                query = '?'+query;
            }
            router.navigate(window.location.pathname+query, {trigger: true, replace:true});
        }

        function save(data){
            var newQuery = makeNewURL(data);
            relativeNav(newQuery);
        }

        this.getEntityName = function() {
            var data = parseQueryString();
            return data["form."+fieldName];            
        };

        this.setEntityName = function(entityName) {
            var query = "form." + fieldName + "=" + entityName;
            relativeNav(query);
        };

        this.exists = function(){
            var data = parseQueryString();
            
            if (data[componentId] === undefined || data[componentId] === "") {
                return false;
            }

            if(id === undefined || id === false){
                return true;
            } 

            data = JSON.parse(data[componentId]);
            if(data[id] === undefined){
                return false;
            } 

            return true;
        };

        this.createURL = function(models, options){
            var baseURL,
                url,
                json,
                query,
                current,
                urlData = {};

            options = options || {};
            options = _.extend({fullUrl:true}, options);

            current = parseQueryString();

            _.each(models, function(model){
                json = model.toJSON();
                setCurrentData(json, urlData, model.id);
            });

            // prefer our new data, overwrite any existing
            urlData = _.extend({}, current, urlData);

            query = Splunk.util.propToQueryString(urlData);
            if(!options.fullUrl){
                return query;
            }

            baseURL = window.location.href;

            if(current){
                baseURL = baseURL.split("?")[0];
            }

            url = baseURL + '?' + query;

            return url;
        };

        this.sync = function(method, model, options) {
            var current,
                urlData,
                data;

            switch (method) {
                case "read":
                    current = parseQueryString();
                    if(!current || current[componentId] === undefined){
                        break;
                    }

                    urlData = JSON.parse(current[componentId]);
                    if(fieldName !== undefined 
                        && fieldName !== false
                        && current[fieldName] !== undefined
                    ){
                        _.each(urlData, function(item){
                            item[fieldName] = current[fieldName];
                        });
                    }
                    options.parseUrl = true;
                    // This feeds back to 'parse' with our new URL data
                    options.success(model, urlData, options);
                    
                    break;
                case "create":
                    if (!model.componentId){
                        model.set(model.idAttribute, _.uniqueId());
                    }
                    data = model.toJSON();
                    save(data);
                    break;
                case "update":
                    data = model.toJSON();
                    save(data);
                    break;
                case "delete":
                    break;
                default:
                    break;
           }
        };
    };
});
