define([
     "jquery",
     "underscore",
     "backbone",
     "contrib/text!app/templates/AttributesTable.html"
], function(
     $,
     _,
     Backbone,
     Template
) {
     var unneeded = ["identity_tag", "tag", "key", "asset_id", "asset_tag", "asset", "identity", "count"];
     return Backbone.View.extend({
          initialize: function(options) {
               this.options = options || {};
               this.model = this.options.model;
               this.renderLoader();

               this.render = _.debounce(this._render, 100);
               this.model.on("change", _.bind(this.render, this));
               this.undefinedEntity = _.debounce(this._undefinedEntity, 100);
               this.model.on("entity:undefined", this.undefinedEntity, this);
               this.unfoundEntity = _.debounce(this._unfoundEntity, 100);
               this.model.on("entity:notFound", this.unfoundEntity, this);
               this.invalidEntity = _.debounce(this._invalidEntity, 100);
               this.model.on("entity:invalid", this.invalidEntity, this);
                this.model.on("setEntityName", _.bind(this.showLoader, this));
          },
          renderLoader: function() {
                var width = this.$el.width();
                this.svg = d3.select("svg.loadingIcon");
                this.loadingIcon = this.svg.append('g')
                    .attr('transform', 'translate(' + (width / 2 - 150) + ',5)');

                this.loadingIcon.append('use')
                    .attr('xlink:href', '#loader')
                    .attr('transform', 'scale(0.5)')
                    .attr('width', 200);
                
                this.loadingIcon.append('text')
                    .text("Loading...")
                    .attr('transform', 'translate(50,12)');
          },
          showLoader: function() {
                this.$(".attributes").hide();
                this.svg.style("display", "block");
          },
          hideLoader: function() {
                this.$(".attributes").show();
                this.svg.style("display", "none");
          },
          _render: function() {
               var value = this.model.value,
                    detail = this.model.get("asset") || this.model.get("identity") || [],
                    attrs = _.omit(this.model.attributes, unneeded);

                this.hideLoader();
               this.$(".attributes").html(_.template(Template, {
                    value: value,
                    detail: detail,
                    attrs: attrs
               }));
               this.spaceTable();
          },
          _undefinedEntity: function() {
                this.hideLoader();
               this.$(".attributes").text("Entity name is not specified.  Search for " + this.model.fieldName + " to populate.");
          },
          _unfoundEntity: function() {
                this.hideLoader();
               this.$(".attributes").text(this.model.value + " is not a known " + this.model.fieldName + ".");
          },
          _invalidEntity: function() {
                this.hideLoader();
               this.$(".attributes").text(this.model.value + " is not a known " + this.model.fieldName + ".");
          },
          spaceTable: function() {
               var width = this.$(".attributes").width() / 4;
               this.$("td").width(width);
          }
     });
});
