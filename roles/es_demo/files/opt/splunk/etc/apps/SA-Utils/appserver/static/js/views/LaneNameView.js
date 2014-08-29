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
    return Backbone.View.extend({
        className: 'lane_label',
        tagName: 'g',
        initialize: function() {
            this.svg = d3.select(this.el)
                .append(this.tagName)
                .classed(this.className, true);
            this.el = this.svg[0][0];
        },
        render: function() {
            var label = this.model.get('label'),
                height = this.model.get('height'),
                title = this.model.get('title');

            this.svg.append('rect')
              .classed(label.rect.className, true)
              .attr('x', label.rect.x)
              .attr('y', label.rect.y)
              .attr('height', height)
              .attr('width', label.rect.width)
              .attr('fill', label.rect.fill)
              .attr('stroke', label.rect.stroke);

            this.svg.append('rect')
              .attr('class', 'lane_label_border_bottom')
              .attr('x', label.rect.x)
              .attr('y', label.rect.y+height)
              .attr('height', 1)
              .attr('width', label.rect.width-1)
              .attr('stroke', '#828282');

           this.svg.append('text')
              .classed(label.text.className, true)
              .attr('dx', label.text.dx)
              .attr('dy', label.text.dy)
              .attr('fill', label.text.fill)
              .style('font-family', "'helvetica neue',helvetica,arial")
              .text(title);

           return this;
        }
    });
});
