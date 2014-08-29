// Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require(['jquery','underscore', 'splunkjs/mvc', 'splunkjs/mvc/utils', 'splunkjs/mvc/tokenutils', 'splunkjs/mvc/simplexml/ready!'],
        function($, _, mvc, utils, TokenUtils) {

        var tableView = mvc.Components.get('element4');

        tableView.getVisualization(function(viz) {
            viz.settings.set('drilldown', 'row');
        });

        tableView.on("click", function(e) {
            e.preventDefault();

            var submittedTokenModel = mvc.Components.getInstance('submitted', {create: true});
            var tokens = _.extend(submittedTokenModel.toJSON(), e.data);
            
            var assetInvestigatorExists = false,
            	identityInvestigatorExists = false;

            // create a service instance that will proxy thru splunkweb
            var service = mvc.createService({
                app: '-',
                owner: 'nobody'
            });
            
            // create a views instance
            var views = service.views();
        
            // fetch views ending in _investigator
            views.fetch({
                search: 'name=*_investigator'
            }, function(err, views) {
                var list = views.list();
            
                _.each(list, function(view) {
                    if(view.name === 'asset_investigator') {
                        assetInvestigatorExists = true;
                    } else if(view.name === 'identity_investigator') {
                        identityInvestigatorExists = true;
                    }
                });

                // perform conditional drilldown
                if (e.field === 'ip' && assetInvestigatorExists) {
                    utils.redirect(TokenUtils.replaceTokenNames('asset_investigator?form.asset=$click.value2$', tokens, TokenUtils.getEscaper('url')), e.event.modifierKey);
                } else if (e.field === 'dns' && assetInvestigatorExists) {
                    utils.redirect(TokenUtils.replaceTokenNames('asset_investigator?form.asset=$click.value2$', tokens, TokenUtils.getEscaper('url')), e.event.modifierKey);
                } else if (e.field === 'owner' && identityInvestigatorExists) {
                    utils.redirect(TokenUtils.replaceTokenNames('identity_investigator?form.identity=$click.value2$', tokens, TokenUtils.getEscaper('url')), e.event.modifierKey);
                } else if (e.field === 'mac' && assetInvestigatorExists) {
                    utils.redirect(TokenUtils.replaceTokenNames('asset_investigator?form.asset=$click.value2$', tokens, TokenUtils.getEscaper('url')), e.event.modifierKey);
                } else if (e.field === 'nt_host' && assetInvestigatorExists) {
                    utils.redirect(TokenUtils.replaceTokenNames('asset_investigator?form.asset=$click.value2$', tokens, TokenUtils.getEscaper('url')), e.event.modifierKey);
                } else {
                    utils.redirect(TokenUtils.replaceTokenNames('search?q=| `datamodel("Identity_Management", "All_Assets")` | `drop_dm_object_name("All_Assets")` | search $click.name2$="$click.value2$"', tokens, TokenUtils.getEscaper('url')), e.event.modifierKey);
                }      
                
            });
        });
});