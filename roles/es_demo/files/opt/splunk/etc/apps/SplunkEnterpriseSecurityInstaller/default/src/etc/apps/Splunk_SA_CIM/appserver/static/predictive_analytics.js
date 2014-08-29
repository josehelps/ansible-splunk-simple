
// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore','splunkjs/mvc','splunkjs/mvc/tokenawaremodel','views/shared/results_table/renderers/BaseCellRenderer', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc, TokenAwareModel, BaseCellRenderer){

    /*------ Token Handling ------*/
    var submittedTokens = mvc.Components.get('submitted');
    
    // When the function token changes...
    submittedTokens.on('change:function change:attribute', _.debounce(function(){
        
        // if function exists
        if(submittedTokens.has('function') && submittedTokens.get('function') !== null) {
            var func = submittedTokens.get('function');
            
            // if attribute exists and is not *
            if (submittedTokens.has('attribute') && submittedTokens.get('attribute') !== null && submittedTokens.get('attribute') !== '*') {
                var attrib = submittedTokens.get('attribute');
                
                submittedTokens.set('aggregate',func + '(' + attrib + ')');
            }
            // if attribute does not exist or is *
            else {
                // if function is count
                if (func === 'count') {
                    submittedTokens.set('aggregate',func);
                }
                // if function is not count
                else {
                    alert('All functions other than count require an attribute!');
                }
            }
        }
        else {
            alert('Please select a function!');
        }
    }));
    
    /*------ Table Styling ------*/
    var table1Element = mvc.Components.get('table1');

    var CustomIconCellRenderer = BaseCellRenderer.extend({
        canRender: function(cell) {
            var excludedFields = ['_time', 'predict'];
            
            if(cell.field.substring(0, 5) == 'lower' || cell.field.substring(0, 5) == 'upper'){
                return false;
            }

            return !_.contains(excludedFields, cell.field);
        },
        render: function($td, cell) {           
            var cell_value = cell.value;
            
            var decoration = cell_value.match(/##icon-\S+##/);
            
            if (decoration !== null) {
                cell_value = cell_value.replace(decoration[0],'');
                
                decoration = decoration[0].replace(/##/g,'');
                                
                $td.addClass('icon').html(_.template('<%- cell_value %><i class="<%- decoration %>" title="<%- decoration %>"></i>', {
                    cell_value: cell_value,
                    decoration: decoration
                }));
            }
            else {
                $td.html(_.template('<%- cell_value %>', {
                    cell_value: cell_value
                }));
            }
        }
    });

    table1Element.getVisualization(function(tableView){
        tableView.table.addCellRenderer(new CustomIconCellRenderer());
        tableView.table.render();
    });
    
    
    /*------ Make Correlation Search ------*/
    getCorrelationSearch = function(){
        var correlationSearchModel = new TokenAwareModel({
            earliest: mvc.tokenSafe('$earliest$'),
            latest: mvc.tokenSafe('$latest$'),
            search: mvc.tokenSafe("| tstats $aggregate$ from datamodel=$dm$ where nodename=\"$object$\" by _time span=$span$ | predict lower$lower$=lower upper$upper$=upper $predict_options$ $aggregate$ as predict | where ('$aggregate$'<'lower$lower$(predict)' OR '$aggregate$'>'upper$upper$(predict)'")
            }, {tokens: true, tokenNamespace: 'submitted'});
        
        return correlationSearchModel;
    }
    
    initEditor = function( ){
        $('#nameField').val("");
        $('#severityField').val("");
        $('#descriptionField').val("");
        $('#domainField').val("");
    }

    showSuccessMessage = function( sid ){
        
        // Doesn't work due to SPL-71631
        //var template = _.template(
        //        $( "script.successMessageTemplate" ).html()
        //);
        
        var template = _.template('The correlation search was successfully created.<p><br/><a target="_blank" href="correlation_search_edit?name=<%- sid %>">View created search</a></p>');
        
        $('#successMessage').html( template( { sid : sid } ) );
    }
    
    showMakeSearchButton = function(){
        
        // Determine if the endpoint for making correlation searches is available and if the ability to make correlation searches ought to be presented
        $.ajax( 
                {
                    url:  Splunk.util.make_url('/custom/SA-ThreatIntelligence/correlationsearchbuilder/ping'),
                    type: 'GET',
                    
                    success: function(data, textStatus, jqXHR){
                        $('#openCorrelationSearchDialog').show();
                    },
                    
                    error: function(jqXHR,textStatus,errorThrown) {
                        $('#openCorrelationSearchDialog').hide();
                    } 
                }
        );
    }
    
    isInputValid = function(){
        
        var failed = false;
        
        // Check the search name
        if( $('#nameField').val().length == 0 ){
            $('#correlationSearchNameGroup').addClass('error');
            failed = true;
        }
        else{
            $('#correlationSearchNameGroup').removeClass('error');
        }
        
        // Check the search description
        if( $('#descriptionField').val().length == 0 ){
            $('#correlationSearchDescriptionGroup').addClass('error');
            failed = true;
        }
        else{
            $('#correlationSearchDescriptionGroup').removeClass('error');
        }
        
        return !failed;
    }
    
    // Wire up the button to save the correlation search dialog
    $('#makeCorrelationSearch').click( function(){
        
        // Get the search
        searchModel = getCorrelationSearch();
        
        // Don't try to submit the input if the content is not valid
        if( !isInputValid() ){
            return;
        }
        
        $("#makeCorrelationSearch").text("Saving...");
        $("#makeCorrelationSearch").attr("disabled", "true");
        $('.loading').show();
        
        // Put together the data
        data = {
            security_domain : $('#domainField').val(),
            earliest : searchModel.attributes['earliest'],
            latest : searchModel.attributes['latest'],
            name : $('#nameField').val(),
            severity : $('#severityField').val(),
            search : searchModel.attributes['search'],
            description : $('#descriptionField').val()
        }
        
        // Post it to the server
        $.ajax( 
                {
                    url:  Splunk.util.make_url('/custom/SA-ThreatIntelligence/correlationsearchbuilder/save'),
                    type: 'POST',
                    data: data,
                    
                    success: function(object){ return function(data, textStatus, jqXHR){
                        $('#successMessage').show();
                        
                        showSuccessMessage(JSON.parse(data)['sid']);
                        
                        $('#editor').hide();
                        $('.loading').hide();
                        $('#makeCorrelationSearch').hide();
                        $("#makeCorrelationSearch").text("Save");
                        $("#makeCorrelationSearch").removeAttr("disabled");
                        
                        initEditor();
                    } }(this),
                    
                    error: function(jqXHR,textStatus,errorThrown) {
                        alert("Correlation search could not be saved");
                        $('.loading').hide();
                        $("#makeCorrelationSearch").text("Save");
                        $("#makeCorrelationSearch").removeAttr("disabled");
                    } 
                }
        );
        
        
    });
    
    // Wire up the button to open the correlation search dialog
    $('#openCorrelationSearchDialog').click( function(){
        
        if( mvc.Components.get('search2').search.attributes['earliest_time'] === undefined ){
            $('#runSearchFirstModal').modal();
            return;
        }
        
        $('#successMessage').hide();
        $('#editor').show();
        $('#makeCorrelationSearch').show();
        $('#createCorrelationSearchModal').modal();
    });
    
    $('#nameField').keyup(isInputValid);
    $('#descriptionField').keyup(isInputValid);
    showMakeSearchButton();
    
    /*--- Predictive Analytics advanced options ---*/
    function updateDisplayedOptions(){
        
        // Hide future_timespan and show correlate if LLB algorithm is selected
        if( $('#algorithmField').val() === "LLB"){
            $('#futureTimespan').hide();
            $('#correlate').show();
        }
        else{
            $('#futureTimespan').show();
            $('#correlate').hide();
        }
        
        // Hide period unless LLP algorithm is selected
        if( $('#algorithmField').val() === "LLP"){
            $('#period').show();
        }
        else{
            $('#period').hide();
        }

        //populateAttributes();
        
    }
    
    function populateAttributes(){

        var existing_selected_value = $('#correlateField').val();

        // Clear the fields
        $('#correlateField').html("");

        // Initialize variables for the loop
        var value = null;
        var title = null;
        var selected = '';

        // Get the fields from the attributes list
        $('#field4 option').each(function() {

            value = $(this).val();
            title = $(this).text();

            if( value !== "*" ){

                if( value === existing_selected_value ){
                    selected = "selected";
                }
                else{
                    selected = "";
                }

                $('#correlateField').append('<option value="' + value + '" ' + selected + '>' + title + "</option>");
                 
            }
        });
    }

    function getAdvancedPredictArgs(){
        var args = {
                algorithm: $('#algorithmField').val(),
                future_timespan: $('#futureTimespanField').val(),
                //correlate: $('#correlateField').val(), //LLB is not supported yet
                holdback: $('#holdbackField').val(),
                period: $('#periodField').val()
        }
        
        var arg_string = "";
        
        for (var key in args) {
            if( args[key] !== ""){
                arg_string = arg_string + key + "=" + args[key] + " ";
            }
        }
        
        return arg_string;
    }
    
    function performValidate(field_selector, val, message, test_function){
        if( !test_function(val) ){
            $(".help-inline", field_selector).show().text(message);
            $(field_selector).addClass('error');
            return 1;
        }
        else{
            $(".help-inline", field_selector).hide();
            $(field_selector).removeClass('error');
            return 0;
        }
    }
    
    function parseIntIfValid(val){
    	
    	var intRegex = /^[-]?\d+$/;
    	
    	if( !intRegex.test(val) ){
    		return NaN;
    	}
    	else{
    		return parseInt(val, 10);
    	}
    }
    
    function isValidTimespan(span){
    	var timeSpecifiers = ['y', 'mon', 'd', 'h', 'm', 's'];
    	
    	var spanRegex=/([0-9]+)(y|(mon)|d|h|m|s)/i;
    	var matches = spanRegex.exec(span);
    	
    	if(matches){
	    	var number = matches[1];
	    	var units = matches[2];
	    	
	    	return true;
    	}
    	else{
    		return false;
    	}
    	
    }
    
    function validateOptions(){
        
        // Record the number of failures
        var failures = 0;
        
        // Verify span is valid
        failures += performValidate( $('#span'), $('#spanField').val(), "Must be a valid timespan",
                function(val){ 
                    return val.length == 0 || isValidTimespan(val);
                }
        );
        
        // Verify lower is between 0-100
        failures += performValidate( $('#lower'), $('#lowerField').val(), "Must be between 0 and 100",
                function(val){ 
                    return val.length == 0 || (parseIntIfValid(val, 10) > 0 && parseIntIfValid(val, 10) < 100);
                }
        );
        
        // Verify upper is between 0-100
        failures += performValidate( $('#upper'), $('#upperField').val(), "Must be between 0 and 100",
                function(val){ 
                    return val.length == 0 || (parseIntIfValid(val, 10) > 0 && parseIntIfValid(val, 10) < 100);
                }
        );
        
        // Verify holdback is positive (if set)
        failures += performValidate( $('#holdback'), $('#holdbackField').val(), "Must be a positive integer",
                function(val){ 
                    return val.length == 0 || (parseIntIfValid(val, 10) > 0);
                }
        );

        // Verify future timespan is zero or more (if set) if algorithm is not LLB
        failures += performValidate( $('#futureTimespan'), $('#futureTimespanField').val(), "Must be zero or more",
                function(val){ 
                    return $('#algorithmField').val() == "LLB" || val.length == 0 || parseIntIfValid(val, 10) >= 0;
                }
        );

        // Verify that the correlate field is provided if algorithm is LLB
        failures += performValidate( $('#correlate'), $('#correlateField').val(), "Must not be empty",
                function(val){ 
                    return $('#algorithmField').val() != "LLB" || val.length > 0;
                }
        );
        
        // Return a boolean indicating the validation succeeded or not
        return failures === 0;
        
    }
    
    // Wire up the button to open the predict options dialog
    $('#predictOptionsDialog').click( function(){
        updateDisplayedOptions();
        $('#predictCommandOptionsModal').modal();
    });
    
    // If the algorithm field changes, make sure that options that do not appy are hidden
    $('#algorithmField').change( function(){
        updateDisplayedOptions();
    });
    
    // If a field value changes, then validate the new values
    $('#options input').change( validateOptions );
    
    // If close is pressed, then validate the arguments and close the modal
    $('#setPredictOptions').on('click', function(){
    	
        if( validateOptions() ){
        	
        	// Set the span
        	var span = $('#spanField').val();
        	
        	if( span !== null && span.length > 0 ){
        		submittedTokens.set('span', span);
        	}
        	else{
        		submittedTokens.set('span', '10m');
        	}
        	
        	// Set the advanced predict options
            submittedTokens.set('predict_options', getAdvancedPredictArgs());

            // Set the lower and upper settings
            var lower = $('#lowerField').val();
            var upper = $('#upperField').val();

            if(lower.length == 0){
                lower = '95';
            }

            if(upper.length == 0){
                upper = '95';
            }

            submittedTokens.set('lower', lower);
            submittedTokens.set('upper', upper);

            // Hide the modal
            $('#predictCommandOptionsModal').modal('hide');
        }
    });
    
    // Fill the tokens with some default values so that the search can be kicked off even if the user didn't change items in the advanced dialog
    submittedTokens.set('predict_options', '');
    submittedTokens.set('lower', '95');
    submittedTokens.set('upper', '95');
    submittedTokens.set('span', '10m');

});