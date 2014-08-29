// Copyright 2011 Splunk, Inc.
//
//   Licensed under the Apache License, Version 2.0 (the "License"); 
//   you may not use this file except in compliance with the License.	
//   You may obtain a copy of the License at
//																										
//	   http://www.apache.org/licenses/LICENSE-2.0 
//
//   Unless required by applicable law or agreed to in writing, software 
//   distributed under the License is distributed on an "AS IS" BASIS,
//   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//   See the License for the specific language governing permissions and 
//   limitations under the License.

/**
 * A module that handles drilldowns
 */
Splunk.Module.SOLNDrilldown = $.klass(Splunk.Module, {

	initialize: function($super, container) {

		$super(container);

		this.logger = Splunk.Logger.getLogger("SOLNDrilldown.js");
		this.messenger = Splunk.Messenger.System.getInstance();
		this.drilldownKey = this.getParam('drilldownKey', null);
		this.filterKey = this.getParam('filterKey', null);
		this.preCommand = this.getParam('preCommand', null);
		this.postCommand = this.getParam('postCommand', null);
		this.useFullSearch = this.getParam('useFullSearch', null);
		this.leftPipeTrim = this.getParam('leftPipeTrim', null);
		this.rightPipeTrim = this.getParam('rightPipeTrim', null);
		this.baseOverride = this.getParam('baseOverride', null);
		this.useSVUSub = this.getParam('useSVUSub', null);
		this.newSearch = this.getParam('newSearch', null);

	},

	getModifiedContext: function() {
		var context = this.getContext(), 
			click = context.getAll('click'),
			search = context.get('search'),
			moddrill,
			new_search,
			full_search = search.job.getSearch(),
			event_search = search.job.getEventSearch(),
			useFullSearch = Boolean(this.useFullSearch),
			time_range;
		search.abandonJob();
	
	//Handle base search or partial search or baseOverride

		if (this.useFullSearch) {
				new_search = full_search;
		}
		else if (this.baseOverride) {
			new_search = this.baseOverride;
		}
		else {
				new_search = event_search;
		}

	//Process Trim Rules
	var i;
	var pos;
	if (this.leftPipeTrim !== null) {
		i=0;
		pos=0;
		for (i=0;i<this.leftPipeTrim;i++)
		{
			pos = full_search.indexOf("|",pos + 1);
		}
		new_search = full_search.slice(0, pos);
	}
	
	if (this.rightPipeTrim !== null) {
		i=0;
		pos=full_search.length;
		for (i=0;i<this.rightPipeTrim;i++)
		{
			pos = full_search.lastIndexOf("|",pos - 1);
		}
		new_search = full_search.slice(pos);
	}

	//Append preCommand to search stream

		if (!(this.preCommand === null)) {
				new_search = new_search + ' | ' 
					+ this.preCommand ;
		}
	
	//Replace "clicks" with actual item clicked on

		if (!(this.drilldownKey === null)) {
			if (click.name || click.value || (click.name2 && click.name2 != 'OTHER') || click.value2) {
			moddrill = this.drilldownKey;
			moddrill = moddrill.replace("$click.name$",click.name);
			moddrill = moddrill.replace("$click.name2$",click.name2);
			moddrill = moddrill.replace("$click.value$",click.value);
			moddrill = moddrill.replace("$click.value2$",click.value2);
				new_search = new_search + ' | search ' 
					+ moddrill; 
			}
		}
	
	//Append filterKey with fields command

		if (!(this.filterKey === null)) {
				new_search = new_search + ' | fields ' 
					+ this.filterKey ;
		}
	
	//Append postCommand

		if (!(this.postCommand === null)) {
				new_search = new_search + ' | ' 
					+ this.postCommand ;
		}
		
	//Override with newSearch
		
		if (!(this.newSearch === null)) {
			modsearch = this.newSearch;
			if (click.name || click.value || (click.name2 && click.name2 != 'OTHER') || click.value2) {
				modsearch = modsearch.replace("$click.name$",click.name);
				modsearch = modsearch.replace("$click.name2$",click.name2);
				modsearch = modsearch.replace("$click.value$",click.value);
				modsearch = modsearch.replace("$click.value2$",click.value2);
			}
            if (this.useSVUSub !== null) {
            	// we wont return this one. But we need the full set of tokens
           		// for $foo$ replacements in the search param.
           		var internalContext = this.getContext();
           		Sideview.utils.setStandardTimeRangeKeys(internalContext);
           		Sideview.utils.setStandardJobKeys(internalContext);
           		modsearch = Sideview.utils.replaceTokensFromContext(modsearch, internalContext);
            }
			new_search = modsearch;
		}
	
	//Handle timerange

		if (click.timeRange) {
			time_range = click.timeRange.clone();
			search.setTimeRange(time_range);
		}
		search.setBaseSearch(new_search);
		context.set('search', search);
		return context;
	}
});