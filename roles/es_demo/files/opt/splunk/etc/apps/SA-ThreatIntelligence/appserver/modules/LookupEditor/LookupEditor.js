/**
 * Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
 */

Splunk.Module.LookupEditor = $.klass(Splunk.Module, {
    initialize: function($super,container) {
        var retVal = $super(container);
        
        // if path is returned as 'insufficient_permissions' do not attempt to load the csv
        // this provides cleaner page rendering to the user
        path = $("#selectedLookup").val();
        
        if (path != 'insufficient_permissions') {
        	this.loadCsv(app, path);
        }
        
        var formElement = $('form', this.container);
        formElement.submit(function(e) {
            try {
                $(this).ajaxSubmit({
                    'success': function(json) {
                        if (json["success"]) {
                            // TODO - display success message / error message
                            window.location = listView;
                        } else {
                            var messenger = Splunk.Messenger.System.getInstance();
                            messenger.send('error', "this_string_effectively_means_nothing", _('ERROR - ') + json["messages"][0]["message"] || json);

                        }
                    },
                    'dataType': 'json'
                });
            } catch(e) {
                alert(e);
            }

            return false;

        });

        return retVal;
    },
    
    loadCsv: function(app, path) {
        var url = Splunk.util.make_url('custom','SA-ThreatIntelligence','lookupeditor','load');
        $.ajax({
            url: url,
            cache: false,
            data: {
        		namespace: app,
                path: path
            },
            'dataType': 'json',
            success: function(json) {
                if (json["success"]) {
                
                	$('.lookuped > h1').html(json.data[0]['label']);
                    $('textarea.lookupData').val(json.data[1]);
                } else {
                    var messenger = Splunk.Messenger.System.getInstance();
                    messenger.send('error', "this_string_effectively_means_nothing", _('ERROR - ') + json["messages"][0]["message"] || json);

                }
            }
        });
    }
    
});