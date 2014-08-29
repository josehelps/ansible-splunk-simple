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
        className: 'event',
        tagName: 'rect',
        hexMap: {
            blue: "#005ad5",
            yellow: " #fac51c",
            red: "#d85d3c",
            orange: "#f7902b",
            purple: "#956d95",
            green: "#9ac23c"
        },
        initialize: function(options) {
            this.options = options || {};
            this.height = this.options.height;
            this.model = this.options.model;
            this.offset = this.options.offset;
            this.opacity = this.options.opacity;
            this.result = this.options.result;
            this.width = this.options.width;
            this.x = this.options.x;
            this.y = this.options.y;

            this.tooltip = d3.select('#swimlane_tooltip');

            this.parent_svg = d3.select(this.el);

            this.svg = this.parent_svg
                .append(this.tagName)
                .classed(this.className, true);

            this.el = this.svg[0][0];
            
            this.model.on('change:color', _.bind(this.onColorChange, this)); 
            this.model.sign_board.on('add', _.bind(this.onSignBoardAdd, this));
            this.model.sign_board.on('remove', _.bind(this.onSignBoardRemove, this));
            this.model.sign_board.on('reset', _.bind(this.onSignBoardReset, this));
            this.result.on('click:coordinates', _.bind(this.onXCoordinates, this));

        },
        onColorChange: function() {
            this.svg.attr('fill', this.colorToHex(this.model.get('color')));
        },
        activateClick: function() {
            this.svg.attr('stroke', '#111111');
        },
        deactivateClick: function() {
            this.svg.attr('stroke', 'transparent');
        },
        onSignBoardAdd: function() {
            if (this.isSelected()) {
                this.activateClick();
            } else {
                this.deactivateClick();
            }
        },
        onSignBoardRemove: function() {
            if (!this.isSelected()) {
                this.deactivateClick();
            }
        },
        onSignBoardReset: function(collection) {
            if (collection.length < 1) {
                this.deactivateClick();
                return;
            }
            if (!this.isSelected()) {
                this.deactivateClick();
            } else {
                this.activateClick();
            }
        },
        /*
         * if the dragged range falls in the event range,
         * add to sign_board and make self selected
         */
        onXCoordinates: function(range_x) {
            var x1 = this.x,
                x2 = this.x+this.width-1;

            // http://gamedev.stackexchange.com/questions/586/what-is-the-fastest-way-to-work-out-2d-bounding-box-intersection
            if(!(range_x[0] > x2 || range_x[1] < x1)){
                this.model.sign_board.add(this.result);
                this.activateClick();
            }
        },
        renderTooltip: function(r, m, offset) {
            var scale = m.time_range.get('innerTimeScale'),
                timeFormatter,
                output,
                innerTimeRange = m.time_range.get('innerTimeRange'),
                timeDiff = m.time_range.calculateTotalInner(innerTimeRange);

            if(timeDiff.days < 1){
                timeFormatter = d3.time.format("%I:%M:%S %p");
            } else {
                timeFormatter = d3.time.format("%m/%d %I:%M:%S %p");
            }

            output = timeFormatter(new Date(r.get('_time')))+" - "+
                         timeFormatter(new Date(scale.invert(offset+1)))+
                         "<br/>"+r.get('count')+"&nbsp;Events";

            return output;
        },
        initBehaviors: function() {
            var tooltip = this.tooltip,
                model = this.model,
                offset = this.offset,
                result = this.result,
                $parent = $(tooltip.node().parentNode),
                renderTooltip = this.renderTooltip;

            this.svg
                .on('click', _.bind(this.onClick, this))
                .on('mouseover', function() {
                    tooltip.transition()
                        .duration(500)
                        .style({
                          'opacity': 0.8,
                          'visibility': 'visible'
                        });
                })
                .on("mousemove", function(d, i){
                    var left = d3.select(this).attr('x'),
                        height = this.getBoundingClientRect().height,
                        isFF = navigator.userAgent.toLowerCase().indexOf('firefox') > -1,
                        isWindows = window.navigator.platform.toLowerCase().indexOf('win') > -1,
                        absTop = this.getBoundingClientRect().top + $(document).scrollTop(),
                        top = absTop - 5 - tooltip.node().getBoundingClientRect().height;

                    tooltip.style("left", left + "px")
                        .style("top", top + "px")
                        .html(function(){return renderTooltip(result, model, offset);})
                        .style("text-align", "left");
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
        onClick: function(e) {
            if (d3.event.metaKey || d3.event.ctrlKey) {
                if(this.isSelected()) {
                    this.model.sign_board.remove(this.result);
                } else {
                    this.model.sign_board.add(this.result);
                }
            } else {
                this.model.sign_board.reset(this.result);
            }
        },
        colorToHex: function(color) {
            if (this.hexMap[color]) {
                return this.hexMap[color];
            }
            return "#005ad5";
        },
        isSelected: function() {
            var meta = this.result.get('meta'),
                lane_name = meta.lane_name,
                id = meta.id,
                clicked = this.model.sign_board.clicked.get(lane_name) || [];

            if (_.contains(clicked, id)) {
                return true;
            }

            return false;
        },
        render: function() {
            this.svg 
                .attr('x', this.x)
                .attr('y', this.y)
                .attr('height', this.height)
                .attr('width', this.width-1)
                .attr('fill-opacity', this.opacity)
                .attr('fill', this.colorToHex(this.model.get('color')))
                .attr('stroke', 'transparent')
                .attr('stroke-width', 0.7);

            if (this.isSelected()) {
                this.model.sign_board.add(this.result);
            }
                
            this.initBehaviors();

            return this;
        }
    });
});
