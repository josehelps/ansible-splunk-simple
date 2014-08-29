define(
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/shared/timerangepicker/dialog/Master',
        'views/shared/delegates/Popdown',
        'collections/SplunkDsBase',
        'splunk.util',
        'util/console'
    ],
    function($, _, module, BaseView, Dialog, Popdown, SplunkDsBaseV2, splunk_util, console) {
        /**
         * @param {Object} options {
         *      model: {
         *          timeRange: <models.TimeRange>,
         *          user: <models.services.admin.User>,
         *          appLocal: <models.services.AppLocal>,
         *          application: <models.Application>
         *      },
         *      collection: <collections.services.data.ui.TimesV2>
         *      {String} timerangeClassName (Optional) Class attribute to the button element. Default is btn.
         *      {Object} dialogOptions: (Optional) Keys and values passed to the dialog for customization. See views/shared/timerangepicker/dialog/Master.
         * }
         */
        return BaseView.extend({
            moduleId: module.id,
            className: 'btn-group',
            initialize: function(options) {
                this.options = options || {};
                var defaults = {
                    timerangeClassName: 'btn'
                };

                _.defaults(this.options, defaults);

                BaseView.prototype.initialize.call(this, options);
               
                this.children.dialog = new Dialog(
                    $.extend(
                        {
                            model: {
                                timeRange: this.model.timeRange,
                                user: this.model.user,
                                appLocal: this.model.appLocal,
                                application: this.model.application
                            },
                            collection: this.collection
                        },
                        this.options.dialogOptions || {}
                     )
                );
                
                if (this.collection) {
                    this.collection.on('reset', function(){
                        console.log("timerangepicker setting label because of collection reset");
                        this.setLabel();
                    }, this);
                }
                this.listenToModels();
                this.model.timeRange.trigger("prepopulate");
            },
            listenToModels: function() {
                this.model.timeRange.on('change:earliest change:latest', _.debounce(this.timeRangeChange, 0), this);
                this.model.timeRange.on('applied', this.timeRangeApplied, this);
                this.model.timeRange.on('change:earliest_epoch change:latest_epoch change:earliest change:latest', _.debounce(this.setLabel, 0), this);
            },
            stopListeningToModels: function() {
                this.model.timeRange.off(null, null, this);
            },
            timeRangeChange: function() {
                this.stopListeningToModels();
                this.listenToModels();
            },
            timeRangeApplied: function() {
                this.children.popdown.hide();
            },
            setLabel: function() {
                var timeLabel = this.model.timeRange.generateLabel(this.collection || new SplunkDsBaseV2());
                this.$el.children('a').find(".time-label").text(_(timeLabel).t());
            },
            render: function() {
                this.$el.html(this.compiledTemplate({
                    options: this.options
                }));

                this.$('.popdown-dialog').append(this.children.dialog.render().el);

                this.children.popdown = new Popdown({
                    el: this.el,
                    toggle:'> a',
                    mode: "dialog",
                    attachDialogTo: 'body',
                    ignoreClasses: [
                        "ui-datepicker",
                        "ui-datepicker-header",
                        "dropdown-menu"
                    ]
                });
                
                this.children.popdown.on('shown', function() {
                    if (this.children.dialog.$(".accordion-group.active").length){
                        this.children.dialog.onShown();
                        return;
                    }
                    var timePanel = "presets";
                    this.children.dialog.children[timePanel].$el.closest(".accordion-group").find(".accordion-toggle").first().click();
                    this.children.dialog.onShown();
                }, this);
                                
                this.setLabel();

                return this;
            },
            template: '\
                <a class=" splBorder splBorder-nsew splBackground-primary <%- options.timerangeClassName %>" href="#"><span class="time-label"></span><span class="caret"></span></a>\
                <div class="popdown-dialog">\
                    <div class="arrow"></div>\
                </div>\
                '
        });
    }
);
