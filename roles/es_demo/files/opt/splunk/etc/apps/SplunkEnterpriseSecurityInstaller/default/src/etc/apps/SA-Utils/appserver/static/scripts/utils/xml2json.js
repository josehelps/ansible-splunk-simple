define([
    "jquery",
    "underscore"
], function(
    $,
    _
) {
    /* 
        translates XML gotten from data/ui/nav/default.xml to 
        something the nav editor can process in JSON
    */
    return function(data) {
        var flattened = [];

        function recurseEl(el) {
            var children = $(el).children(),
                result = {};

            result.type = $(el).prop("tagName");
            result.attributes = {};
            _.each(el.attributes, function(attr) {
                result.attributes[attr.nodeName] = attr.nodeValue;
                if (attr.nodeName === "name"
                    || attr.nodeName === "label") {
                    result.name = attr.nodeValue;
                }
            });
            result.text = $(el).text();

            result.children = [];
            _.each(children, function(child) {
                result.children.push(recurseEl(child));
            });
            
            return result;
        }

        function convertXML(str) {
            // convert from str to DOM
            var parser = new DOMParser(),
                dom = parser.parseFromString(str, "text/xml");

            return recurseEl($(dom).children()[0]);
        }

        if (!_.isUndefined(data)) {
            convertXML(data);
        }

        return {convertXML: convertXML, flattened: flattened}; 
    };
    
});