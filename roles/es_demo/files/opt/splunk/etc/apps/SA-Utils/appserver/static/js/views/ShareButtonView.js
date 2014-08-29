define([
    'jquery',
    'backbone',
    'underscore',
    'd3',
    'contrib/text!app/templates/ShareButtonPopup.html',
    'backbone-mediator'
],
function(
    $,
    Backbone,
    _,
    d3,
    ShareButtonPopupTemplate
){
    return Backbone.View.extend({
        initialize: function(){
            var self = this,
                $popUp;

            this.popUpVisible = false;

            $popUp = $(_.template(ShareButtonPopupTemplate, {}));
            this.$el.after($popUp);

            /*
            Clicks do not bubble up -
            doing so would close the popup.
            */

            $popUp.on('click', function(e){
                e.stopPropagation();
            });

            this.$el.on('click', function(e){
                var url;

                e.stopPropagation();
                url = self.model.getUrl();
                $popUp.find('input').val(url);
                
                if(self.popUpVisible){
                    $popUp.hide();
                    self.popUpVisible = false;
                } else {
                    $popUp.show();
                    self.popUpVisible = true;
                }
            });

            $(window).on('click', function(){
                if(self.popUpVisible){
                    $popUp.hide();
                    self.popUpVisible = false;
                }
            });
        },
        
        render: function(){
        }
    });
});