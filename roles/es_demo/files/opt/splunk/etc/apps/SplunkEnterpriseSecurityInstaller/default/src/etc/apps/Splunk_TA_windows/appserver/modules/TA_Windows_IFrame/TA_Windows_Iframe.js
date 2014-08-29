Splunk.namespace("Module");
Splunk.Module.TA_Windows_IFrame = $.klass(Splunk.Module.IFrameInclude, {

    initialize: function($super, container){
        $super(container);
    },

    onLoad: function(event) {
        this.logger.info("TA_Windows_IFrame onLoad event fired.");
         
        this.resize();
        this.iframe.contents().find("body").click(this.resize.bind(this));
    },
            
    resize: function() {
        this.logger.info("TA_Windows_IFrame resize fired.");
    		    
        var height = this.getHeight();
        if(height<1){
            this.iframe[0].style.height = "auto";
            this.iframe[0].scrolling = "auto";
        } else {
            this.iframe[0].style.height = height + this.IFRAME_HEIGHT_FIX + 40 + "px";
            this.iframe[0].scrolling = "yes";
        }
                
    }
     	
});
