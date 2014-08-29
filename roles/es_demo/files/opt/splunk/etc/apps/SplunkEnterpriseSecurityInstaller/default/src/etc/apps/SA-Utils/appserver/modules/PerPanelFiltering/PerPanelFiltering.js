
Splunk.Module.PerPanelFiltering = $.klass(Splunk.Module.DispatchingModule, {
	
    initialize: function($super,container) {
        var retVal = $super(container);
        
        $(".perPanelFileringPopupLink", this.container).click(this.openPopupForm.bind(this));
        
        $("#ppf_prev", this.container).click(this.previousPage.bind(this));
        $("#ppf_next", this.container).click(this.nextPage.bind(this));
        
        // Get a reference to the form
        var formElement = $('form', this.container);
        
        // Update the form call with an Ajax request submission
        formElement.submit(function(e) {
        	
        	// Initiate the Ajax request
            try {
                $(this).ajaxSubmit({
                	
                	// Upon the successful processing of the Ajax request, evaluate the response to determine if the status was created
                    'success': function(json) {
                		var messenger = Splunk.Messenger.System.getInstance();
                		
                		// If successful, print a message noting that it was successful
                        if (json["success"]) {
                        	
                        	// Print a message noting that the change was successfully made
                        	messenger.send('info', "splunk.SA-Utils", json["message"]);
                        	
                        	// Force a reload
                        	var m = moduleReference;
                        	
                        	// Find the search to dispatch
                        	while (m.getContext().get("search").isJobDispatched()) {
                        		m = m.parent;
                            }
                        	
                        	// Push the content in order to re-submit the search
                        	m.pushContextToChildren();
                        	
                        // If it was unsuccessful, then print an error message accordingly
                        } else {
                            messenger.send('error', "splunk.SA-Utils", _('ERROR - ') + json["message"] || json);
                        }
                    },
                    'dataType': 'json'
                });
                
            // The Ajax request failed, print an exception
            } catch(e) {
                alert(e);
            }

            return false;

        });
        
        return retVal;
    },
   	
    populateForm: function(data){
    	
    	// The list of fields that we are to filter
    	fields_to_get = [];
    	
    	// Get the fields from the form
    	$('.entityEditForm:visible input[name=fields]').each(function() {
    		
    		// Get the field value
    		value = $(this).attr("value");
    		
    		// Only add the field if it is not in the array already
    		if ( jQuery.inArray(value, fields_to_get) == -1 ){
    			fields_to_get.push(value);
    		}
    	});
    	
    	// The list of columns indexes to get
    	columns_to_get = [];
    	                  
    	// Determine the column numbers to get
    	for( i = 0; i < fields_to_get.length; i = i + 1 ){
    		for( j = 0; j < data.fields.length; j = j + 1 ){    			
    			if( data.fields[j] == fields_to_get[i]){
    				columns_to_get.push(j);
    			}
    		}
    	}
    	
    	// Create the header of the table
    	html = "<thead><tr><th></th>";
    	
    	for( i = 0; i < fields_to_get.length; i = i + 1 ){
    		html += "<th>" + fields_to_get[i] + "</th>";
    	}
    	
    	$("#ppf_table").html(html + "</tr></thead>");
    	
    	// Define a function for shortening long text strings
    	function ellipsify (str, max_length) {
    	
	    	if( max_length === null | max_length === undefined ){
	    		max_length = 50;
	    	}
	    	
	        if (str.length > max_length) {
	            return (str.substring(0, max_length) + "...");
	        }
	        else {
	            return str;
	        }
	    }
    	
    	// Add each row, add the HTML
    	for( i = 0; i < data.columns[0].length && i < 10; i = i + 1 ){
    		
    		html = ""; // This will be the HTML for the new table
    		value = undefined; // The unique value of the row that ought to be sent to the CSV
    		
    		for( j = 0; j < columns_to_get.length; j = j + 1){
    			
    			// Get the field value
    			field_value = data.columns[ columns_to_get[j] ][i];
    			
    			// If the field is an array (which happens with multi-line fields)
    			if( $.isArray(field_value) ){
    				field_value = field_value.join("");
    			}
    			
    			// Get the unique value that will be passed to the server and used to make the CSV
    			if( value == undefined ){
    				value = field_value;
    			}
    			else{
    				value += "|" + field_value;
    			}
 
    			
    			html += "<td><label ";
    			
    			if( field_value.length > 70 ){
    				html += 'title="' + field_value + '" ';
    			}
    			
    			html += "for=\"checkbox_" + i + "\">" + ellipsify(field_value, 70) + "</label></td>";
    		}
    		
    		html = "<tr><td><input class=\"ppf_value\" id=\"checkbox_" + i + "\" type=\"checkbox\" name=\"values\" value=\"" + value + "\"></input></td>" + html + "</tr>";
    		
    		$("#ppf_table").append(html + "</tr>");
    	}
    	
    },
    
    nextPage: function(evt){
    	this.updateWithResults(evt, 1);
    },
    
    previousPage: function(evt){
    	this.updateWithResults(evt, -1);
    },
    
    updateWithResults: function(evt, change){
    	
    	if( $('.entityEditForm:visible input[name=page]').length > 0 ){
    		page_number = parseInt( $('.entityEditForm:visible input[name=page]')[0].value, 10);
    	}
    	else{
    		page_number = 0;
    	}
    	
    	// Set the page number if it was not already defined
    	if( page_number === undefined || page_number === null ){
    		page_number = 0;
    	}
    	
    	// Determine the amount of change (for changing pages)
    	if( change === undefined || change === null ){
    		change = 0;
    	}
    	
    	// Get the resulting page number
    	page_number = page_number + change;
    	
    	if( page_number < 0 ){
			page_number = 0;
		}
    	
    	// Get the actual number of search results
    	search_results_count = this.getEntityCount();
    	
    	offset = page_number * 10;
    	page_count = 10;
    	
    	// If we are already on the last page, then stop
    	if( offset >= search_results_count ){
    		return;
    	}
    	
    	// Disable the next button if there are no more results
    	if( search_results_count <= (offset + page_count) ){
    		$('#ppf_next').addClass("disabled");
    	}
    	else{
    		$('#ppf_next').removeClass("disabled");
    	}
    	
    	// Disable the next button if there are no more results
    	if( page_number === 0 ){
    		$('#ppf_prev').addClass("disabled");
    	}
    	else{
    		$('#ppf_prev').removeClass("disabled");
    	}
    	
    	// Set the page number so that we remember where we are
    	if( $('.entityEditForm:visible input[name=page]').length > 0){
    		$('.entityEditForm:visible input[name=page]')[0].value = page_number;
    	}
    	
    	// Get the search from the context so that we can determine if it is finalized
    	var context = this.getContext();
    	var search = context.get("search");
    	
        var params = new Object();
        var sid = search.job.getSID();
        params.sid = sid;
        
        params.showOffset = 1;
        params.segmentation = 'raw';
        params.output_mode = 'json_cols';
        params.offset = offset;
        params.count = page_count;
        
        var uri = Splunk.util.make_url('/splunkd/search/jobs/', sid,(search.job.isDone()) ? '/results' : '/results_preview');
        uri += '?' + Splunk.util.propToQueryString(params);
        
        $.getJSON( uri, this.populateForm );
    },
    
    getEntityCount: function(){
        var count;
        var context = this.getContext();
        var search  = context.get("search");
        switch(this.entityName){
            case this.AUTO_ENTITY_NAME:
                count = search.job.areResultsTransformed() ? search.job.getResultCount() : search.getEventAvailableCount();
                break;
            case this.EVENTS_ENTITY_NAME:
                //Search now has it's own getEventAvailableCount
                //that will return the correct answer even when the user has 
                //selected a subset of the timerange  
                count = search.getEventAvailableCount();
                break;
            case this.RESULTS_ENTITY_NAME:
                count = search.job.getResultCount();
                break;
            case this.SETTINGS_MAP_ENTITY_NAME:
                count = this.length;
                break;
            default:
                this.logger.error("Invalid module entityName value of", this.entityName);
                count = 0;
                break;
        }
        return count;
    },
    
    // Open the popup form
    openPopupForm: function(evt) {
    	 
    	// Get the search from the context so that we can determine if it is finalized
    	//var context = this.getContext();
    	//var search = context.get("search");
    	
        var popup = null;
        var clonedForm = null;
        
        var formToClone = $("form", this.container);
        
        //var params = new Object();
        //var sid = search.job.getSID();
        //params.sid = sid;
        
        //params.showOffset = 1;
        //params.segmentation = 'raw';
        //params.output_mode = 'json_cols';
        
        //var uri = Splunk.util.make_url('/splunkd/search/jobs/', sid,(search.job.isDone()) ? '/results' : '/results_preview');
        //uri += '?' + Splunk.util.propToQueryString(params);
        
        this.updateWithResults();
        
        //$.getJSON( uri, this.populateForm );
        
        // Now we create the instance of the Popup element and pass in our handleUpdate callback.
        // This will clone the contents of our form and create the popup onscreen.
        // All is ready for the user.
        this.popup = new Splunk.Popup(formToClone[0], {
            title: _('Filter Results from Panel'),
            buttons: [
                {
                    label: _('Cancel'),
                    type: 'secondary',
                    callback: function(){
                        return true;
                    }
                },
                {
                    label: _('Update'),
                    type: 'primary',
                    callback: this.onFormSubmit.bind(this)
                }
            ]
        });
        popupReference = this.popup.getPopup();

        this.clonedForm = $(popupReference).find("form");
        this.clonedForm.attr("action",this.getResultURL());
        
        return false;
        
    },
    
    
    // Submit the form
    onFormSubmit: function() {
    	
        var moduleReference = this;
        
        // Make sure that the user selected at least one item
        if( $("input.ppf_value:checked").length === 0 ){
        	alert("No items were selected. Please select at least one item to continue.");
        	return false;
        }
        
        // Submit the form
        try {
        	
            // Change it from 'Update' to 'Updating' 
            $('div.popupFooter button.splButton-primary span', this.popup._popup).text(_('Updating...'));
            
            // Grey it out and unbind the handler so you can't click it twice.
            $('div.popupFooter button.splButton-primary', this.popup._popup).unbind('click').removeClass('primary').addClass('secondary');
            
            if( $('input[name=namespace]:first', this.clonedForm).length > 0 ){
            	reload_page_after_editing = $('input[name=reload_page_after_editing]:first', this.clonedForm)[0].value.toLowerCase() == 'true' || $('input[name=reload_page_after_editing]:first', this.clonedForm)[0].value == '1';
            }
            else{
            	reload_page_after_editing = false;
            }
            
            this.clonedForm.ajaxSubmit({
                'success': function(json) {
                    var messenger = Splunk.Messenger.System.getInstance();

                    if( $('div.popupFooter button.splButton-primary span').text().indexOf("Updating...") >= 0 ){
	                    Splunk.Popup._globalPopupCount -= 1;
	                    $('.popupContainer').remove();
	                    $('.splOverlay').remove();
                    }
                    
                    if (json["success"]) {
                	
                        // Print a success message if some changes were successfully submitted
                    	messenger.send('info', "splunk.ess", json["message"] );
                    	
                    	//Reload the page or re-dispatch the search
                    	if( reload_page_after_editing ){
                    		window.location = window.location;
                    	}
                    	else{
                        	// Resubmit the search
                        	var module = moduleReference;
                        	
                        	// Find the search to dispatch
                        	while (module.getContext().get("search").isJobDispatched()) {
                                module = module.parent;
                            }
                        	
                        	// Push the content in order to re-submit the search
                            module.pushContextToChildren();
                    	}
                    } else {
                        messenger.send('error', "splunk.ess", json["message"] || json);
                    }
                },
                'dataType': 'json'
            });
            return false;
        } 
        
        // If we're going to fail, fail fast and fail loud. 
        catch(e) {
            var messenger = Splunk.Messenger.System.getInstance();
            messenger.send('error', "splunk.ess", "an unexpected error occurred -- " + e);
        }
        
        return false;
    },
    
    
    handleSubmitCallback: function() {
    	var messenger = Splunk.Messenger.System.getInstance();
    	messenger.send('info', "splunk.SA-Utils", "Action succeeded");
    	
    }
});