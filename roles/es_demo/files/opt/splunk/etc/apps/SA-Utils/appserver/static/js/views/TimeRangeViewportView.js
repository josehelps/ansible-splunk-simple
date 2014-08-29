define([
    'jquery',
    'backbone',
    'underscore',
    'd3',
    'entityUtils'
],
function(
    $,
    Backbone,
    _,
    d3,
    entityUtils
){
    return Backbone.View.extend({
        initialize: function(options){
            this.options = options || {};
            this.centerDragOrigin = 0;
            this.dragOffset = 0;
            this.svg = this.options.svg;
            this.width = this.options.width;
            this.clipId = this.options.clipId;

            this.tooltip = d3.select('#time_tooltip');

            this.element_map = this.getElementMap();
            this.renderInnerTimeRangeInfo = _.throttle(this._renderInnerTimeRangeInfo, 16);
            this.element_map.borderTopRight.attr('x2', this.width);
            
            // This must be hidden at first to avoid a flash of unstyled content
            this.element_map.highlight.attr('clip-path', 'url(#'+ this.options.clipId +')')
                .style('visibility', 'hidden');

            this.gripperWidth = this.element_map.leftGripper.attr('width');

            this.innerTimeRangeScale = d3.scale.linear()
                .domain([0, 100])
                .range([0, this.width]);

            this.setupDrag();

            this.model.on('change:outerTimeRange', function(){
                this.renderOuterTimeline();
            }, this);

            this.model.on('change:innerPos', function(){
                this.setGripperPosition();
                this.renderInnerTimeRangeInfo();
            }, this);

        },
        getGripperDiff: function() {
           var diff = Math.abs(this.leftGripperX-this.rightGripperX);
           if (isNaN(diff)){
               diff = 0;
           }
           return diff;
        },
        renderToolTip: function(timeRange, duration) {
            var output = "earliest: " + timeRange.earliest_date +
                         "<br/>latest: " + timeRange.latest_date + 
                         "<br/>duration: " + duration;
            return output;
        },
        setupDrag: function() {
            var leftDrag = this.handleLeftGripperDrag,
                rightDrag = this.handleRightGripperDrag,
                centerDrag = this.handleCenterDrag,
                dragOffset = this.dragOffset,
                onDragStart = this.onDragStart,
                centerDragOrigin = this.centerDragOrigin,
                model = this.model, 
                width = this.width, 
                gripperWidth = this.gripperWidth,
                innerTimeRangeScale = this.innerTimeRangeScale,
                tooltip = this.tooltip,
                renderToolTip = this.renderToolTip,
                elements = this.element_map,
                formatTotalTime = this.formatTotalTime;

            d3.select(this.el).select('.grippers')
                .attr('transform', 'translate(0,14)');

            this.element_map.leftGripper.call(
                d3.behavior.drag()
                  .on("drag", function() {
                    leftDrag(model, width, gripperWidth, innerTimeRangeScale);
                  }
                )
            );
            this.element_map.rightGripper.call(
                d3.behavior.drag()
                  .on("drag", function() {
                    rightDrag(model, width, gripperWidth, innerTimeRangeScale);
                  }
                )
            );
            this.element_map.innerTimeRangeInfo.select('.totalTime rect').call(
                d3.behavior.drag()
                  .on('drag', function() {
                      centerDrag(model, width, innerTimeRangeScale, dragOffset, elements);
                  })
                  .on('dragstart', function() {
                      centerDragOrigin = d3.event.sourceEvent.clientX;
                      if(model.get('swapped')){
                        dragOffset = centerDragOrigin - elements.rightGripper.node().getBoundingClientRect().left;
                      } else {
                        dragOffset = centerDragOrigin - elements.leftGripper.node().getBoundingClientRect().left;
                      }
                  })
            );
            this.element_map.highlight.call(
                d3.behavior.drag()
                  .on('drag', function() {
                      centerDrag(model, width, innerTimeRangeScale, dragOffset, elements);
                  })
                  .on('dragstart', function() {
                      centerDragOrigin = d3.event.sourceEvent.clientX;
                      dragOffset = centerDragOrigin - elements.leftGripper.node().getBoundingClientRect().left;
                  })
            );

            var self = this;
 
            // inner time range info mouseover
            this.element_map.innerTimeRangeInfo
                .on('mouseover', function() {
                    var enableTooltip = model.get('enableTooltip');

                    if (enableTooltip===false) {
                        return;
                    }

                    tooltip.transition()
                        .duration(200)
                        .style({
                          'opacity': 0.8,
                          'visibility': 'visible'
                        });
                })
                .on("mousemove", function(d, i){
                    var coords = this.getBoundingClientRect(),
                        left = coords.left-70,
                        $this = $(this),
                        top,
                        totalInnerTime = model.get('totalInnerTime'), 
                        innerTimeRange = model.get('innerTimeRange'),
                        duration = formatTotalTime(totalInnerTime),
                        enableTooltip = model.get('enableTooltip'),
                        isFF = navigator.userAgent.toLowerCase().indexOf('firefox') > -1,
                        isWindows = window.navigator.platform.toLowerCase().indexOf('win') > -1,
                        extraOffset = 40;

                    if (enableTooltip===false) {
                        return;
                    }

                    tooltip.style("left", left + "px")
                        .html(function(){return renderToolTip(innerTimeRange, duration);})
                        .style("text-align", "left");

                    top = coords.top + $(document).scrollTop() + extraOffset;
                    tooltip.style("top", top + "px");
                })
                .on("mouseout", function(d, i){
                    tooltip.transition()
                        .duration(200)
                        .style({
                          'opacity': 1e-6,
                          'visibility': 'hidden'
                        });
            });

        },
        handleLeftGripperDrag: function(model, width, gripperWidth, innerTimeRangeScale){
            var x = Math.max(0, Math.min(width - gripperWidth, d3.event.x));
            model.updateGrippers({'left': innerTimeRangeScale.invert(x)});
        },
        handleRightGripperDrag: function(model, width, gripperWidth, innerTimeRangeScale){
            var x = Math.max(0, Math.min(width - gripperWidth, d3.event.x));
            model.updateGrippers({'right': innerTimeRangeScale.invert(x)});
        },
        handleCenterDrag: function(model, width, innerTimeRangeScale, dragOffset, elements){
            var dx,
                x1,
                x2,
                current,
                distToEnd,
                mouseCurrentX,
                xOffset,
                domSpaceX1,
                distToStart;

            current = model.get('innerPos');
            mouseCurrentX = d3.event.sourceEvent.clientX;
            domSpaceX1 = elements.leftGripper.node().getBoundingClientRect().left;

            x1 = innerTimeRangeScale(current.left);
            x2 = innerTimeRangeScale(current.right);

            // Compensate for the starting location of the mouse within the
            // element being dragged.
            dx = d3.event.sourceEvent.clientX - (domSpaceX1 + dragOffset);

            distToStart = x1;
            distToEnd = width - x2;

            // This keeps the box's size the same,
            // while keeping the box inside the boundaries
            if(dx < 0){
                if(distToStart + dx < 0){
                    dx = -distToStart;
                }
            } else {
                if(distToEnd - dx < 0){
                    dx = distToEnd;
                }
            }

            // Avoid any unnecesary updates
            if(dx !== 0){
                x1 = innerTimeRangeScale(current.left) + dx;
                x2 = innerTimeRangeScale(current.right) + dx;
                model.updateGrippers({
                  right: innerTimeRangeScale.invert(x2), 
                  left: innerTimeRangeScale.invert(x1)
                });
            }
        },
        parseTranslate: function(el){
            var translateStr = el.attr('transform'),
                re = /\((.*)\)/,
                result = re.exec(translateStr);

            result = result[1].split(',');
            return {
                x: Number(result[0]),
                y: Number(result[1])
            };
        },
        setGripperPosition: function(){
            var innerPos = this.model.get('innerPos'),
                leftX,
                rightX;

            this.leftGripperX = this.innerTimeRangeScale(innerPos.left);
            this.rightGripperX = this.innerTimeRangeScale(innerPos.right);

            this.element_map.leftGripper.attr('transform', 'translate('+this.leftGripperX+', 0)');
            this.element_map.rightGripper.attr('transform', 'translate('+this.rightGripperX+', 0)');
        },
        render: function(){
            this.setGripperPosition();
            this.renderOuterTimeline();
            this.renderInnerTimeRangeInfo();
            return this;
        },
        updateTopBorder: function(left, right){
            var swapped = this.model.get('swapped');
            if(swapped){
                this.element_map.borderTopLeft
                    .attr('x2', this.rightGripperX);

                this.element_map.borderTopRight
                    .attr('x1', this.leftGripperX);
            } else {
                this.element_map.borderTopLeft
                    .attr('x2', this.leftGripperX);

                this.element_map.borderTopRight
                    .attr('x1', this.rightGripperX);
            }

        },
        _renderInnerTimeRangeInfo: function(){
            var outerTimeRange = this.model.get('outerTimeRange'),
                innerTimeRange = this.model.get('innerTimeRange') || outerTimeRange,
                timeFormat = this.model.getTimeFormat(outerTimeRange.duration),
                diff = this.getGripperDiff(),
                swapped = this.model.get('swapped'),
                totalInnerTime = this.model.get('totalInnerTime'),
                centerTextWidth,
                startTimeTextWidth,
                endTimeTextWidth;

            this.element_map.innerTimeRangeInfo.select('.totalTime rect')
                .attr('width', diff);

            if(swapped){
                this.element_map.innerTimeRangeInfo.select('.totalTime rect')
                    .attr('transform', 'translate(-'+diff+')');
            } else {
                this.element_map.innerTimeRangeInfo.select('.totalTime rect')
                    .attr('transform', null);
            }
            this.element_map.innerTimeRangeInfo.attr('transform', 'translate('+this.leftGripperX+',50)');

            this.updateTopBorder(this.leftGripperX, this.rightGripperX);

            /*
            We cannot move this around with a transform attribute.
            The svg clipping occurs /before/ the transformation. 
            This results in the element not clipping appropiately.
            */
            this.element_map.highlight
                .attr('width', diff)
                .style('visibility', 'visible');

            if(swapped){
                this.element_map.highlight
                    .attr('x', this.rightGripperX);

                this.element_map.startTimeLabel
                    .text(timeFormat(innerTimeRange.latest_date));
                this.element_map.endTimeLabel
                    .text(timeFormat(innerTimeRange.earliest_date));
            } else {
                this.element_map.highlight
                    .attr('x', this.leftGripperX);

                this.element_map.startTimeLabel
                    .text(timeFormat(innerTimeRange.earliest_date));
                this.element_map.endTimeLabel
                    .text(timeFormat(innerTimeRange.latest_date));                
            }

            startTimeTextWidth = this.element_map.startTimeLabel.node().getComputedTextLength();
            endTimeTextWidth = this.element_map.endTimeLabel.node().getComputedTextLength();

            if(diff < startTimeTextWidth+endTimeTextWidth){
                this.element_map.innerTimeRangeInfoText.text('');
                this.element_map.endTimeLabel
                    .attr('visibility', 'hidden');
                this.element_map.startTimeLabel
                    .attr('visibility', 'hidden');
                this.model.set({enableTooltip: true});
            } else {
                this.element_map.endTimeLabel
                    .attr('visibility', 'visible');
                this.element_map.startTimeLabel
                    .attr('visibility', 'visible');
                this.element_map.innerTimeRangeInfoText
                    .text('view: '+ this.formatTotalTime(totalInnerTime));
                this.model.set({enableTooltip: false});
                centerTextWidth = this.element_map.innerTimeRangeInfoText.node().getComputedTextLength();
                if(swapped){
                    this.element_map.startTimeLabel
                        .attr('transform', 'translate('+[0-startTimeTextWidth, 0]+')');
                    this.element_map.endTimeLabel
                        .attr('transform', 'translate(0,0)');
                    this.element_map.innerTimeRangeInfoText
                        .attr('transform', 'translate('+(-diff/2-centerTextWidth/2)+',0)');
                } else {
                    this.element_map.startTimeLabel
                        .attr('transform', 'translate(0,0)');
                    this.element_map.endTimeLabel
                        .attr('transform', 'translate('+[0-endTimeTextWidth, 0]+')');
                    this.element_map.innerTimeRangeInfoText
                        .attr('transform', 'translate('+(diff/2-centerTextWidth/2)+',0)');
                }
            }
            
            this.element_map.innerTimeRangeInfo.select('.endTime')
                .attr('transform', 'translate('+(this.rightGripperX-this.leftGripperX)+',0)');
        },
        renderOuterTimeline: function(){
            var outerTimeRange,
                timeScale,
                timeFormat,
                xAxis;
            
            outerTimeRange = this.model.get('outerTimeRange');
            timeFormat = this.model.getTimeFormat(outerTimeRange.duration);

            timeScale = d3.time.scale()
                .domain([outerTimeRange.earliest_date, outerTimeRange.latest_date])
                .range([0, this.width]);

            xAxis = d3.svg.axis()
                .scale(timeScale)
                .orient('bottom')
                .ticks(5)
                .tickFormat(timeFormat)
                .tickPadding(2);

            this.element_map.outerTimeRange
                .classed('outerTimeRange', true)
                .call(xAxis);

            d3.select(this.el).selectAll('.outerTimeRange .tick line')
                .attr('y2', -50);

            this._renderInnerTimeRangeInfo();
        },
        getElementMap: function() {
            return {
                $innerTimeRange: this.$el.find('.innerTimeRange'),
                innerTimeRange: d3.select(this.el).select('.innerTimeRange'),
                outerTimeRange: d3.select(this.el).select('.outerTimeRange'),
                totalTime: d3.select(this.el).select('.totalTime'),
                startTime: d3.select(this.el).select('.startTime'),
                endTime: d3.select(this.el).select('.endTime'),
                leftGripper: this.svg.select('.gripper.left'),
                rightGripper: this.svg.select('.gripper.right'),
                innerTimeRangeInfo: this.svg.select('.innerTimeRangeInfo'),
                innerTimeRangeInfoText: this.svg.select('.innerTimeRangeInfo .totalTime text'),
                startTimeLabel: this.svg.select('.innerTimeRangeInfo .startTime text'),
                endTimeLabel: this.svg.select('.innerTimeRangeInfo .endTime text'),
                highlight: this.svg.select('.blueHighlight'),
                highlightGroup: this.svg.select('.blueHighlightGroup'),
                borderTopLeft: this.svg.select('.borderTopLeft'),
                borderTopRight: this.svg.select('.borderTopRight')
            };
        },
        formatTotalTime: function(time){
            var str = "";
            if(time.days > 0){
                str += time.days + "d ";
            }
            if(time.hours > 0){
                str += time.hours + "h ";
            }
            if(time.minutes > 0){
                str += time.minutes + "m";
            }
            return str;
        }
    });
});

