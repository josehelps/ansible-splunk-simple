define([
    'jquery',
    'underscore',
    'backbone'
], function(
    $,
    _,
    Backbone
) {
    return Backbone.Collection.extend({
        initialize: function(models, options) {
            this.max_concurrency = options.max_concurrency || 2;
            this.queue = new Backbone.Collection();
            this.interval = 500;
            this.timer = setInterval(_.bind(this.checkQueue, this), this.interval);

            this.on('add change:innerTimeRange', _.bind(this.addToQueue, this));
            this.on('search:cancel search:done', _.bind(this.onSearchDone, this));
        },
        /*
         * when managers are added to the collection,
         * they are automatically added to the queue
         */
        addToQueue: function(manager) {
            manager.set({running: false});
            this.queue.add(manager);
        },
        /*
         * if the queue is not empty, dispatch as many jobs
         * as there are slots available, setting running to true
         */
        checkQueue: function() {
            if (this.queue.length < 1) {
               return;
            }

            var running_jobs = this.queue.where({running: true}),
                available_slots = this.max_concurrency - running_jobs.length,
                to_add;

            if (available_slots > 0) {
                to_add = this.queue.where({running: false}).slice(0, available_slots);
                _.each(to_add, function(item) {
                    item.set({running: true});
                    item.startSearch();
                });
            } 
        },
        /*
         * find the manager in the queue that has completed
         * remove from the queue and set running to false
         */
        onSearchDone: function(search, job) {
            if (!job) {
                return;
            }
            
            var manager = this.queue.filter(function(model){
                if (!model.job) {
                    return false;
                }
                return model.job.sid===job.sid;
            });

            if (manager.length > 0) {
                manager = manager[0];
                this.queue.remove(manager);
                manager.set({running: false});
            }
        }
    });
});
