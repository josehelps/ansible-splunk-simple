require([
    "splunkjs/mvc",
    "underscore",
    "jquery",
    "splunkjs/mvc/simplexml",
    "splunkjs/mvc/simplexml/urltokenmodel",
    "splunkjs/mvc/headerview",
    "splunkjs/mvc/footerview",
    "splunkjs/mvc/utils",
    "splunkjs/mvc/searchmanager",
    "splunkjs/mvc/timelineview",
    "splunkjs/mvc/searchcontrolsview",
    "splunkjs/mvc/eventsviewerview",
    "splunkjs/mvc/postprocessmanager",
    "splunkjs/mvc/simpleform/formutils",
    "splunkjs/mvc/simpleform/input/dropdown",
    "splunkjs/mvc/simpleform/input/text",
    "splunkjs/mvc/simpleform/input/timerange",
    "splunkjs/mvc/simpleform/input/submit",
    "app-components/incident_review/button_group/ButtonGroupView",
    "app-components/incident_review/button_group/ButtonGroupInput",
    "app-components/incident_review/eventsviewer/IREventsViewerView",
    "css!app-css/incident_review",
    "bootstrap.button"
    ],
    function(
        mvc,
        _,
        $,
        DashboardController,
        UrlTokenModel,
        HeaderView,
        FooterView,
        utils,
        SearchManager,
        Timeline,
        SearchControls,
        EventsViewer,
        PostProcessManager,
        FormUtils,
        DropdownInput,
        TextInput,
        TimeRangeInput,
        SubmitButton,
        ButtonGroup,
        ButtonGroupInput,
        IREventsViewer ) {

        var pageLoading = true;


        // 
        // TOKENS
        //
        
        // Create token namespaces
        var urlTokenModel = new UrlTokenModel();
        mvc.Components.registerInstance('url', urlTokenModel);
        var defaultTokenModel = mvc.Components.getInstance('default', {create: true});
        var submittedTokenModel = mvc.Components.getInstance('submitted', {create: true});

        /*
        Handle re-direct (drilldown) from other pages.  The designated convention -- "form.selected_urgency=<urgency>" is expected as part of the URL param value.
        This dashboard's urgency filter (ButtonGroupView) disables the corresponding urgency from the search.
        Since other pages expect the param passed to enable/choose the selection, we need to provide logic to disable the other urgencies or the set complement.
        */
        var selectedUrgency = urlTokenModel.attributes["form.selected_urgency"];
        var toDisableUrgencyList = ["unknown", "informational", "low", "medium", "high", "critical"];
        
        if (selectedUrgency) {
            console.log("selected_urgency:", selectedUrgency);
            
            //remove the enabled urgency from the to-disable urgency list
            toDisableUrgencyList.splice( toDisableUrgencyList.indexOf( selectedUrgency ), 1 );
            
            //add the remaining to-disable urgencies to URL token 'form.new_urgency_count_form' as expected by the ButtonGroupView
            urlTokenModel.attributes["form.new_urgency_count_form"] = toDisableUrgencyList;

            /*
            Remove/clear selected_urgency from the URL after it's been converted to form.new_urgency_count_form
            This allows refresh with any changes to new form.new_urgency_count_form values.
            */
            urlTokenModel.attributes["form.selected_urgency"] = undefined;
        }   

        //Continue setting token models
        urlTokenModel.on('url:navigate', function() {
            defaultTokenModel.set(urlTokenModel.toJSON());
            if (!_.isEmpty(urlTokenModel.toJSON()) && !_.all(urlTokenModel.toJSON(), _.isUndefined)) {
                submitTokens();
            } else {
                submittedTokenModel.clear();
            }
        });

        // Initialize tokens
        defaultTokenModel.set(urlTokenModel.toJSON());

        function submitTokens() {
            // Copy the contents of the defaultTokenModel to the submittedTokenModel and urlTokenModel
            FormUtils.submitForm({ replaceState: pageLoading });
        }

        function setToken(name, value) {
            defaultTokenModel.set(name, value);
            submittedTokenModel.set(name, value);
        }

        function unsetToken(name) {
            defaultTokenModel.unset(name);
            submittedTokenModel.unset(name);
        }

        //
        // SPLUNK HEADER AND FOOTER
        //

        new HeaderView({
          id: 'header',
          section: 'dashboards',
          el: $('.header'),
          acceleratedAppNav: true
        }, {tokens: true}).render();

        new FooterView({
          id: 'footer',
          el: $('.footer')
        }, {tokens: true}).render();

        var managerMainSearch = new SearchManager({
            "id": "id-main-search",
            "earliest_time": "$earliest$",
            "latest_time": "$latest$",
            "search":'`notable` | search NOT `suppression` | search $new_urgency_token$ $status$ $owner$ $rule_name$ $security_domain$ $srch$ | eventstats count(eval(urgency="critical")) as _***critical, count(eval(urgency="high")) as _***high, count(eval(urgency="medium")) as _***medium, count(eval(urgency="low")) as _***low, count(eval(urgency="informational")) as _***informational | fillnull value="unknown" governance',
            "cancelOnUnload": true,
            "status_buckets": 300,
            "autostart":true,
            "app": utils.getCurrentApp(),
            "auto_cancel": 90,
            "preview": true
        }, {tokens: true, tokenNamespace: "submitted"});


        var managerPostProcess = new PostProcessManager({
            "id":"id-post-process",
            "managerid":"id-main-search",
            "search":'head 1 | table _***critical, _***high, _***medium, _***low, _***informational | transpose | rename column as hidden_urgency, "row 1" as new_count | eval new_urgency_value=ltrim(hidden_urgency, "_***") | eval new_urgency_label=new_urgency_value.":".new_count'
        }, {tokens: true, tokenNamespace: "submitted"}); 


        var irTimeline = new Timeline({
            "id": "ir_timeline",
            "managerid": "id-main-search",
            "el": $("#timeline_div")
        }).render();

        var irEventsViewer = new IREventsViewer({
            id: "ir_events_viewer",
            managerid: "id-main-search",
            el: $("#event-viewer-body")
        }).render();

        var irSearchControls = new SearchControls({
            "id": "ir_search_controls",
            "managerid": "id-main-search",
            "el": $("#search_controls_div")
        }).render();

        // Update the search manager when the timeline changes
        irTimeline.on("change", function() {
            managerMainSearch.search.set(irTimeline.val());
        });

        var status_filter = new DropdownInput({
            "label":"Status",
            "id": "status_filter",
            "choices": [
                {"label": "All", "value": ""}
            ],
            "selectFirstChoice": false,
            "labelField": "status_label",
            "default": "",
            "suffix": "\"",
            "valueField": "status",
            "prefix": "status=\"",
            "value": "$form.status$",
            "managerid": "search1",
            "showClearButton": true,
            "el": $('#status_filter')
        }, {tokens: true}).render();

        status_filter.on("change", function(newValue) {
            FormUtils.handleValueChange(status_filter);
        });

        // Populating search for field 'status_filter'
        var search1 = new SearchManager({
            "id": "search1",
            "search": "|`reviewstatuses` | `reviewstatus_exclusions` | sort + status",
            "earliest_time": "",
            "status_buckets": 0,
            "cancelOnUnload": true,
            "latest_time": "+0s",
            "app": utils.getCurrentApp(),
            "auto_cancel": 90,
            "preview": true,
            "runWhenTimeIsUndefined": false
        }, {tokens: true});


        var owner_filter = new DropdownInput({
            "label":"Owner",
            "id": "owner_filter",
            "choices": [
                {"label": "All", "value": ""}
            ],
            "selectFirstChoice": false,
            "labelField": "owner_realname",
            "default": "",
            "suffix": "\"",
            "valueField": "owner",
            "prefix": "owner=\"",
            "value": "$form.owner$",
            "managerid": "search2",
            "showClearButton": true,
            "el": $('#owner_filter')
        }, {tokens: true}).render();

        owner_filter.on("change", function(newValue) {
            FormUtils.handleValueChange(owner_filter);
        });

        // Populating search for field 'owner_filter'
        var search2 = new SearchManager({
            "id": "search2",
            "search": "| rest /services/authentication/current-context | fields username,realname | rename username as owner | eval sort=100 | inputlookup append=T notable_owners_lookup | rename realname as owner_realname | eval owner_realname=if(isnull(owner_realname),owner,owner_realname) | sort -sort,+owner_realname | dedup owner",
            "earliest_time": "",
            "status_buckets": 0,
            "cancelOnUnload": true,
            "latest_time": "+0s",
            "app": utils.getCurrentApp(),
            "auto_cancel": 90,
            "preview": true,
            "runWhenTimeIsUndefined": false
        }, {tokens: true});

        var domain_filter = new DropdownInput({
            "label":"Security Domain",
            "id": "domain_filter",
            "choices": [
                {"label": "All", "value": ""}
            ],
            "selectFirstChoice": false,
            "labelField": "security_domain_label",
            "default": "",
            "suffix": "\"",
            "valueField": "security_domain",
            "prefix": "security_domain=\"",
            "value": "$form.security_domain$",
            "managerid": "search3",
            "showClearButton": true,
            "el": $('#domain_filter')
        }, {tokens: true}).render();

        domain_filter.on("change", function(newValue) {
            FormUtils.handleValueChange(domain_filter);
        });

        // Populating search for field 'domain_filter'
        var search3 = new SearchManager({
            "id": "search3",
            "search": "| `security_domains` | search is_expected=true",
            "earliest_time": "",
            "status_buckets": 0,
            "cancelOnUnload": true,
            "latest_time": "+0s",
            "app": utils.getCurrentApp(),
            "auto_cancel": 90,
            "preview": true,
            "runWhenTimeIsUndefined": false
        }, {tokens: true});

        var rule_filter = new TextInput({
            "label":"Name",
            "id": "rule_filter",
            "default": "",
            "suffix": "\"",
            "prefix": "rule_name=\"",
            "value": "$form.rule_name$",
            "el": $('#rule_filter')
        }, {tokens: true}).render();

        rule_filter.on("change", function(newValue) {
            FormUtils.handleValueChange(rule_filter);
        });

        var srch_filter = new TextInput({
            "label":"Search",
            "id": "srch_filter",
            "default": "",
            "value": "$form.srch$",
            "el": $('#srch_filter')
        }, {tokens: true}).render();

        srch_filter.on("change", function(newValue) {
            FormUtils.handleValueChange(srch_filter);
        });

        var time_filter = new TimeRangeInput({
            "label":"Time",
            "managerid":"id-main-search",
            "id": "time_filter",
            "default": {"latest_time": "now", "earliest_time": "-24h@h"},
            "earliest_time": "$earliest$",
            "latest_time": "$latest$",
            "el": $('#time_filter')
        }, {tokens: true}).render();

        var urgencyButtonGroup = new ButtonGroupInput({
            "label":"Urgency",
            "id": "urgency_buttongroup",
            "managerid":"id-post-process",
            "labelField":"new_urgency_label",
            "valueField":"new_urgency_value",
            "default":"",
            "value":"$form.new_urgency_count_form$",
            "el": $("#button-group")
        },{tokens:true}).render();

        urgencyButtonGroup.on("change", function(newValue){
            FormUtils.handleValueChange(urgencyButtonGroup);

        });

        defaultButtonGroupChoices = [{value: "critical", label:"critical:0" },
                {value: "high", label:"high:0"},
                {value: "medium", label:"medium:0"},
                {value: "low", label:"low:0"},
                {value: "informational", label:"informational:0"}
        ];


        var mainSearchInstance = null;
        var mainSearchResults = null;
        var postProcessInstance = null;
        var postProcessResults = null;

        /*Some debugging notes*/
        managerMainSearch.on("search:start", function() {
            console.log("main search started...");
            mainSearchInstance = mvc.Components.getInstance("id-main-search");
            mainSearchResults = mainSearchInstance.data("events");
        });

        managerPostProcess.on("search:start", function() {
            console.log("post process started...");
            postProcessInstance = mvc.Components.getInstance("id-post-process");
            postProcessResults = postProcessInstance.data("results");
        });

        managerMainSearch.on("search:done", function() {
            console.log("main search done!");
        });

        managerPostProcess.on("search:progress", function() {
            console.log("post process progress", postProcessResults.data());
        });
        managerPostProcess.on("search:done", function() {
            //var postProcessInstance = mvc.Components.getInstance("id-post-process");
            //var postProcessResults = postProcessInstance.data("results");
            console.log("post process done!");
            console.log("post process hasData()?", postProcessResults.hasData());
            console.log("post process results",postProcessResults.data('results'));
            console.log("main search hasData()? ", mainSearchResults.hasData());

            if (!mainSearchResults.hasData() && !postProcessResults.hasData()) {
                mvc.Components.getInstance("urgency_buttongroup").settings.set("choices", defaultButtonGroupChoices);
                console.log("added null choices");
                //console.log("the choices", mvc.Components.getInstance("urgency_buttongroup").settings.get("choices"));
                //console.log("the settings:", mvc.Components.getInstance("urgency_buttongroup").settings);
            } else {
                mvc.Components.getInstance("urgency_buttongroup").settings.set("choices", undefined);
                console.log("removed null choices");
                //console.log("the choices", mvc.Components.getInstance("urgency_buttongroup").settings.get("choices"));
                //console.log("the settings:", mvc.Components.getInstance("urgency_buttongroup").settings);
            }
        });

        /*
        Provide token replacement logic for multi-value urgency filter
        clicked buttons will be tokenized in the search like so:
        search (NOT urgency="low" AND NOT urgency="medium" AND NOT urgency="high")
        */
        function make_new_urgency_count_token(value) {            
            // initialize additional tokens to empty strings
            var urgencyStr = "";
            
            // update tokens if value is positive
            if (value !== null && value !== '') {
                urgencyArr = value.split(" ");
                for (var i = 0; i < urgencyArr.length; i++) {
                    if (urgencyArr[i] !== "") {

                        if (urgencyStr.length < 1) {
                            urgencyStr += "NOT urgency=\"" + urgencyArr[i] + "\"";
                        }   
                        else {
                            urgencyStr += " AND NOT urgency=\"" + urgencyArr[i] + "\"";
                        } 
                    }
                }
                urgencyStr = "(" + urgencyStr + ")";
            }

            // set new tokens
            submittedTokens.set('new_urgency_token',urgencyStr);
        }

        // Get Submitted Tokens
        var submittedTokens = mvc.Components.get('submitted');

        // When the new_urgency_count_form token changes...
        submittedTokens.on('change:new_urgency_count_form', function(){
            // if new_urgency_count_form exists
            if(submittedTokens.has('new_urgency_count_form')) { make_new_urgency_count_token(submittedTokens.get('new_urgency_count_form')); }
        });

        if(submittedTokens.has('new_urgency_count_form')) { make_new_urgency_count_token(submittedTokens.get('new_urgency_count_form')); }

        // 
        // SUBMIT FORM DATA
        //

        var submit = new SubmitButton({
            id: 'submit',
            el: $('#ir_submit_btn')
        }, {tokens: true}).render();

        submit.on("submit", function() {
            submitTokens();
        });

        // Initialize time tokens to default
        if (!defaultTokenModel.has('earliest') && !defaultTokenModel.has('latest')) {
            defaultTokenModel.set({ earliest: '0', latest: '' });
        }

        submitTokens();


        //
        // DASHBOARD READY
        //

        DashboardController.ready();
        pageLoading = false;

        $("body>div.preload").removeClass("preload");
        $("title").text("Incident Review");
        
        /*
        SOLNESS-5092: The mode switcher should always be in smart mode. It should not be allowed to switch modes as fields will disappear and the Incident Review interface will break.
        */
        $(".dropdown-toggle-search-mode").addClass("disabled");
});
