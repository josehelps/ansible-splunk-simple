Splunk.namespace("Module");
Splunk.Module.TA_Windows_FTR= $.klass(Splunk.Module, {

    NOT_WINDOWS_WARN: '<p class="popupText">Splunk has detected that the server operating system is not Windows.</p><p class="popupText">The Splunk Add-on for Windows 
    can only be installed and configured on Windows operating systems.</p><p class="popupText">Please click on Manage Apps to disable the Splunk Add-on for Windows and restart Splunk.</p>', 

    initialize: function($super, container) {
        $super(container);
        this.logger = Splunk.Logger.getLogger("ta_windows_ftr.js");
        this.messenger = Splunk.Messenger.System.getInstance();
        this.popupDiv = $('.ftrPopup', this.container).get(0);
        this.getResults();
    },

    renderResults: function(response, turbo) {
        if (response.is_windows || response.is_windows===false) {
            this.popupDiv.innerHTML = this.NOT_WINDOWS_WARN;
            this.popup = new Splunk.Popup(this.popupDiv, {
                cloneFlag: false,
                title: _("Unsupported Operating System"),
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
