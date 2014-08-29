/**
 * Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
 */

function validate (data) {
	
	// If the cell is the first row, then ensure that the new value is not blank
	if( data[0][0] === 0 && data[0][3].length === 0 ){
		return false;
	}
}

function lookupRenderer(instance, td, row, col, prop, value, cellProperties) {
	
	Handsontable.TextCell.renderer.apply(this, arguments);

	if(!value || value === '') {
		td.className = 'cellEmpty';
	}
	else if (parseFloat(value) < 0) { //if row contains negative number
		td.className = 'cellNegative';
	}
	else if( String(value).substring(0, 7) == "http://"){
		td.className = 'cellHREF';
	}
	else if (parseFloat(value) > 0) { //if row contains positive number
		td.className = 'cellPositive';
	}
	else if(row === 0) {
		td.className = 'cellHeader';
	}
	else if(value === 'true') {
		td.className = 'cellTrue';
	}
	else if(value === 'false') {
		td.className = 'cellFalse';
	}
	else if(value === 'unknown') {
		td.className = 'cellUrgencyUnknown';
	}
	else if(value === 'informational') {
		td.className = 'cellUrgencyInformational';
	}
	else if(value === 'low') {
		td.className = 'cellUrgencyLow';
	}
	else if(value === 'medium') {
		td.className = 'cellUrgencyMedium';
	}
	else if(value === 'high') {
		td.className = 'cellUrgencyHigh';
	}
	else if(value === 'critical') {
		td.className = 'cellUrgencyCritical';
	}
	else {
		td.className = '';
	}
	
	if(cellProperties.readOnly) {
	    td.style.opacity = 0.7;
	}
	
}

function setupTable( data ){
	
	if (data === null){
		data = [
			["", "", "", ""],
			["", "", "", ""]
		];
	}
	
	new_jquery("#dataTable").handsontable({
	  data: data,
	  startRows: 1,
	  startCols: 1,
	  minSpareRows: 0,
	  minSpareCols: 0,
	  colHeaders: false,
	  rowHeaders: true,
	  contextMenu: true,
	  stretchH: 'all',
	  manualColumnResize: true,
	  manualColumnMove: true,
	  onBeforeChange: validate,
	  
	  cells: function (row, col, prop) {
		    var cellProperties = {};
		    
		    cellProperties.type = {
		      renderer: lookupRenderer
		    };
		    
		    return cellProperties;
		  }
	  
	});
}

function gotoToList(){

	if( $('#returnto').length > 0 && $('#returnto').val() ){
		document.location = $('#returnto').val();
	}
}

function getTableAsJSON(){
	
	var data = [];
	var rows = 0;
	
	$('table.htCore').find('tr:not(:last-child)').each(function(){
		var id = $(this).attr('id');
		var row = [];
		rows = rows + 1;
		
		$(this).find('td:not(:last-child)').each(function(){
			row.push( $(this).text() );
		});

		data.push(row);
	} );

	return data;
}

function saveSuccess(){
	console.log("Lookup file saved successfully");

	$("#save > span").text("Save");
	
	var messenger = Splunk.Messenger.System.getInstance();
	messenger.send('info', "splunk.sa_utils", "File successfully updated");
	
	// Return the user to the lookup list
	gotoToList();
}

function saveLookup(){
	$("#save > span").text("Saving...");
	
	// Use a delay so that the event loop is able to change the button text before the work begins
	setTimeout( doSaveLookup, 100);
}
	
function doSaveLookup(){
	
	var handsontable = new_jquery("#dataTable").data('handsontable');
	row_data = handsontable.getData();
	
	json = JSON.stringify(row_data);
	
	data = {
			lookup_file : lookup_file,
			namespace   : namespace,
			contents    : json
	};
	
	if (data["lookup_file"] === ""){
		data["lookup_file"] = $("#lookup_file_input").val();
	}

	// Make sure that the file name was included
	if (data["lookup_file"] === ""){
		$("#item-lookup-file > div > .widgeterror").text("Please define a file name");
		$("#item-lookup-file > div > .widgeterror").show();
		$("#save > span").text("Save");
		return false;
	}

	// Make sure at least a header exists
	if(row_data.length === 0){
		$("#item-data-table > div > .widgeterror").text("Lookup files must contain at least one row (the header)");
		$("#item-data-table > div > .widgeterror").show();
		loadLookupContents( lookup_file, namespace, user, true );
		$("#save > span").text("Save");
		alert("Lookup files must contain at least one row (the header)");
		return false;
	}
	
	// Make sure the headers are not empty.
	// If the editor is allowed to add extra columns then ignore the last row since this for adding a new column thus is allowed
	for( i = 0; i < row_data[0].length; i++){
		if( row_data[0][i] === "" ){
			$("#item-data-table > div > .widgeterror").text("The header rows cannot be empty");
			$("#item-data-table > div > .widgeterror").show();
			alert("Header rows cannot contain empty cells (column " + (i + 1) + " of the header is empty)");
			return false;
		}
	}
	
	$.ajax( Splunk.util.make_url('/custom/SA-Utils/lookupeditor/save'),
			{
				uri:  Splunk.util.make_url('/custom/SA-Utils/lookupeditor/save'),
				type: 'POST',
				data: data,
				
				beforeSend: function(xhr) {
					xhr.setRequestHeader('X-Splunk-Form-Key', $('input[name=splunk_form_key]').val());
				},
				
				success: saveSuccess,
				
				error: function(jqXHR,textStatus,errorThrown) {
					console.log("Lookup file not saved");
					alert("The lookup file could not be saved");
					$("#save > span").text("Save");
				} 
			}
	);
	
	return false;
	
}

