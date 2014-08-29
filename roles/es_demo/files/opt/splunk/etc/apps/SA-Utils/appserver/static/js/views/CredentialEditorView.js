require.config({
    paths: {
        text: "../app/SA-Utils/js/lib/text",
        jquery_validate: "../app/SA-Utils/js/lib/jquery.validate",
        console: '../app/SA-Utils/js/util/Console'
    },
    shim: {
        'jquery_validate': {
            deps: ['jquery']
        }
    }
});

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "text!../app/SA-Utils/js/templates/CredentialEditor.html",
    "css!../app/SA-Utils/css/CredentialEditor.css",
    "jquery_validate",
    "console"
], function(
    _,
    Backbone,
    mvc,
    $,
    SimpleSplunkView,
    CredentialEditorTemplate,
    JqueryValidate
) { 
    // Define the custom view class
    var CredentialEditorView = SimpleSplunkView.extend({
        className: "CredentialEditorView",
        apps: null,
        
        initialize: function() {
            //this.formValidator();
            console.log("CredentialEditorView::initialize");
            $('#progressModal')
                .ajaxStart(function() {
                    $("#progress-bar").show();
                })
                .ajaxStop(function() {
                    $("#progress-bar").hide();
                });
            
        },
        
        formValidator: function () {
        
            $(".form-horizontal").validate({
                rules: {
                
                    // weird jquery/JS error dis-allows hyphens in property names. We need to quote these.
                    "validate-username": {
                        required: true,
                        usernameCustomValidation: true
                    },
                    "validate-realm": {
                        required: false,
                        realmCustomValidation: true                        
                    },
                    "validate-password": {
                        required: true,
                        passwordValidation: true
                    }
                },
                messages: {
                    "validate-username": {
                        required: "* Username is required"
                    },
                    "validate-realm": {
                        required: "* Realm is required"
                    },
                    "validate-password": {
                        required: "* Password is required"
                    }
                }
            });

            $.validator.addMethod("usernameCustomValidation",
                function(value, element) {
	                existsForwardSlash = /[\/]/.test(value);
	                existsWhiteSpace = /[\s]/.test(value);
	                return (!existsForwardSlash && !existsWhiteSpace);
                },
                "* Username cannot contain '/' or space characters"
            );
            
            $.validator.addMethod("realmCustomValidation",
                function(value, element) {
	                existsForwardSlash = /[\/]/.test(value);
	                existsWhiteSpace = /[\s]/.test(value);
	                return (!existsForwardSlash && !existsWhiteSpace);
                },
                "* Realm cannot contain '/' or space characters"
            );

            $.validator.addMethod("passwordValidation",
                function(value, element) {
	                leadingSpace = /^\s/.test(value);
	                trailingSpace = /\s$/.test(value);
	                return (!leadingSpace && !trailingSpace);
                },
                "* Passwords cannot contain leading or trailing whitespace"
            );
        },

        events: {
            "click #save-changes": "saveChanges"
        },

        render: function() {
            console.log("editor::render::" + this.$el.attr('id'));
            
            args = _.extend({apps: this.getApps(), 'app': null}, this.options);
            
            this.$el.html(_.template(CredentialEditorTemplate, args));
            return this;
        },
        
        getApps: function(){
        	
        	if( this.apps !== null ){
        		return this.apps;
        	}
        	
            $.ajax({
                type: "GET",
                url: Splunk.util.make_url("/splunkd/services/apps/local?output_mode=json&count=-1"),
                async: false,
                success: function(data) {
                	apps = [];
                	
                	for(var c = 0; c < data.entry.length; c++){
                		apps.push(data.entry[c]['name']);
                	}
                	
                    this.apps = apps;
                }.bind(this)
            });
            
            return this.apps;
        	
        },
        
        saveChanges: function() {
        
            usernameVal = $("#input-username").val();
            realmVal = $("#input-realm").val();
            passVal = $("#input-password").val();
            appVal = $("#input-app").val();
            
            $("#warning_message").hide();
            
            //set up the form validator
            this.formValidator();
            
            var isValid = this.validateInput(usernameVal, realmVal, passVal);
            
            if (isValid) {            
                var params = new Object();
                params.output_mode = 'json';
                var uri = "";
                if (this.options.isEdit) {
                    uri = Splunk.util.make_url('/custom/SA-Utils/credential_management_editor/update');
                }
                else {
                    uri = Splunk.util.make_url('/custom/SA-Utils/credential_management_editor/create');
                }
                uri += '?' + Splunk.util.propToQueryString(params);

                jQuery.ajax({
                    url:  uri,
                    type:    'POST',
                    cache:   false,
                    async:   false,
                    data: {"user": usernameVal,
                           "realm": realmVal,
                           "password": passVal,
                           "app": appVal,
                           "owner": "admin"},
                    success: function(jsonResult) {
                        if (jsonResult["success"])  {
                            console.log("change saved!");
                            this.result = jsonResult.data[0];
                            Backbone.trigger("list-refresh-event");
                        }
                    
                        else {
                        	$("#warning_message").text(jsonResult["messages"][0]["message"]).show();
                        }
                    }.bind(this),
                
                    error: function(jqXHR,textStatus,errorThrown) {
                        console.warn("Error Updating Credentials");
                        alert("Error Updating Credentials");
                    } 
                });
            }
            //else: do nothing, validateInput will display error messages
        },
        
        validateInput: function(user, realm, password) {
            isValid = false;
            //isEdit is passed into view as this.options from the credential list view
            if (this.options.isEdit) {
                //only validate the password field since edit only allows editing the password
                isValid = true;
            }
            else {
                //validate all fields
                isValid = true;            
            }
            
            //return isValid;
            return $(".form-horizontal").valid();
        }

    });
    
    return CredentialEditorView;
});
