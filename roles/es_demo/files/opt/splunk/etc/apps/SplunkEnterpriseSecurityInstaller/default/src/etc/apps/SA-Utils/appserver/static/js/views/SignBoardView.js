/*
This responds to the 'eventCollection:selected' mediator event
That event passes in a reference to the selected 'Events' collection (AKA bucket)
*/

define([
    'jquery',
    'backbone',
    'underscore',
    'd3',
    'app/views/ShareButtonView',
    'app/models/ShareButton',
    'app/models/GotoSearch',
    'app/views/GotoSearchView',
    'app/models/CreateNotableEvent',
    'app/views/CreateNotableEventView',
    'app/views/SignBoardHeaderView',
    'app/views/SignBoardBodyView'
],
function(
    $,
    Backbone,
    _,
    d3,
    ShareButtonView,
    ShareButton,
    GotoSearch,
    GotoSearchView,
    CreateNotableEvent,
    CreateNotableEventView,
    SignBoardHeaderView,
    SignBoardBodyView
){
    return Backbone.View.extend({
        initialize: function(options){
            this.options = options || {};
            this.collection = this.options.collection;

            this.elements = {
                '$body': this.$el.find('.signBoardBody'),
                '$header': this.$el.find('.signBoardHeader'),
                '$toSearch': this.$el.find('.toSearch'),
                '$share': this.$el.find('.share'),
                '$createNotable': this.$el.find('.createNotable')
            };

            this.svg = d3.select(this.el)
                .insert('svg', '.signBoardBody')
                .attr('width', 260)
                .attr('height', 60);

            this.showSpinner = _.throttle(this._showSpinner, 100);
            this.hideSpinner = _.throttle(_.debounce(this._hideSpinner, 50), 1000);

            this.gotoSearchView = new GotoSearchView({
                model: new GotoSearch({
                    collection: this.collection
                }),
                el: this.elements.$toSearch
            });

            this.shareButtonView = new ShareButtonView({
                model: new ShareButton({
                    prefs: this.options.prefs
                }),
                el: this.elements.$share
            });

            this.createNotableEventView = new CreateNotableEventView({
                model: new CreateNotableEvent({
                    collection: this.collection,
                    prefs: this.options.prefs
                }),
                el: this.elements.$createNotable
            });
            
            this.signBoardHeaderView = new SignBoardHeaderView({
                model: this.collection.data,
                el: this.elements.$header
            });

            this.signBoardBodyView = new SignBoardBodyView({
                model: this.collection.data,
                el: this.elements.$body
            });

            this.renderLoadingIcon();

            this.collection.data.on('ready:headerData', _.bind(this.renderHeader, this));
            this.collection.data.on('ready:bodyData', _.bind(this.renderBody, this));
            this.collection.data.on('clearAll', _.bind(this.hide, this));

            this.$el.on('click', '.toggleHandle', function(){
                var $this = $(this);
                $this.prev().toggle('fast');
                $this.find('.showMore').toggle();
                $this.find('.showLess').toggle();
            });
        },
        hide: function() { this.$el.css('visibility', 'hidden'); },
        show: function() { this.$el.css('visibility', 'visible'); },
        renderLoadingIcon: function() {
            this.loadingIcon = this.svg.append('g')
                .attr('transform', 'translate(50,10)');

            this.loadingIcon.append('use')
                .attr('xlink:href', '#loader')
                .attr('transform', 'scale(0.5)')
                .attr('width', 200);

            this.loadingIcon.append('text')
                .text("Loading...")
                .attr('transform', 'translate(50,12)');
        },
        _showSpinner: function() {
            this.elements.$body.empty().hide();
            this.svg.style('display', 'block');
        },
        _hideSpinner: function() {
            this.svg.style('display', 'none');
            this.elements.$body.show();
        },
        renderHeader: function(data){
            if (!this.collection || this.collection.length < 1) {
                this.hide();
                return this;
            }

            this.show();
            this.showSpinner();

            return this;
        },
        renderBody: function() {
            this.hideSpinner();

            return this;
        }
    });
});