function setupView(){
	loadLookupContents( lookup_file, namespace, user, false );
}

function setupHandlers(){
	$("#save").click( saveLookup );
	$("#cancel").click( gotoToList );
	
	// Make sure that the variables that indicate which lookup to load are defined. Don't bother continuing if they weren't.
	if (typeof lookup_file !== 'undefined' && typeof namespace !== 'undefined') {
		
		// Set the data-table width and height so that the editor takes up the entire page
		// We shouldn't have to do this since we should be able to use width of 100%. However, width 100% only works if
		// the parents have widths defined all the way to the top (which they don't).
		$('#dataTable').width( $(document).width() - 100 ) ;
		$('#dataTable').height( $(document).height() - 320 ) ;
		
		// Setup the view. We are going to delay this because we have to swap out the jQuery version and we need to Splunk
		// javascripts to complete first.
		setTimeout(setupView, 300);
	}
}

$(document).ready( setupHandlers );

function loadLookupContents(lookup_file, namespace, user, header_only){
    url = Splunk.util.make_full_url("/custom/SA-Utils/lookupeditor/get_lookup_contents", 
                  {"lookup_file":lookup_file,
                   "namespace":namespace,
                   "header_only":header_only});
	
	$ = new_jquery;
	
	$.ajax({
		  url: url,
		  cache: false,
		  success: function(data) {
			  console.info('JSON of lookup table was successfully loaded');
			  setupTable( data );
			  $("#tableEditor").show();
		  },
		  complete: function(jqXHR, textStatus){
			  if( jqXHR.status == 404){
				  console.info('Lookup file was not found');
				  alert("The lookup could not be loaded from the server as the file does not appear to exist. This can happen if you have not run setup yet.");
			  }
			  else if( jqXHR.status == 403){
				  console.info('Inadequate permissions');
				  alert("You do not have permission to view lookup files (you need the 'edit_lookups' capability)");
			  }
			  
			  
			  $(".table-loading-message").hide();
		  },
		  error: function(jqXHR, textStatus, errorThrown){
			  if( jqXHR.status != 404 && jqXHR.status != 403 ){
				  console.info('Lookup file could not be loaded');
				  alert("The lookup could not be loaded from the server");
			  }
		  }
	});

	$ = old_jquery;
}

Splunk.Module.SOLNLookupEditor = $.klass(Splunk.Module, {
	
    initialize: function($super,container) {
        var retVal = $super(container);
        
    	// Get the name of the view to redirect to and save it so that we can redirect
    	$('#returnto').val( this.getParam('listView') );
        
        // Get a reference to the form
        var formElement = $('form', this.container);
        
        // Update the form call with an Ajax request submission
        formElement.submit(function(e) {
        	
        	// Initiate the Ajax request
            try {
                $(this).ajaxSubmit({
                	
                	// Upon the successful processing of the Ajax request, evaluate the response to determine if the status was created
                    'success': function(json) {
                		var messenger;
                		
                		// If successful, print a message noting that it was successful
                        if (json["success"]) {
                        	
                        	// Print a message noting that the change was successfully made
                        	messenger = Splunk.Messenger.System.getInstance();
                        	messenger.send('info', "splunk.SA-Utils", json["message"]);
                        	
                        // If it was unsuccessful, then print an error message accordingly
                        } else {
                            messenger = Splunk.Messenger.System.getInstance();
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
    
    handleSubmitCallback: function() {
    	var messenger = Splunk.Messenger.System.getInstance();
    	messenger.send('info', "splunk.SA-Utils", "Action succeeded");
    	
    }
});