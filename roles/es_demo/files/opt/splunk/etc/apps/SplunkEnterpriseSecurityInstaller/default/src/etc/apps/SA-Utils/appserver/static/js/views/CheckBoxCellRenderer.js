/**
 * This cell renderer adds a checkbox to table cells.
 */
define(function(require, exports, module) {
	
    // Load dependencies
    var _ = require('underscore');
    var mvc = require('splunkjs/mvc');
    var $ = require('jquery');
    
    var BaseCellRenderer = require('views/shared/results_table/renderers/BaseCellRenderer');
    
    var CheckBoxCellRenderer = BaseCellRenderer.extend({
    	 canRender: function(cell) {
    		 return (cell.index === 0 && cell.value !== null) || $.inArray(cell.field, ["filter"]) >= 0;
		 },
		 
		 render: function($td, cell) {

				 // Move the contents to the right so that it matches the header
				 if( cell.columnType == "number"){
					 $td.addClass("numeric");
				 }
				 
				 // Render the checkbox in the cell
				 $td.html(_.template('<label style="float:left""><input name="<%- field %>" value="<%- value_quote_escaped %>" style="margin-top: 0px; margin-right: 2px" class="cell-row-checkbox" type="checkbox" /> </label><%- value %>', {
			    	 value: cell.value,
			    	 field: cell.field,
			    	 value_quote_escaped : cell.value.replace('"', '\\"')
			     }));

			 // Stop propagation of the click handler so that check boxes can be changed
			 $('input', $td).click( function(event){ event.stopPropagation();} );
		 }
	});
    
    return CheckBoxCellRenderer;
});