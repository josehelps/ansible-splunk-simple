define([
    'jquery',
    'backbone',
    'underscore',
    'd3'
],
function(
    $,
    Backbone,
    _,
    d3
){
    return {
        roundTo: function(x, numDigits){
            numDigits = Math.pow(10, numDigits); 
            return Math.round(x * numDigits)/numDigits;
        },
        hasHorizScroll: function(){
            return $(document).width() > $(window).width()+10;
        }
    };
});