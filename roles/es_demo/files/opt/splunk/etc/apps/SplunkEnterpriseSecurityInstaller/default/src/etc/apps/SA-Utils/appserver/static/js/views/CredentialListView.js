require.config({
    paths: {
        credential_editor_view: '../app/SA-Utils/js/views/CredentialEditorView',
        datatables: "../app/SA-Utils/js/lib/DataTables/js/jquery.dataTables",
        bootstrapDataTables: "../app/SA-Utils/js/lib/DataTables/js/dataTables.bootstrap",
        text: "../app/SA-Utils/js/lib/text",
        console: '../app/SA-Utils/js/util/Console'
    },
    shim: {
        'bootstrapDataTables': {
            deps: ['datatables']
        }
    }
});

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "datatables",
    "credential_editor_view",
    "bootstrapDataTables",
    "css!../app/SA-Utils/js/lib/DataTables/css/jquery.dataTables.css",
    "css!../app/SA-Utils/js/lib/DataTables/css/dataTables.bootstrap.css",
    "css!../app/SA-Utils/css/CredentialList.css",
    "css!../app/SA-Utils/css/SplunkDataTables.css",
    "console"
], function(
    _,
    Backbone,
    mvc,
    $,
    SimpleSplunkView,
    dataTable,
    CredentialEditorView
){
    // Define the custom view class
    var CredentialListView = SimpleSplunkView.extend({
        className: "CredentialListView",

        initialize: function() {
            this.result = null;
            
            options = this.options || {};
            this.default_app = options.default_app;
            
            this.listenTo(Backbone, "list-refresh-event", function() {
                $("#credential-editor").modal("hide");
                this.refreshResults();
            });
            $("#credential-new-btn").click(function(event){
                this.newCredential();
            }.bind(this));
            console.log("CredentialListView::initialize");
        },
        
        events: {
            "click #editLink": "editCredential"
            //Cannot put this here because the button is not within this view's EL
            //Backbone binds the event handlers to the view's this.el using delegate
            //"click #credential-new-btn": "newCredential"
        },
        
        /**
         * Render the modal dialog for editing amn existing credential.
         */
        editCredential: function(evt) {
            username = $(evt.currentTarget).attr('user-name');
            realm = $(evt.currentTarget).attr('realm');
            app = $(evt.currentTarget).attr('app');
                        
            console.log("username:" + $(evt.currentTarget).attr('user-name') +
                        " realm:" + $(evt.currentTarget).attr('realm'));

            //make input!!
            var input = {"username":username, "realm":realm, "isEdit":true, "app":app};

            //call editor view with the input
            var editorView = new CredentialEditorView(input);

            //append editor modal to DOM
            $("#credential_modal").html(editorView.render().el);

            //display editor modal - NOTE: id="credential-editor" is defined in CredentialManager.html template.
            $("#credential-editor").modal();
        },
        
        /**
         * Render the modal dialog for adding a new credential.
         */
        newCredential: function() {
            //make input!!
            var input = {"username":"", "realm":"", "isEdit":false, "app": this.default_app};

            //call editor view with the input
            var editorView = new CredentialEditorView(input);

            //append editor modal to DOM
            $("#credential_modal").html(editorView.render().el);

            //display editor modal - NOTE: id="credential-editor" is defined in CredentialManager.html template.
            $("#credential-editor").modal();
        },
        
        /**
         * Render the list or a dialog if the user doesn't have permission.
         */
        render: function() {
            console.log("before-render:fetch:result:" + JSON.stringify(this.result));
            this.fetchCredentials();
            console.log("after-render:fetch:result:" + JSON.stringify(this.result));
            
            if( this.result === null ){
                $('#credential-new-btn').hide();
                return this;
            }
            else{
                $('#credential-new-btn').show();
            }

            tableData = this.result;
            
            for (var i=0; i<tableData.length; i++) {
                if (tableData[i] instanceof Array) {
                    username = tableData[i][0];
                    realm = tableData[i][1];
                    app = tableData[i][2];
                    tdActionLink = '<a href="#" user-name="' + username + '" realm="' +  realm + '" app="' +  app + '" id="editLink">Edit</a>';
                                   //future reference, we can add a delete link once there's a related endpoint
                                   //'&nbsp;&nbsp;|&nbsp;&nbsp;' + 
                                   //'<a href="#" user-name="' + username + '" realm="' +  realm + '" id="deleteLink">Delete</a>';
                    tableData[i] = tableData[i].concat(tdActionLink);
                }
                
              //else: do nothing, this is not a table row.
            }

            this.$el.html( '<table cellpadding="0" cellspacing="0" border="0" class="table table-striped display" id="example"></table>' );
            $('#example').dataTable( {
              "aaData": tableData,
              "iDisplayLength": 25,
              "sDom": "<'row-fluid'<'span6'T><'span6'f>r>t<'row-fluid'<'span6'i><'span6'p>>",
              "aoColumns": [
                {"sTitle":"Username"},
                {"sTitle":"Realm"},
                {"sTitle":"Application"},
                {"sTitle":"Action"}
              ]                            
            } );
            
            console.log("CredentialListView::render");  
            return this;
        },
        
        /**
         * Fetch Credentials
         */
        fetchCredentials: function() {
            
            var params = new Object();
            params.output_mode = 'json';
            
            var uri = Splunk.util.make_url('/custom/SA-Utils/credential_management_editor/list');
            uri += '?' + Splunk.util.propToQueryString(params);

            jQuery.ajax({
                url:  uri,
                type:    'POST',
                cache:   false,
                async:   false,
                success: function(jsonResult) {
                    if (jsonResult["success"])  {
                        this.result = jsonResult.data[0];
                    }
                    
                    else {
                        var message = jsonResult["messages"][0]["message"];
                        this.$el.html('<div class="alert" style="background-color: rgb(250, 234, 230); border-color: rgb(216, 93, 60); color: rgb(216, 93, 60); display: block;" id="warning_message">' + message + '</div>');
                    }
                }.bind(this),
                
                error: function(jqXHR,textStatus,errorThrown) {
                    console.warn("Error Fetching Credentials");
                    alert("Error Fetching Credentials");
                } 
            });
        },
        
        /**
         * Fetch the credentials.
         */
        refreshResults: function () {
            this.fetchCredentials();
            this.render();
        }
    });
    
    return CredentialListView;
});
