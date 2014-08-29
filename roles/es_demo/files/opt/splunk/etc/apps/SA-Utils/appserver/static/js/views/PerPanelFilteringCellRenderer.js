/**
 * This cell renderer adds a checkbox to table cells and renders blocklisted entries with an icon.
 */
define(function(require, exports, module) {
	
    // Load dependencies
    var _ = require('underscore');
    var mvc = require('splunkjs/mvc');
    var $ = require('jquery');
    
    var BaseCellRenderer = require('views/shared/results_table/renderers/BaseCellRenderer');
    
    var PerPanelFilteringCellRenderer = BaseCellRenderer.extend({
    	
    	 defaults: {
             show_checkboxes: true
    	 },
    	 
         initialize: function() {
             
			 args = _.extend({}, this.defaults);

			 for( var c = 0; c < arguments.length; c++){
			 	args = _.extend(args, arguments[c]);
			 }

             // Get the arguments
             this.show_checkboxes = args.show_checkboxes;
         },
    	 
    	 canRender: function(cell) {
    		 return (cell.index === 0 && cell.value !== null) || $.inArray(cell.field, ["filter"]) >= 0;
		 },
		 
		 render: function($td, cell) {
			 
			 if( cell.index === 0 && this.show_checkboxes ){
				 
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
			 else if(cell.value == "blacklist"){
				 
				 
				 $td.html(_.template('<i style="font-size: 14pt; color: #E22" class="icon icon-alert-circle"></i>', {
			    	 value: cell.value,
			    	 field: cell.field
			     }));
				 
			 }
			 else{
				 $td.html(cell.value);
			 }

		     
		 }
	});
    
    return PerPanelFilteringCellRenderer;
});