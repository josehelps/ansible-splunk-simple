define([
     "jquery",
     "underscore",
     "backbone",
     "contrib/text!app/templates/SignBoardRow.html",
     "contrib/text!app/templates/SignBoardVal.html",
     "contrib/text!app/templates/SignBoardToggle.html"
 
], function(
     $,
     _,
     Backbone,
     SignBoardRowTemplate,
     SignBoardValTemplate,
     SignBoardToggleTemplate
) {
     return Backbone.View.extend({
         initialize: function() {
             this.model.on('ready:bodyData', _.bind(this.render, this));
             this.model.on('clearAll', _.bind(this.emptyAll, this));
         },
         emptyAll: function() {
             this.$el.empty();
         },
         render: function() {
             var keys = _.sortBy(_.keys(this.model.attributes), function(x) {return x;});

             this.emptyAll();
             _.each(keys, function(k) {
                 var $val,
                     item = this.model.get(k),
                     maxShown = 2,
                     $rightSide,
                     showToggleHandle = false,
                     numHiddenItems = 0;

                 if(k === 'meta' || k==='count' || k==='_time'){
                     return;
                 }

                 $template = $(_.template(SignBoardRowTemplate, {name: k}));
                 $rightSide = $template.find(".signBoardRowRight");
                 this.$el.append($template);

                 _.each(item, function(itemName, i){
                     $val = _.template(SignBoardValTemplate, {val: itemName});
                     if(i < maxShown){
                         $rightSide.find(".alwaysVisible").append($val);
                     } else {
                         $rightSide.find(".toggleable").append($val);
                         showToggleHandle = true;
                         numHiddenItems++;
                     }
                 });

                 if(showToggleHandle){
                     $rightSide.append(_.template(SignBoardToggleTemplate, {numHiddenItems: numHiddenItems}));
                 }

             }, this);

             return this;
          }
     });
});
