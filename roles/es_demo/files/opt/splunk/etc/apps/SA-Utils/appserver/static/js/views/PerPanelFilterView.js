require.config({
    paths: {
        text: '../app/SA-Utils/js/lib/text'
    }
});

define(['underscore', 'splunkjs/mvc', 'jquery', 'splunkjs/mvc/simplesplunkview', 'text!../app/SA-Utils/js/templates/PerPanelFilter.html'],
function(_, mvc, $, SimpleSplunkView, PerPanelFilterTemplate) {
	
    // Define the custom view class
    var PerPanelFilterView = SimpleSplunkView.extend({
        className: "PerPanelFilterView",
        
        /**
         * Setup the defaults
         */
        defaults: {
        	link_title: "Advanced Filter...",
        	owner: "nobody"
        },
        
        /**
         * Event handlers
         */
        events: {
            "click #openPerPanelFilteringDialog": "openOptionsDialog",
            "click #ppfDialogSave": "save"
        },
        
        /**
         * Initialize the key indicators view
         */
        initialize: function() {
        	
        	// Apply the defaults
        	this.options = _.extend({}, this.defaults, this.options);
        	
        	// Get the arguments
            this.lookup_file = this.options.lookup_file; // The lookup file to place the filters results into
            this.lookup_name = this.options.lookup_name; // The lookup name (based on prosp/transforms) to place the filters results into
            this.namespace = this.options.namespace; // The app that hosts the lookup file
            this.owner = this.options.owner; // The owner of the lookup file (defaults to nobody)
            this.fields = this.options.fields.slice(0); // The fields to put into the PPF filter
            this.panel_id = this.options.panel_id; // The panel ID of the table with checkboxes indicating the results to filter on
            this.$panel_id = $(this.options.panel_id);
            this.search_managers = this.options.search_managers.slice(0); // Includes the search managers that ought to be restarted once the filters are updated
            this.link_title = this.options.link_title; // The title of the link
            this.lookup_edit_view = this.options.lookup_edit_view; // The link to the view where one can edit the PPF lookup file
        },
        
        /**
         * Render the view
         */
        render: function() {
        	this.$el.html( _.template(PerPanelFilterTemplate,{ 
        		link_title: this.link_title,
        		lookup_edit_link: this.lookup_edit_view
        	}));
        },
        
        /**
         * Open the dialog for filtering.
         */
        openFilteringDialog: function(){
        	console.warn("Dialog not implemented yet!");
        },
        
        /**
         * Trim whitespace from a string
         */
        trim: function(str) 
        {
            return String(str).replace(/^\s+|\s+$/g, '');
        },
        
        /**
         * Determine if any highlighted items are selected.
         */
        areHighlightedSelected: function(){
        	
        	selected_checkboxes = $('.cell-row-checkbox:checked', this.$panel_id);

        	for( var i=0; i < selected_checkboxes.length; i++){
        	    if( $(".icon", $(selected_checkboxes[i]).parent().parent().parent()).length > 0 ){
        	        return true;
        	    }
        	}
        	
        	return false;
        },
        
        /**
         * Get arguments that can be passed to the REST endpoint for persisting the changes.
         */
        getArgData: function(){
        	
        	// Setup the argument data
        	arg_data = {};
        	
        	arg_data.owner = this.owner;
        	arg_data.namespace = this.namespace;
        	arg_data.fields = this.fields;
        	arg_data.filter = $('input[name=filter]:checked', this.$el).val();
        	
        	if( this.lookup_file !== null ){
        		arg_data.lookup_file = this.lookup_file;
        	}
        	
        	if( this.lookup_name !== null ){
        		arg_data.lookup_name = this.lookup_name;
        	}
        	
        	// Determine the field names from the header
        	fields_offset = {};
        	
        	$.each( $('th', this.$panel_id), function(index, value) {
        		fields_offset[ value.getAttribute("data-sort-key") ] = index;
        	});
        	
        	// Get the selected items and populate a list of the field values
        	fields_values = [];
        	
        	$.each( $('.cell-row-checkbox:checked', this.$panel_id).parent().parent().parent(), function(index, row_node) {
        		
        		// Iterate through the fields and add each corresponding value
        		for( var i = 0; i < this.fields.length; i++ ){
        			
        			// Find the offset of the field
        			column = fields_offset[ this.fields[i] ];
        			
        			// Determine which column contains the value
        			var c = 0;
        			current = row_node.firstChild;
        			
        			while(null !== current) {
        				
        				// If the offset matches this cell, then use this value
        				if( c == column ){
        					fields_values.push( this.trim(current.textContent ) );
        					break;
        				}
        				
        				// Evaluate the next sibling
        			    current = current.nextSibling;
        			    c++;
        			}
        			
        		}
        	}.bind(this));
        	
        	arg_data.values = fields_values;
        	
        	return arg_data;
        },
        
        /**
         * Called after a save was successful and results in restarting the searches
         */
        saveSuccess: function(){
        	$('#ppfOptions', this.$el).modal('hide');
        	
        	// Kick the search
        	if( this.search_managers ){
        		
        		// If the search managers are an array, then kick off them all
        		if( Object.prototype.toString.call( this.search_managers ) === '[object Array]' ) {
        			
        			for( var i = 0; i < this.search_managers.length; i++ ){
        				this.search_managers[i].startSearch();
        			}
        		}
        		else{
        			this.search_managers.startSearch();
        		}
        		
        	}
        },
        
        /**
         * Open the options dialog for filtering some selected items.
         */
        openOptionsDialog: function(){
        	
        	var items_selected = $('.cell-row-checkbox:checked', this.$panel_id).length;
        	
        	// Stop if no results were selected
        	if( items_selected === 0 ){
        		$('#ppfNoResults', this.$el).modal('show');
        		return;
        	}
        	
        	// Show the unhighlight option if filtered items are selected
        	if( this.areHighlightedSelected() ){
        		$('#unhighlight-radio', this.$el).show();
        	}
        	else{
        		$('#unhighlight-radio', this.$el).hide();
        	}
        	
        	// Update the text of the modal dialog
        	if( items_selected == 1){
        		$('#row-count', this.$el).html("1 result");
        	}
        	else{
        		$('#row-count', this.$el).html( items_selected.toString() + " results");
        	}
        	
        	// Show the dialog
        	$('#ppfOptions', this.$el).modal('show');
        },
        
        /**
         * Save the selected filters.
         */
        save: function(){
        	
        	data = this.getArgData();
        	
        	// Prepare to make a call to the per-panel endpoint to save the filter
            $.ajax( 
                    {
                        url:  Splunk.util.make_url('/custom/SA-Utils/perpanelfiltering/update'),
                        type: 'POST',
                        data: data,
                        traditional: true,
                        
                        success: function(){
                        	console.info("Key indicators saved successfully");
                        	this.saveSuccess();
                        }.bind(this),
                        
                        error: function(jqXHR,textStatus,errorThrown) {
                            console.warn("Panel filters could not saved");
                            alert("The panel filters could not be saved");
                        } 
                    }
            );
        	
        }
    });
     
    
    return PerPanelFilterView;
});