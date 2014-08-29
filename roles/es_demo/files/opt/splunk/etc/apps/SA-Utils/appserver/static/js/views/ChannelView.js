define([
    'jquery',
    'backbone',
    'underscore',
    'd3',
    'app/collections/Events',
    'app/views/EventView'
],
function(
    $,
    Backbone,
    _,
    d3,
    Events,
    EventView
){
    return Backbone.View.extend({
        className: 'lane_channel',
        // this url is created by the SVGDefs template and is used
        // to provide the spinning gif which indicates loading
        spinner_fill: 'url(#spinner_fill)',
        tagName: 'g',
        initialize: function(options) {
            this.options = options || {};
            this.model = this.options.model;
            this.sign_board = this.model.sign_board;
            this.time_range = this.model.time_range;

            this.svg = d3.select(this.el)
                .append(this.tagName)
                .classed(this.className, true);
            this.el = this.svg[0][0];

            this.svg.attr('transform', 'translate('+[4,0]+')');

            // hook up drag
            this.svg.call(this.setupDrag());

            this.data = null;
            this.manager = null;
            this.rect = null;

            // render outer container
            this.renderContainer();

            // debounce spinner to prevent artifacts
            this.showSpinner = _.debounce(this._showSpinner, 100);
            this.hideSpinner = _.debounce(this._hideSpinner, 100);

            this.addSearchManager();

            // add the search manager bindings
            this.model.on('add:manager', _.bind(this.addSearchManager, this));
            if (!this.model.get("entity_name")) {
                this._hideSpinner();
            }
        },
        setupDrag: function() {
            var height = this.model.get('height'),
                offset = this.model.get('offset'),
                isRightClick = false,
                last_x = null,
                last_y = null,
                orig_x = null,
                orig_y = null,
                that = this,
                is_additive = false,
                dragData = {},
                drag = d3.behavior.drag()
                    .on("dragstart", function() {

                        if (d3.event.sourceEvent.metaKey || d3.event.sourceEvent.ctrlKey) {
                            is_additive = true;
                        } else {
                            is_additive = false;
                        }

                        isRightClick = that.isRightClick(d3.event.sourceEvent); 
                        if (isRightClick) {
                            return;  
                        }

                        d3.event.sourceEvent.stopPropagation();

                        dragData.offset = $(that.el).offset();
                        dragData.x = $(window).scrollLeft() + d3.event.sourceEvent.clientX - dragData.offset.left;
                        dragData.y = $(window).scrollTop() + d3.event.sourceEvent.clientY - dragData.offset.top;

                        // JIC
                        that.svg.selectAll('rect.dragger').remove();

                        dragData.rect = that.svg.append("rect")
                            .classed('dragger', true)
                            .attr("x", dragData.x)
                            .attr("y", dragData.y)
                            .attr("width", 0)
                            .attr("height", 0)
                            .attr("fill", '#303030')
                            .attr("opacity", 0.5);

                    }).on("dragend", function() {

                        if (isRightClick) {
                            return;
                        }

                        // must remove dragger rectangle first
                        dragData.rect.remove();

                        // if there has never been a drag event, bail out
                        if (orig_x===null || orig_y===null) {
                            return;
                        }
 
                        // trigger selection event on model, then null coordinates and remove rectangle
                        // the delay helps ensure that the rectangle is removed and the sign board spins before
                        // the computationaly-intensive work of creating the signboard data begins 
                        if(!is_additive){
                            that.model.sign_board.reset();
                        }
                        _.delay(function() {
                            that.model.trigger('drag:selection', orig_x, last_x, orig_y, last_y, height*offset, is_additive);
                            last_x = last_y = orig_x = orig_y = null;
                        }, 200);

                    }).on("drag", function() {

                        if (isRightClick) {
                            return;
                        }

                        // must remove dragger rectangle first
                        if (orig_x===null) {
                            orig_x = d3.event.x;
                        }
                        if (orig_y===null) {
                            orig_y = d3.event.y;
                        }

                        var width = d3.event.x - orig_x,
                            height = d3.event.y - orig_y;

                        last_x = d3.event.x;
                        last_y = d3.event.y;

                        dragData.rect
                            .attr("x", orig_x)
                            .attr("y", orig_y)
                            .attr("width", Math.abs(width))
                            .attr("height", Math.abs(height));
                        
                        if (width < 0) {
                            dragData.rect.attr("x", d3.event.x);
                        }
                        if (height < 0) {
                            dragData.rect.attr("y", d3.event.y);
                        }

                    });
            return drag;
        },
        isRightClick: function(sourceEvent) {
            if (sourceEvent.which !== 1) {
                return true;
            } 
            if (sourceEvent.ctrlKey === true) {
                return true;
            }
            return false;
        },
        addSearchManager: function() {
            if (!this.model.manager) {
                return;
            }

            var previous_data = this.model.get('previous_data');

            // bind to preview results 
            this.manager = this.model.manager;
            this.manager.set('done', true);

            // when search data arrives
            this.data = this.manager.data('preview');
            this.data.on('data', _.bind(this.onData, this));
       
            // wire up callbacks to search start and search done
            this.manager.on('search:start', _.bind(this.onSearchStart, this));
            this.manager.on('search:progress', _.bind(this.onSearchProgress, this));
            this.manager.on('search:done', _.bind(this.onSearchDone, this));
            this.manager.on('search:error', _.bind(this.onSearchError, this));
            
            // wire up callback to time range change
            // use manager event which is debounced
            this.manager.on('change:innerTimeRange', _.bind(this.onInnerTimeRangeChange, this));

            // if there is old data in the model, render it
            if (previous_data) {
                this.render(previous_data);
            }

        },
        onInnerTimeRangeChange: function() {
            this.destroyEvents();
            this.clearErrorMessage();
            this.showSpinner();
            this.model.pref.clearClickedEvents();
        },
        onSearchStart: function() {
            this.manager.set('done', false);
            this.destroyEvents();
            this.showSpinner();
            this.clearErrorMessage();
        },
        onSearchProgress: function(properties) {
            properties = properties || {};
            var content = properties.content || {},
                previewCount = content.resultPreviewCount || 0,
                isJobDone = content.isDone || false;

            if (previewCount===0 && isJobDone) {
                this.noResults();
            }
        },
        onSearchDone: function(state, job) {
            this.manager.set('done', true);
            this.hideSpinner();
        },
        onSearchError: function(a, b) {
            console.error('Search Error: ', this.model.id, a, this.manager);

            this.hideSpinner();
            this.errorMessageIcon.text("\ue801");
            this.errorMessageText.text("Error.  Search did not run correctly");
        },
        onData: function() {
            var collection = this.data.collection();
            if (collection && collection.length > 0) {
                this.render(collection);
            }
        },
        renderContainer: function() {
            var channel = this.model.get('channel'),
                height = this.model.get('height');

            this.rect = this.svg.append('rect')
              .classed(channel.rect.className, true) 
              .attr('x', channel.rect.x)
              .attr('y', channel.rect.y)
              .attr('width', channel.rect.width)
              .attr('height', height)
              .attr('fill', channel.rect.fill)
              .attr('stroke', channel.rect.stroke);

            this.loadingIcon = this.svg.append('g')
                .attr('transform', 'translate(525,5)');

            this.loadingIcon.append('rect')
                .attr('fill', 'white')
                .attr('width', 150)
                .attr('height', height-1)
                .attr('transform', 'translate(0,-4)');

            this.loadingIcon.append('use')
                .attr('xlink:href', '#loader')
                .attr('transform', 'scale(0.5)')
                .attr('width', 200);
            
            this.loadingIcon.append('text')
                .text("Loading...")
                .attr('transform', 'translate(50,12)');

            this.errorMessage = this.svg.append('g')
                .attr('transform', 'translate(520, 25)');

            this.errorMessageIcon = this.errorMessage.append("text")
                .classed("errorMessageIcon", true)
                .style("font-family", "fontello");

            this.errorMessageText = this.errorMessage.append("text")
                .classed("errorMessageText", true)
                .attr("x", 20);
        },
        _showSpinner: function() {
            this.loadingIcon.attr('display', 'block');
        },
        _hideSpinner: function() {
            this.loadingIcon.attr('display', 'none');
        },
        noResults: function() {
            this.hideSpinner();
            this.destroyEvents();
            this.model.set({previous_data: new Backbone.Collection()});
            this.errorMessageText.text("Search returned no results");
        },
        destroyEvents: function() {
            this.svg.selectAll('rect.event').remove();
            this.svg.selectAll('rect.clicked').remove();
        },
        clearErrorMessage: function() {
            this.errorMessageIcon.text("");
            this.errorMessageText.text("");
        },
        render: function(collection) {
            var sorted_coll = collection.clone(),
                sign_board = this.sign_board,
                model = this.model,
                channel = model.get('channel'),
                height = model.get('height'),
                base_x = channel.rect.x,
                width = channel.rect.width/80, 
                el = this.el,
                scale = this.time_range.get('innerTimeScale'),
                count_scale = d3.scale.pow().range([0.3,1.0]),
                events = new Events();

            this.destroyEvents();

            if (!collection || collection.length<1) {
                this.noResults();
                return this;
            } 

            this.hideSpinner();
            this.clearErrorMessage();

            // sorting function to order the cloned
            // collection by count (must cast to Number)
            sorted_coll.comparator = function(a, b) {
                var ca = Number(a.get('count')),
                    cb = Number(b.get('count'));
                if (ca > cb) {
                    return 1;
                }
                if (ca < cb) {
                    return -1;
                }
                if (ca===cb) {
                    return 0;
                }
            };
            sorted_coll.sort();

            // set opacity scale based on range of counts
            count_scale.domain([
                Number(sorted_coll.at(0).get('count')), 
                Number(sorted_coll.at(sorted_coll.length-1).get('count'))
            ]); 

            // render each event
            collection.each(function(m, i) {
                var _time = m.get('_time'),
                    t = new Date(_time),
                    idx = Math.max(0, Math.round(scale(t), 0)),
                    opacity = Math.round(count_scale(m.get('count'))*10)/10,
                    offset = scale(t),
                    x = (idx*width)+base_x,
                    meta = {
                      search: model.manager.get('data').normalizedSearch,
                      drilldown: model.get('normalizedDrilldown'),
                      lane_name: model.id,
                      earliest_time: new Date(t),
                      latest_time: new Date(scale.invert(idx+1)),
                      id: _time,
                      offset: offset
                    };

                m.set('meta', meta);

                new EventView({
                  el: el,
                  height: Number(height)-4,
                  offset: offset,
                  model: model,
                  result: m,
                  opacity: opacity,
                  width: width,
                  x: x,
                  y: 2
                }).render();

                events.add(m);
            });

            model.set({events: events});
            model.set({previous_data: collection}, {silent: true});
        

            return this;
        }
    });
});
