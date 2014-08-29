define([
    'jquery',
    'backbone',
    'underscore',
    'd3',
    'app/views/SwimlaneView',
    'entityUtils',
    'splunk.util'
],
function(
    $,
    Backbone,
    _,
    d3,
    SwimlaneView,
    entityUtils
){
    return Backbone.View.extend({
        tagName: 'g',
        transform: {
            x: 0,
            y: 40
        },
        className: 'swimLanes',
        initialize: function(options){
            this.options = options || {};
            this.parent_svg = d3.select(this.el);
            this.svg = this.parent_svg
                .append(this.tagName)
                .classed(this.className, true);
            this.el = this.svg[0][0];
            
            // time range model
            this.time_range = this.options.model;

            this.shortFormat = d3.time.format('%H:%M');
            this.longFormat = d3.time.format('%m/%d %H:%M');

            // apply default transform
            this.svg.attr('transform', 'translate('+[this.transform.x,this.transform.y]+')');

            // append x axis 
            this.xAxis = this.svg.append('g').classed('xAxis', true);
            this.xAxis.attr('transform', 'translate('+[180,0]+')');

            this.collection.on('reset change:selected reorder:lane_order', _.bind(this.render, this));
            this.time_range.on('change:innerTimeRange', _.bind(this.renderAxis, this));
        },
        /*
         * render all selected swimlanes and reset container height
         * offset is set for translate computations on lanes
         */
        render: function(){
            if (this.collection.length < 1) {
               return this;
            }
            
            var collection = this.collection,
                model0 = collection.at(0),
                height = model0.get('height'),
                channel = model0.get('channel'),
                width = channel.rect.width,
                pref = model0.pref,
                group = pref.get('selected'),
                lanes_order = pref.get('lane_order'),
                lane_order = _.uniq(lanes_order[group]), // If duplicates exist, then prune them
                totalHeight;

            this.width = width;

            this.svg.selectAll('g.swimlane').remove();
            
            // Iterate through the lane order and add the lanes accordingly; skip any that cannot be loaded.
            _.each(lane_order, function(id, offset){
                var model = collection.get(id);
                
                // Don't try to proceed if we couldn't load the model
                if( model ){
	                model.set({offset: offset});
	                this.renderOne(this.el, model);
                }
            }, this);

            // resize swimlanes container height
            totalHeight = this.getTotalHeight();
            this.parent_svg
              .attr('height', totalHeight);

            this.resizeTicks();

            return this;
        },
        getTotalHeight: function(){
            var model0 = this.collection.at(0),
                height;

            if(model0 !== undefined){
                height = model0.get('height');
                return (this.collection.where({selected: true}).length*height)+height;
            }

            return 0;
        },
        resizeTicks: function(){
            var totalHeight = this.getTotalHeight(),
                ticks = this.svg.selectAll('.tick line');

            ticks
                .attr('y2', totalHeight)
                .attr('transform', 'translate(0'+-5+')');
        },
        /*
         * render one swimlane
         */
        renderOne: function(el, model) {
           return new SwimlaneView({
              el: el, 
              model: model
           }).render();
        },
        /*
         * render x axis at the top of swimlanes
         */
        renderAxis: function(model) {
            var innerTimeRange,
                timeFormat,
                timeScale,
                width = this.width || 840,
                xAxis,
                numTicks = 8,
                previousDate,
                self = this,
                timeDiff;

            innerTimeRange = this.time_range.get('innerTimeRange');

            if(innerTimeRange !== undefined){
                timeDiff = this.time_range.calculateTotalInner(innerTimeRange);

                if(timeDiff.minutes < 4 && timeDiff.days < 1 && timeDiff.hours < 1){
                    numTicks = 2;
                }

                timeScale = d3.time.scale()
                              .domain([innerTimeRange.earliest_date, innerTimeRange.latest_date])
                              .range([0,width]);

                xAxis = d3.svg.axis()
                    .scale(timeScale)
                    .orient('top')
                    .ticks(numTicks)
                    .tickFormat(function(currentDate){
                        if(previousDate === undefined){
                            previousDate = currentDate;
                        }

                        if(currentDate.getDay() > previousDate.getDay()){
                            timeFormat = self.longFormat;
                        } else {
                            timeFormat = self.shortFormat;
                        }

                        previousDate = currentDate;
                        return timeFormat(currentDate);
                    })
                    .tickPadding(15);
                
                this.xAxis.call(xAxis);
                this.resizeTicks();
            }
        }
    });
});
