require.config({
    paths: {
        log_review_popup_view: '../app/SA-ThreatIntelligence/js/views/LogReviewPopupView'
    }
});

define(
		[
		 'jquery',
		 'underscore',
		 'views/Base',
		 'log_review_popup_view'
		 ],
		 function($, _, BaseView, LogReviewPopupView){
			return BaseView.extend({
				/**
				 * @param {Object} options {
				 *      model: {
				 *         result: <models.services.search.job.ResultsV2>,
				 *         summary: <models.services.searchjob.SummaryV2>,
				 *         report: <models.services.SavedSearch>,
				 *         application: <models.Application>
				 *     },
				 *     collection: {
				 *         selectedRows: <collections.SelectedRows>
				 *     },
				 *     backboneEventMediator : this.backboneEventMediator // If events needs to be trigger to other views
				 **/
				initialize: function() {
					BaseView.prototype.initialize.apply(this, arguments);
				},
				
				getSelectedIDs: function(){
					var selected = this.collection.selectedRows.toJSON();
					
					var uids = [];
					
					for(var i=0; i < selected.length; i++){
						uids.push(selected[i].id);
					}
					
					return uids;
				},
				
				render: function() {
					
					
					// Make the log review popup instance
				    var logReviewPopupView = new LogReviewPopupView({
				        el: this.$el,
				        checkbox_el: $('#notable_events'),
				        rule_uids_fx: function(){ return this.getSelectedIDs(); }.bind(this),
				        managerid: "id-main-search",
				        show_select_unselect_all: false
				    });
				    
				    // Render the log review popup
				    logReviewPopupView.render();
				}
			});
		}
);