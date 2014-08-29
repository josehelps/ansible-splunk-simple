/**
 * This cell renderer renders a number with an arrow indicating whether the value is going up or down.
 */
define(function(require, exports, module) {
    
    // Load dependencies
    var _ = require('underscore');
    var mvc = require('splunkjs/mvc');
    var $ = require('jquery');
    
    var BaseCellRenderer = require('views/shared/results_table/renderers/BaseCellRenderer');
    
    var TrendCellRenderer = BaseCellRenderer.extend({
        
        defaults: {
            trend_columns: ['trend', 'change', 'delta']
        },
     
        initialize: function() {
            
             args = _.extend({}, this.defaults);
    
             for( var c = 0; c < arguments.length; c++){
                args = _.extend(args, arguments[c]);
             }
    
             // Get the arguments
             this.trend_columns = args.trend_columns;

        },
        
        canRender: function(cell) {
            // Only use the cell renderer for the specified columns
            return _.indexOf(this.trend_columns, cell.field) >= 0;
        },
        
        render: function($td, cell) {
            
            // Parse the integer, we'll use this value if the value isn't in the "NN (+NN)" form
            var value_int = parseInt(cell.value, 10);

            // If the trend is in the format "52 (+16)" then parse out the trend
            var regex = /[+](-?[0-9]+)/g;
            var matches = regex.exec(cell.value);

            if(matches) {
                value_int = matches[1];
            }

            // Determine the trend 
            var trend = "none";

            if( isNaN(value_int) ){
                trend = "none";
            }
            else if(value_int > 0){
                trend = "up";
            }
            else if(value_int < 0){
                trend = "down";
            }

            // Translations from rangemap results to CSS class
            var ICONS = {
                up: 'arrow-up',
                none: '',
                down: 'arrow-down'
            };
            
            var STYLES = {
                 up: {'color': 'red'},
                 none: '',
                 down: {'color': 'green'}
            };
            
            var style = "";

            // Fetch the style for the value
            if (STYLES.hasOwnProperty(trend)) {
                style = STYLES[trend];
            }
            
            $td.css(style);
            $td.addClass("numeric");
            
            // Fetch the icon for the value
            var icon = null;
            
            if (ICONS.hasOwnProperty(trend)) {
                icon = ICONS[trend];
            }
            
            // Create the icon element and add it to the table cell
            if( icon !== null ){
                $td.addClass('icon').html(_.template('<i style="margin-right: 3px;" class="icon-<%-icon%>"></i><%- value %>', {
                    icon: icon,
                    value: cell.value
                }));
            }
            else{
                $td.html(_.template('<%- value %>', {
                    icon: icon,
                    value: cell.value
                }));
            }
            
        }
    });
    
    return TrendCellRenderer;
});