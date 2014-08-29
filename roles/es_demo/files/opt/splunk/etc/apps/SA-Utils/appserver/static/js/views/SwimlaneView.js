define([
    'jquery',
    'backbone',
    'underscore',
    'd3',
    'app/models/LaneName',
    'app/views/ChannelView',
    'app/views/LaneNameView'
],
function(
    $,
    Backbone,
    _,
    d3,
    LaneName,
    ChannelView,
    LaneNameView
){
    return Backbone.View.extend({
        className: 'swimlane',
        tagName: 'g',
        initialize: function() {
            this.svg = d3.select(this.el)
                .append(this.tagName)
                .classed(this.className, true)
                .attr('data-id', this.model.id);

            this.el = this.svg[0][0];
        },
        render: function() {
            new LaneNameView({
              el: this.el, 
              model: this.model 
            }).render();

            new ChannelView({
              el: this.el, 
              model: this.model
            });

            // wire up behaviors after render 
            this.initBehaviors();

            return this;
        },
        initBehaviors: function() {
            var getOrigin = this.getOrigin,
                addGripPad = this.addGripPad,
                onDrag = this.onDrag,
                onDragEnd = this.onDragEnd,
                last_y = 0,
                model = this.model,
                height = this.model.get('height'),
                label = this.model.get('label'), 
                length = this.model.collection.where({selected:true}).length,
                offset = this.model.get('offset'),
                detectRightClick = this.isRightClick,
                isRightClick = false,
                translate = this.getTranslate(),
                this_svg = this.svg,
                label_group = this.svg.select('.lane_label'),
                total_y = length*height,
                offset_y = offset*height,
                max_y = total_y-height,
                min_y = 0-offset_y,
                x = label.rect.x,
                y = label.rect.y;

            // apply default translation
            this.svg.attr('transform', translate);

            // lane mouseover behaviors
            label_group
              .on('mouseover', function() {
                addGripPad(this, x, y, height);
              })
              .on('mouseout', function() {
                this_svg.selectAll('line.grip_handle_line').remove();
            });
            
            // drag behaviors
            label_group.call(
                d3.behavior.drag()
                    .origin(getOrigin)
                    .on('dragstart', function() {
                      isRightClick = detectRightClick(d3.event.sourceEvent);
                      if (isRightClick) {
                          return;
                      }
                      addGripPad(this, x, y, height);
                    })
                    .on('drag', function() {
                      if (isRightClick) {
                          return;
                      }
                      last_y = onDrag(this, min_y, max_y, offset_y);
                    })
                    .on('dragend', function() {
                      if (isRightClick) {
                          return;
                      }
                      onDragEnd(this_svg, this, last_y, model);
               })
            );
        },
        isRightClick: function(sourceEvent) {
            if (sourceEvent.which !== 1) {
                return true;
            } else if (sourceEvent.ctrlKey === true) {
                return true;
            }
            return false;
        },
        /*
         * get translated origin for swimlane of label being dragged
         */
        getOrigin: function() {
            var t = d3.select(this.parentNode),
                tf = d3.transform(t.attr('transform')),
                x = t.attr('x'),
                y = t.attr('y');
            return {
                x: x+tf.translate[0],
                y: y+tf.translate[1]
            }; 
        },
        /*
         * get default translation for swimlane based on offset and height
         */
        getTranslate: function() {
            return 'translate(0,'+(this.model.get('offset')*this.model.get('height'))+')';
        }, 
        /*
         * adds grip pad to swimlane label for mouseover and drag
         */
        addGripPad: function(node, x, y, height) {
            var this_svg = d3.select(node),
                lines = this_svg 
                  .selectAll('line.grip_handle_line')
                  .data([0,1,2]);
          
            lines
              .enter()
                .append('line') 
                .classed('grip_handle_line', true)
                .style('fill', '#6E6E6E')
                .style('stroke', '#CDCDCD')
                .style('stroke-width', 1)
                .style('stroke-dasharray', "2 ,2")
                .attr('x1', function(d) { return x+4+d*3; })
                .attr('x2', function(d) { return x+4+d*3; })
                .attr('y1', function(d) { return y+2; })
                .attr('y2', function(d) { return y+height-2; }); 

            lines
              .exit().remove();
        },  
        /*
         * handler for swimlane label drag events
         */
        onDrag: function(node, min_y, max_y, offset_y) { 
            var x = Math.min(d3.event.x, 20),
                y = Math.min(max_y-offset_y, Math.max(min_y, d3.event.y-offset_y));

            // append the swimlane to the parent group so it will be on top
            node.parentNode.parentNode.appendChild(node.parentNode);

            // translate the label to the new y coordinate
            d3.select(node) 
                .attr('transform', 'translate('+ [x, y] +')');

            // return the y coordinate for the next drag event
            return y;
        },  
        /*
         * determine if swimlane needs to be repositioned
         * else put the label back where it started
         */
        onDragEnd: function(this_svg, node, y, model) { 
            var group = model.pref.get('selected'),
                height = model.get('height'),
                length = model.collection.where({selected: true}).length,
                lanes_order = model.pref.get('lane_order') || {},
                lane_order = lanes_order[group] || [],
                max = length*height,
                offset = model.get('offset'),
                scale = d3.scale.linear()
                    .domain([0,max])
                    .range([0,length]),
                index = Math.round(y/height);             
            
            // remove grip pad
            this_svg.selectAll('line.grip_handle_line').remove();
   
            // if lane was dropped in the same place, put it back 
            // else change the lane_order and trigger a reorder event
            if (index===0) {
                d3.select(node).attr('transform', 'translate('+ [0, 0]+')');
            } else {
                // remove from lane_order and add back at new index
                // which is calculated as original offset + new index
                // new index can be positive or negative
                lane_order = _.without(lane_order, model.id);
                lane_order.splice(offset+index, 0, model.id); 

                // silently set the new lane_order and trigger a reorder event 
                lanes_order[group] = lane_order;
                model.pref.set(
                  {lane_order: lanes_order},
                  {silent: true}
                );
                model.trigger('reorder:lane_order', model, lane_order);
            }
        }  
    });
});