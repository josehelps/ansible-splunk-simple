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
        initialize: function(options){
            this.options = options || {};
            this.width = this.options.width;
            this.height = this.options.height;
            this.svg = this.options.svg;
            this.time_range = this.options.time_range;

            this.linechart = d3.select(this.el);
            this.id = _.uniqueId('TimeRangeLinegraphView-');
            this.clipId = this.id + '-clip';

            this.time_range.on('change:outerTimeRange', _.bind(this.render, this));

            // If the clippath is not always there, bad things happen
            this.clipPath = this.linechart.append('clipPath')
                .attr('id', this.clipId);

            this.loadingIndicator = this.linechart.append("use")
                .attr('xlink:href', '#loader')
                .attr('transform', 'scale(0.5) translate(700, 0)')
                .attr('width', 200)
                .style('visibility', 'hidden');

            this.model.on('change:data', this.render, this);
            this.model.on('change:loading', this.onLoading, this);
        },
        getClipId: function(){
            return this.clipId;
        },
        clear: function(){
            this.linechart.selectAll("path").remove();
            this.clipPath.selectAll("path").remove();
        },
        onLoading: function(){
            var loading = this.model.get('loading');
            if(loading){
                this.clear();
                this.loadingIndicator.style('visibility', 'visible');
            } else {
                this.loadingIndicator.style('visibility', 'hidden');
            }
        },
        render: function(){
            var data,
                earliest = this.model.get('earliest'),
                latest = this.model.get('latest'),
                yScale,
                xScale,
                lineGen,
                areaGen;

            data = this.model.get('data');
            if(data){
                yScale = d3.scale.linear()
                    .domain([this.model.get('min'), this.model.get('max')])
                    .range([this.height, 0]);

                xScale = d3.time.scale()
                    .domain([earliest, latest])
                    .range([0, this.width]);

                lineGen = d3.svg.line()
                    .x(function(d) { 
                        return xScale(d.get('_time').getTime()); 
                    })
                    .y(function(d) { 
                        return yScale(d.get('numEvents')); 
                    });

                areaGen = d3.svg.area()
                    .x(function(d) { return xScale(d.get('_time').getTime()); })
                    .y0(this.height)
                    .y1(function(d) { return yScale(d.get('numEvents')); });

                this.linechart.append("path")
                      .attr("class", "line")
                      .attr("clip-path", "url(#"+this.clipId+")")
                      .attr("d", lineGen(data.models));

                this.clipPath.append('path')
                    .attr('d', areaGen(data.models));

                this.linechart.append("path")
                    .attr('class', 'area')
                    .attr('clip-path', 'url(#'+this.clipId+')')
                    .attr('id', this.clipId)
                    .attr('d', areaGen(data.models));
            }
        }

    });
});
