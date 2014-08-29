// Copyright 2011 Splunk, Inc.                                      
//
//   Licensed under the Apache License, Version 2.0 (the "License");         
//   you may not use this file except in compliance with the License.        
//   You may obtain a copy of the License at                                 
//                                                                           
//       http://www.apache.org/licenses/LICENSE-2.0                          
//                                                                           
//   Unless required by applicable law or agreed to in writing, software     
//   distributed under the License is distributed on an "AS IS" BASIS,       
//   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//   See the License for the specific language governing permissions and     
//   limitations under the License.    

Splunk.namespace("Module");
Splunk.Module.TA_Unix_FTR= $.klass(Splunk.Module, {

    COLLISION_WARN: '<p class="popupText">The app "%s" is installed on this system.</p><p class="popupText">Splunk for Unix Technical Add-on and the "%s" app cannot exist together on the same Splunk instance.</p><p class="popupText">Please click on Manage Apps to disable the conflicting app, then remove "%s" from $SPLUNK_HOME/etc/apps and restart Splunk.</p>',
    
    initialize: function($super, container) {
        $super(container);
        this.logger = Splunk.Logger.getLogger("ta_unix_ftr.js");
        this.messenger = Splunk.Messenger.System.getInstance();
        this.popupDiv = $('.ftrPopup', this.container).get(0);
        this.getResults();
    },

    renderResults: function(response, turbo) {
        if (response.is_conflict && response.is_conflict===true) {
            this.popupDiv.innerHTML = this.COLLISION_WARN.replace(/%s/g, response.app_label);
            this.popup = new Splunk.Popup(this.popupDiv, {
                cloneFlag: false,
                title: _("Unsupported Configuration"),
                pclass: 'configPopup',
                buttons: [
                    {
                        label: _("Manage Apps"),
                        type: "primary",
                        callback: function(){
                            Splunk.util.redirect_to('manager/' + Splunk.util.getCurrentApp() + '/apps/local');                                                    
                        }.bind(this)
                    }       
                ]       
           });      
        } 
    }

});

