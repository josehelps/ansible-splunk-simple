/* Rules
 * 1. No commas in field names.
 * 2. No null values for fields.
 */


Splunk.Module.SOLNDropdown = $.klass(Splunk.Module.DispatchingModule, {
	initialize: function($super, container) {
		$super(container);
		//Set up internal variables
		this.cbElement = $('.ui-combobox', this.container);
		this.displayField = this.getParam("displayField");
		this.valueFields = this.getParam("valueField").split(',');
		this.staticItems = this.getParam("staticItem") ? this.getParam("staticItem").split(";") : [];
		this.solnns = this.getParam("varName") ? this.getParam("varName") : false;
		this.staticOnly = Splunk.util.normalizeBoolean(this.getParam("staticOnly"));
		$(this.container).attr("style",this.getParam("style"));
		this.firstLoad = true; //use this to decide what value to set on render
		this.label = this.getParam("label") ? this.getParam("label") : "";
		$(".SOLNDropdownLabel",$(this.container)).html(this.label);
		//Handle soln namespace if defined and pull the previously used value
		if (this.solnns) {
			this.stickyValue = SOLN.pullSelection(this.solnns);
		}
		else {
			this.stickyValue = false;
		}
		
		//Context flow gates
		this.doneUpstream = false;
		this.gettingResults = false;

		//Set up set of fields we need to tell splunk that we need
		this.requiredFields = this.valueFields.slice(0);
		this.requiredFields.push(this.displayField);
		
		//Make combobox functionality, thank you jQueryUI...
		(function( $ ) {
			$.widget( "ui.combobox", {
				_create: function() {
					var input,
						self = this,
						select = this.element.hide(),
						selected = select.children( ":selected" ),
						value = selected.val() ? selected.text() : "",
						wrapper = this.wrapper = $( "<span>" )
							.addClass( "ui-combobox" )
							.insertAfter( select );

					input = $( "<input>" )
						.appendTo( wrapper )
						.val( value )
						.addClass( "ui-state-default ui-combobox-input" )
						.autocomplete({
							delay: 0,
							minLength: 0,
							source: function( request, response ) {
								var matcher = new RegExp( $.ui.autocomplete.escapeRegex(request.term), "i" );
								response( select.children( "option" ).map(function() {
									var text = $( this ).text();
									if ( this.value && ( !request.term || matcher.test(text) ) ){
										return {
											label: text.replace(
												new RegExp(
													"(?![^&;]+;)(?!<[^<>]*)(" +
													$.ui.autocomplete.escapeRegex(request.term) +
													")(?![^<>]*>)(?![^&;]+;)", "gi"
												), "<strong>$1</strong>" ),
											value: text,
											option: this
										};
									}
								}) );
							},
							select: function( event, ui ) {
								ui.item.option.selected = true;
								self._trigger( "selected", event, {
									item: ui.item.option
								});
								select.trigger("change");
							},
							change: function( event, ui ) {
								if ( !ui.item ) {
									var matcher = new RegExp( "^" + $.ui.autocomplete.escapeRegex( $(this).val() ) + "$", "i" ),
										valid = false;
									select.children( "option" ).each(function() {
										if ( $( this ).text().match( matcher ) ) {
											this.selected = valid = true;
											return false;
										}
									});
									if ( !valid ) {
										// remove invalid value, as it didn't match anything
										$( this ).val( "" );
										select.val( "" );
										input.data( "autocomplete" ).term = "";
										return false;
									}
								}
							}
						})
						.addClass( "ui-widget ui-widget-content ui-corner-left" );

					input.data( "autocomplete" )._renderItem = function( ul, item ) {
						return $( "<li></li>" )
							.data( "item.autocomplete", item )
							.append( "<a>" + item.label + "</a>" )
							.appendTo( ul );
					};

					$( "<a>" )
						.attr( "tabIndex", -1 )
						.attr( "title", "Show All Items" )
						.appendTo( wrapper )
						.button({
							icons: {
								primary: "ui-icon-triangle-1-s"
							},
							text: false
						})
						.removeClass( "ui-corner-all" )
						.addClass( "ui-corner-right ui-combobox-toggle" )
						.click(function() {
							// close if already visible
							if ( input.autocomplete( "widget" ).is( ":visible" ) ) {
								input.autocomplete( "close" );
								return;
							}

							// work around a bug (likely same cause as #5265)
							$( this ).blur();

							// pass empty string as value to search for, displaying all results
							input.autocomplete( "search", "" );
							input.focus();
						});
				},

				destroy: function() {
					this.wrapper.remove();
					this.element.show();
					$.Widget.prototype.destroy.call( this );
				}
			});
		})( jQuery );
		
		this.cbElement.change(function() {
			this.onChange();
			}.bind(this));
	},
	onContextChange: function() {
		if (this.staticOnly) {
			//note this really doesn't get results as much as 
			//recognize there are only static resutls
			this.getResults();
		}
		else {
			var context = this.getContext();
			if (context.get("search").job.isDone()) {
				this.getResults();
			} else {
				this.doneUpstream = false;
			}
		}
	},
	onJobDone: function(event) {
		this.getResults();
	},
	requiresDispatch: function($super,search) {
		if (this.staticOnly) {
			return false;
		}
		else {
			return $super(search);
		}
	},
	getResultURL: function() {
		var context = this.getContext();
		var params = {};
		var search  = context.get("search");
		params['search'] = search.getPostProcess() || "";
		params['outputMode'] = "json";
		params['count'] = 0;
		var url = search.getUrl("results");
		return url + "?" + Splunk.util.propToQueryString(params);
	},
	getResults: function($super) {
		this.doneUpstream = true;
		this.gettingResults = true;
		if (this.staticOnly) {
			this.renderResults("");
		}
		else { 
			return $super();
		}
	},
	renderResults: function(jsonRsp) {
		//Clean up existing
		this.cbElement.empty();
		$("input",this.cbElement.parent()).val('');
		var data = SOLN.parseResults(jsonRsp);
		var ii;
		var jj;
		var values;
		var label;
		
		if (this.staticItems.length>0) {
			for (ii=0; ii<this.staticItems.length; ii++) {
				var item = this.staticItems[ii];
				var staticValues = item.split(",");
				//Pull out the label from configured param
				label = $.trim(staticValues.shift());
				values = [];
				//Assemble values array per spec varName,varValue,...
				for (jj=0; jj<staticValues.length; jj++) {
					values.push($.trim(this.valueFields[jj]));
					values.push($.trim(staticValues[jj]));
				}
				this.cbElement.append($("<option>").text(label).attr("value",values.toString()).attr("soln-ns",staticValues[0]));
			}
		}
		for (ii=0; ii<data.length; ii++) {
			var row = data[ii];
			label = row[this.displayField];
			values = [];
			//values.push(label); don't need the label value in the value array
			for (jj=0; jj<this.valueFields.length; jj++) {
				valField = $.trim(this.valueFields[jj]);
				values.push(valField);
				values.push(row[valField]);
			}
			//actually create a DOM element and dump it in the select, note that we add the special attribute "soln-ns" for soln var namespacing
			this.cbElement.append($("<option>").text(label).attr("value",values.toString()).attr("soln-ns",row[this.valueFields[0]]));
		}
		this.cbElement.combobox();
		context = this.getContext();
		//Please forgive this awful long if but here's what's up: check for initial load, existant namespace, existant variable in namespace, existant option matching that variable
		if (this.firstLoad && this.solnns && SOLN.getVariableValue(this.solnns, context) && $("option[soln-ns=" + SOLN.escapeStringForSelector(SOLN.getVariableValue(this.solnns, context)) + "]",this.cbElement).length) {
			//Set to the value in the context if it exists and this is the first load
			$("input",this.cbElement.parent()).val($("option[soln-ns=" + SOLN.escapeStringForSelector(SOLN.getVariableValue(this.solnns, context)) + "]",this.cbElement).text());
			this.cbElement.val($("option[soln-ns=" + SOLN.escapeStringForSelector(SOLN.getVariableValue(this.solnns, context)) + "]",this.cbElement).val());
		}
		else if (this.stickyValue && $("option[soln-ns=" + SOLN.escapeStringForSelector(this.stickyValue) + "]",this.cbElement).length) {
			//Set the value to the previously selected if it exists
			$("input",this.cbElement.parent()).val($("option[soln-ns=" + SOLN.escapeStringForSelector(this.stickyValue) + "]",this.cbElement).text());
			this.cbElement.val($("option[soln-ns=" + SOLN.escapeStringForSelector(this.stickyValue) + "]",this.cbElement).val());
		}
		else {
			//If all else fails, set to the first value in the list
			$("input",this.cbElement.parent()).val($("option:first",this.cbElement).text());
			this.cbElement.val($("option:first",this.cbElement).val());
		}
		
		this.firstLoad = false;
		this.gettingResults = false;
		this.pushContextToChildren();
	},
	getModifiedContext: function() {
		var context = this.getContext();
		var search  = context.get("search");
		//Get the values associated with the option if selected
		if (this.doneUpstream) {
			var values = this.cbElement.val() ? this.cbElement.val().split(',') : [];
			var displayName = this.displayField;
			for (ii=0; ii<values.length; ii+=2) {
				valueName = values[ii];
				value = values[ii+1];
				context = SOLN.storeVariable(displayName,valueName,value, context);
			}
			//Handle the sticky value
			this.stickyValue = values[1];
			if (this.solnns) {
				//If a varname is defined place the selection in local storage
				SOLN.stickSelection(this.solnns, this.stickyValue);
				context = SOLN.storeVariable(this.solnns, null, this.stickyValue, context);
			}
			return context;
		}
		else {
			return context;
		}
	},
	onChange: function() {
		this.pushContextToChildren();
	},
	onBeforeJobDispatched: function(search) {
		search.setMinimumStatusBuckets(1);
		search.setRequiredFields(this.requiredFields);
	},
	pushContextToChildren: function($super, explicitContext) {
		this.withEachDescendant(function(module) {
			module.dispatchAlreadyInProgress = false;
		});
		return $super(explicitContext);
	},
	isReadyForContextPush: function($super) {
		if (!(this.doneUpstream)) {
			return Splunk.Module.DEFER;
		}
		if (this.gettingResults) {
			return Splunk.Module.DEFER;
		}
		return $super();
	},
	resetUI: function() {} //Just so splunk stops bitching at me
});
