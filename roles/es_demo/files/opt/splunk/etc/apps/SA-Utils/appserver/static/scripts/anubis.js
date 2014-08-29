$(document).ready(function() {
	// ##############################################
	//	TREE FUNCTION BINDING
	// ##############################################
	var $tElement = $('#anubis-selector-container');
	var $contextTextarea = $("#context-textarea");
	var $searchTextarea = $("#search-textarea");
	var limit = 1; //don't fucking change this ever
	var mid; //need this accessible to everyone
	var modifiedContext; //I want to not have to make this everytime
	
	var contextEditor = CodeMirror.fromTextArea(document.getElementById("context-textarea"), {
		mode: {name: "javascript"},
		lineNumbers: true,
		indentUnit: 4,
		tabMode: "shift",
		matchBrackets: true
	});
	var modifiedContextEditor = CodeMirror.fromTextArea(document.getElementById("modified-context-textarea"), {
		mode: {name: "javascript"},
		lineNumbers: true,
		indentUnit: 4,
		tabMode: "shift",
		matchBrackets: true
	});
	var searchEditor = CodeMirror.fromTextArea(document.getElementById("search-textarea"), {
		mode: {name: "javascript"},
		lineNumbers: true,
		indentUnit: 4,
		tabMode: "shift",
		matchBrackets: true
	});
	var resultsEditor = CodeMirror.fromTextArea(document.getElementById("search-results-textarea"), {
		mode: {name: "javascript"},
		lineNumbers: true,
		indentUnit: 4,
		tabMode: "shift",
		matchBrackets: true
	});
	handleExpandAllClick = function() {
		//Basically we just expand all the nodes, nothing really cool here
		$("span.ui-icon-parent").each( function() {
			var $this = $(this);
			if ($this.hasClass("noel-icon-plus")) {
				$this.removeClass("noel-icon-plus");
				$this.addClass("noel-icon-minus");
				$(".ui-tree-container:first",$this.parent().parent()).show();
			}
		});
	};
	handleCollapseAllClick = function() {
		//Basically we just collapse all the nodes, nothing really cool here
		$("span.ui-icon-parent").each( function() {
			var $this = $(this);
			if ($this.hasClass("noel-icon-minus")) {
				$this.removeClass("noel-icon-minus");
				$this.addClass("noel-icon-plus");
				$(".ui-tree-container:first",$this.parent().parent()).hide();
			}
		});
	};
	/**
	* This is the event handler for people entering or removing text from the search bar.
	* It performs a search ONLY on the leaf nodes of the tree hiding those that do not 
	* have a full or partial match. If it detects the value to be an empy string it 
	* immediately shows all leaf nodes. It does this by the assignment of the search 
	* match/nomatch classes to the node box for the element.
	*/
	handleSearchbarInput = function() {
		var searchString = $('.ui-tree-searchbar',this.container).val();
		//Hack because we filter on everything...
		handleExpandAllClick();
		
		if (searchString === "") {
			$('.ui-tree-node').parent().removeClass("ui-search-nomatch");
		}
		else {
			var re = new RegExp(window.opener.SOLN.escapeStringForRegExp(searchString), "i");
			$('.ui-tree-node').each( function() {
				var $this = $(this);
				if ($this.text().match(re)) {
					$this.parent().removeClass("ui-search-nomatch");
				}
				else {
					$this.parent().addClass("ui-search-nomatch");
				}
			});
		}
	};
	
	handleSelected = function(event, ui) {
		//Kill highlight
		$('.devModuleOverlay', window.opener.document).remove();
		//Kill old module data
		contextEditor.setValue("");
		searchEditor.setValue("");
		resultsEditor.setValue("");
		var $node = $(ui.selected);
		var realContext;
		var realModifiedContext;
		mid = $node.attr("id");
		try {
			realContext = window.opener.SOLN.getModuleById(mid).getContext();
			realModifiedContext = window.opener.SOLN.getModuleById(mid).getModifiedContext();
		}
		catch(err) {
			//HIDE ALL THE ERRORS!
			console.log("hit a hack where the module id's are wrong so i tried to fix it with a big hack, enjoy i hope it works.");
			mid = mid.substring(0,mid.length-1) + "0";
			realContext = window.opener.SOLN.getModuleById(mid).getContext();
			realModifiedContext = window.opener.SOLN.getModuleById(mid).getModifiedContext();
		}
		modifiedContext = realModifiedContext;
		var fakeContext = jQuery.extend(true, {}, realContext._root);
		var fakeModifiedContext = jQuery.extend(true, {}, realModifiedContext._root);
		var fakeSearch = jQuery.extend(true, {}, realContext.get("search"));
		if (fakeSearch.job) {
			delete fakeSearch.job;
		}
		if (fakeContext.search) {
			delete fakeContext.search;
			delete fakeContext["results.upstreamPaginator"];
		}
		if (fakeModifiedContext.search) {
			delete fakeModifiedContext.search;
			delete fakeModifiedContext["results.upstreamPaginator"];
		}
		var killRe = new RegExp("[ \t]*\"re\": \{\},[\n\r]+","g");
		var prettyContextRoot = JSON.stringify(fakeContext, null, '    ').replace(killRe,'');
		var prettyModifiedContextRoot = JSON.stringify(fakeModifiedContext, null, '    ').replace(killRe,'');
		var prettySearch = JSON.stringify(fakeSearch, null, '    ');
		contextEditor.setValue(prettyContextRoot);
		modifiedContextEditor.setValue(prettyModifiedContextRoot);
		searchEditor.setValue(prettySearch);
	};
	
	$tElement.selectable({ filter: "div.ui-tree-node.module-node", 
		cancel: 'span.noel-icon',
		selecting: function(event, ui) { 
			if ($(".ui-selected, .ui-selecting").length > limit) {
				$(ui.selecting).removeClass("ui-selecting");
			}
		},
		selected: handleSelected
	});
	
	handleGetResults = function() {
		resultsEditor.setValue("");
		var moduleContext = window.opener.SOLN.getModuleById(mid).getContext();
		var results = window.opener.SOLN.getJobResults(moduleContext);
		console.log(results);
		console.log(typeof(results));
		results = JSON.parse(results);
		results = JSON.stringify(results, null, '    ');
		resultsEditor.setValue(results);
	};
	
	handleInspect = function() {
		var module = window.opener.SOLN.getModuleById(mid);
		var context = module.getContext();
		var search = context.get("search");
		var sid = search.job.getSID();
		window.opener.Splunk.window.openJobInspector(sid);
	};
	
	handleHighlight = function() {
		//two flushes ain't gona get rid of my access to the other window's document!
		$module = $("#" + mid, window.opener.document).css('position', 'relative');
		
		var context = window.opener.SOLN.getModuleById(mid).getContext();
		var contextOutput = [];
		var contextHash = context.getAll();
		for (var k in contextHash) {
			if (contextHash.hasOwnProperty(k)) {
				contextOutput.push(k + '=' + contextHash[k]);
			}
		}
		
		var overlay = $('<div class="devModuleOverlay"><span class="devModuleLabel">' + mid + '</span><div class="devModuleSettings">' + contextOutput.join('<br />') + '</div></div>');
		overlay.css('width', $module.outerWidth());
		overlay.css('height', $module.outerHeight());
		overlay.appendTo($module);
	};
	
	handlePushCustomContext = function() {
		//Veni Vidi Contecem Mutare -- whatever close enough I'm little drunk.
		var userContextRoot = JSON.parse(modifiedContextEditor.getValue());
		userContextRoot = { _root: userContextRoot };
		var explicitContext = jQuery.extend(true, modifiedContext, userContextRoot);
		m = window.opener.SOLN.getModuleById(mid);
		m.pushContextToChildren(explicitContext);
	};
	
	//Bind Control UI functions and make them purrrrty
	$(".ui-tree-button").button();
	$(".ui-tree-buttonset").buttonset();
	$('.ui-tree-expand-all').click(handleExpandAllClick);
	$('.ui-tree-collapse-all').click(handleCollapseAllClick);
	$('.ui-tree-searchbar').keyup(handleSearchbarInput);
	$('#get-results-button').click(handleGetResults);
	$('#inspect-button').click(handleInspect);
	$('#highlight-module-button').click(handleHighlight);
	$('#push-context-button').click(handlePushCustomContext);
	//Bind Tree UI functions
	$("span.ui-icon-parent",this.tElement).click( function() {
		var $this = $(this);
		if ($this.hasClass("noel-icon-plus")) {
			$this.removeClass("noel-icon-plus");
			$this.addClass("noel-icon-minus");
			$(".ui-tree-container:first",$this.parent().parent()).show();
		}
		else {
			$this.removeClass("noel-icon-minus");
			$this.addClass("noel-icon-plus");
			$(".ui-tree-container:first",$this.parent().parent()).hide();
		}
	});

	
});