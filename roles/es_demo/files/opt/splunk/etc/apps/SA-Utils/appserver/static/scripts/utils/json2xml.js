define([
    "jquery",
    "underscore"
], function(
    $,
    _
) {
    /* 
    take nav editor json and turn it into XML to save to data/ui/nav/default.xml
    */
    return function() {

        function recurseObj(obj) {
            var $el = $("<" + obj.type + " />");
            $el.text(obj.text);
            _.each(obj.attributes, function(val, key) {
                $el.attr(key, val);
            });
            _.each(obj.children, function(child) {
                $el.append(recurseObj(child));
            });
            return $el;
        }

        function convertJSON(data) {
            var $result = $("<result></result>");
            $result.append(recurseObj(data));

            return $result.html();
        }

        return {convertJSON: convertJSON};
    };
});