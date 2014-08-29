require([
    'underscore',
    'jquery',
    'splunkjs/mvc',
    'splunkjs/mvc/tableview',
    'splunkjs/mvc/simplexml/ready!'
], function(_, $, mvc, TableView) {

    // Translations from rangemap results to CSS class
    var ICONS = {
        severe: 'alert-circle',
        elevated: 'alert',
        low: 'check-circle'
    };
   
/*----------------------Enabled Treatlist Panel Renderer----------------------*/

    var EnabledThreatListsRenderer = TableView.BaseCellRenderer.extend({
        canRender: function(cell) {
            // Only use the cell renderer for the 'status' field
            return _(['status']).contains(cell.field);
        },
        render: function($td, cell) {
        	
        	if (cell.field === 'status') {
	            var icon = 'question';
	            // Fetch the icon for the value
	            if (ICONS.hasOwnProperty(cell.value)) {
	                icon = ICONS[cell.value];
	            }
	            // Create the icon element and add it to the table cell
	            $td.addClass('icon').html(_.template('<i class="icon-<%-icon%> ' + 
	            		'<%- range %>" title="<%- range %>"></i>', {
	                icon: icon,
	                range: cell.value
	            }));
        	}
        	
        	if (_(['low', 'elevated', 'severe']).contains(cell.value)) {
        		$td.addClass(cell.value);
        	}
        }
    });
    
/*----------------------Local Treatlist Panel Renderer------------------------*/
    
    var LocalThreatListsRenderer = TableView.BaseCellRenderer.extend({
        canRender: function(cell) {
            // Enable this custom cell renderer for the 'lastTime' field
            return _(['lastTime']).contains(cell.field);
        },
        render: function($td, cell) {
            // Add a class to the cell based on the returned value
            var value = String(cell.value);

            // Validate Input --
            var date_re = /\d{4}-\d{2}-\d{2}T\d{2}\:\d{2}\:\d{2}/;
            var matches = value.match(date_re);

            if (matches !== null) {

                var last_modified_time = new Date(String(matches[0]));
                var last_modified_time_epoch = last_modified_time.getTime();

                var today = new Date();
                var today_epoch = today.getTime();

                // Elapsed Time in MilliSeconds --
                elapsed_time = today_epoch - last_modified_time_epoch;

                if (cell.field === 'lastTime') {
                    // 15552000 == Number of MilliSeconds in 180 Days
                    if (elapsed_time >= 15552000000) {
                        $td.addClass('range_severe');
                    }
                    // 7776000 == Number of MilliSeconds in 90 Days
                    else if (elapsed_time >= 7776000000) {
                        $td.addClass('range_elevated');
                    }
                    else {
                        $td.addClass('range_low');
                    }
                }
            }

            // Update the cell content
            $td.text(value).addClass('numeric');
        }
    });
    
/*----------------------Enabled Treatlists Panel------------------------------*/

    mvc.Components.get('enabled_threatlist_table').getVisualization(
		function(tableView){
	        // Register custom cell renderer
	        tableView.table.addCellRenderer(new EnabledThreatListsRenderer());
	        // Force the table to re-render
	        tableView.table.render();
	    }
	);

/*------------------------Local Treatlists Panel------------------------------*/

    mvc.Components.get('local_threatlist_table').getVisualization(
    	function(tableView) {
	        // Add custom cell renderer
	        tableView.table.addCellRenderer(new LocalThreatListsRenderer());
	
	        // Force the table to re-render
	        tableView.table.render();
	    }
    );
});