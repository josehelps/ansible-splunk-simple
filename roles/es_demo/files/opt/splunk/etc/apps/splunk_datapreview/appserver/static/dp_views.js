Splunk.namespace("Splunk.preview");


//
// main preview event view renderer
//

Splunk.preview.EventView = function() {
    this.context = ".previewEvents .events_table";
    this._throbber = $('.eventsLoader');
    this._nextEvent = $('.eventTooltip');
    this._noResults = $('.no_results');
};
Splunk.preview.EventView.prototype = {

    render: function(events) {
        $(this.context).empty();
        var table = $(this.context);
        
        var newTHead = $('<thead/>').append(
            $('<tr/>')
                .append($('<th class="event_count_header"/>'))
                .append($('<th class="timestamp_header"/>').text(_('Timestamp')))
                .append($('<th class="event_header"/>').text(_('Event')))
        );
        if (events.length == 0) {
            this.showNoResults();
            return;
        } else {
            this.hideNoResults();
        }
        
        table.append(newTHead);
        
        $.each(events, $.proxy(function(idx, evt) {

            var raw = evt.get('raw');
            var start = evt.get('time_extract_start');
            var end = evt.get('time_extract_end');
            var rawFragment = Splunk.util.escapeHtml(raw.substring(0, start))
                + '<span class="tex">' + Splunk.util.escapeHtml(raw.substring(start, end))
                + '</span>' + Splunk.util.escapeHtml(raw.substring(end));
            
            var time = 'n/a';
            if (evt.get('time')) {
                // a bit ugly way to get the timestamp aligned to splunkd's timezone
                var timeEpoch = parseFloat(evt._fields._time[0].value);
                var tzOffset = Splunk.Globals.timeZone.getOffset(timeEpoch);
                time = format_datetime_microseconds(epochToDateTime(timeEpoch, tzOffset));
            }
            
            //time = time.replace(/(\d{1,2}\/\d{1,2}\/\d{2})/g, '<span>$1</span>');
            
            var gutterColumn = $('<td/>').text(idx+1).addClass('idx');
            if (evt.get('messages').length) {
                var msglist = $('<ul/>');
                $.each(evt.get('messages'), function(ix, msg) {
                    if (msg.code == "TIMESTAMP_STRPTIME_GENERIC_FAIL") {
                        
                        msg.text += " Make sure a prefix pattern is specified if the events don't begin with a timestamp.";
                    }
                    if (msg.text.length) {
                        $('<li/>').text(Splunk.util.escapeHtml(msg.text)).appendTo(msglist);
                    }
                });
                gutterColumn.html(
                    (idx+1)
                    + '<span class="warning-icon" title="'
                    + $('<div/>').append(msglist).html()
                    + '">&nbsp;</span>' 
                );
                this.setWarningClass();
            }
            var row = $('<tr/>')
                .append(gutterColumn)
                .append($('<td/>').text(time).addClass('time'))
                .append($('<td/>').html('<pre>' + rawFragment + '</pre>').addClass('raw'));
            row.appendTo(table);
        }, this));
        $('span.warning-icon', table).tipTip({
            delay: 0,
            fadeIn: 0,
            maxWidth: '500px'
        });
        
        var updateTooltip = $.proxy(function() {
            if ($('.previewEvents tr').eq(1).position().top + $('.previewEvents tr').eq(1).height() > $('.previewEvents').height() && $('.previewEvents tr').eq(2).length == 1) {
                this.showTooltip();
            } else {
                this.hideTooltip();
            }
        },this);
        
        updateTooltip();
        $('.previewEvents').scroll(updateTooltip);
        
        $('#nextEvent').click($.proxy(function(e) {
            $('.previewEvents').scrollTop($('.previewEvents').scrollTop()+$('.previewEvents tr').eq(2).position().top);
        },this));

        setPreviewHeight();
        $(window).resize(setPreviewHeight);
    },
    
    setWarningClass: function() {
        var $previewEvents = $('.previewEvents');
        if ( !$previewEvents.hasClass('has_warnings') ) {
            $previewEvents.addClass('has_warnings');
        }
    },
    
    clear: function() {
        $(this.context).empty();
    },
    
    showThrobber: function() {
        this._throbber.show();
        // prevent event from firing multiple times
        $('.previewSettingsActions a').bind('click', this.disableLink);
    },

    clearThrobber: function() {
        this._throbber.hide();
        // restore links
        $('.previewSettingsActions a').unbind('click', this.disableLink);        
        this.setProgress(0);
    },
    
    showTooltip: function() {
        this._nextEvent.show();
    },
    
    hideTooltip: function() {
        this._nextEvent.hide();
    },

    setProgress: function(percentage) {
        percentage = parseFloat(percentage).toFixed(1);
        this._throbber.text(format_percent(percentage));
    },

    disableLink: function(e) {
        // cancels the event
        e.preventDefault();
        return false;
    },
    
    showNoResults: function() {
        this._noResults.show();
    },
    
    hideNoResults: function() {
        this._noResults.hide();
    }
    
};


Splunk.preview.EventStructView = function() {
    this.context = ".previewEvents .str_events_table";
    this._throbber = $('.eventsLoader');
    this._noResults = $('.no_fields');
    
};
Splunk.preview.EventStructView.prototype = {

    render: function(output) {
        $(this.context).empty();
    
        if (output.fields.length == 0) {
            this.showNoResults();
            return;
        } else {
            this.hideNoResults();
        }

        var table = $('<div/>');
        // Build header
        var newTHead = $('<thead/>').append(
            $('<tr/>')
                .append($('<th class="event_count_header"/>'))
                .append($('<th class="timestamp_header"/>').text(_('Timestamp')))
        );
        $.each(output.fields, $.proxy(function(idx, field) {
            $('tr',newTHead).append($('<th/>').text(field));
        }, this));
        table.append(newTHead);
        
        // Populate table body
        $.each(output.events, $.proxy(function(idx, evt) {
            
            var time = 'n/a';
            if (evt.get('time')) {
                // a bit ugly way to get the timestamp aligned to splunkd's timezone
                var timeEpoch = parseFloat(evt._fields._time[0].value);
                var tzOffset = Splunk.Globals.timeZone.getOffset(timeEpoch);
                time = format_datetime_microseconds(epochToDateTime(timeEpoch, tzOffset));
            }
            
            var gutterColumn = $('<td/>').text(idx+1).addClass('idx');
            if (evt.get('messages').length) {
                var msglist = $('<ul/>');
                $.each(evt.get('messages'), function(ix, msg) {
                    if (msg.text.length) {
                        $('<li/>').text(Splunk.util.escapeHtml(msg.text)).appendTo(msglist);
                    }
                });
                gutterColumn.html(
                    (idx+1)
                    + '<span class="warning-icon" title="'
                    + $('<div/>').append(msglist).html()
                    + '">&nbsp;</span>' 
                );
                this.setWarningClass();
            }

            // Building rows
            // -------------
            var row = $('<tr/>')
                .append(gutterColumn)
                .append($('<td/>').text(time).addClass('time'));
            
            $.each(output.fields, function(idx, field) {            
                // handle multivalue fields
                var vals = evt._fields[field];
                var cellVal;
                
                if (!vals) {
                    cellVal =  _('N/A');
                } else if (vals.length > 1) {
                    var valArray = [];
                    $.each(vals, function(ix, val) {
                        if (!!val.value) {
                            valArray.push(val.value);
                        }
                    });
                    cellVal = valArray.join('<br>');
                } else if (evt._fields[field].length == 1){
                    cellVal = evt._fields[field][0].value
                } 
                
                $('<td/>').html(cellVal).appendTo(row);
            });
            
            row.appendTo(table);
        }, this));
        
        table.children().appendTo($(this.context));
        $('span.warning-icon', $(this.context)).tipTip({
            delay: 0,
            fadeIn: 0,
            maxWidth: '500px'
        });
        
        setPreviewHeight();
        $(window).resize(setPreviewHeight);
    },
    
    setWarningClass: function() {
        var $previewEvents = $('.previewEvents');
        if ( !$previewEvents.hasClass('has_warnings') ) {
            $previewEvents.addClass('has_warnings');
        }
    },
    
    clear: function() {
        $(this.context).empty();
    },
    
    showThrobber: function() {
        this._throbber.show();
        // prevent event from firing multiple times
        $('.previewSettingsActions a').bind('click', this.disableLink);
    },

    clearThrobber: function() {
        this._throbber.hide();
        // restore links
        $('.previewSettingsActions a').unbind('click', this.disableLink);        
        this.setProgress(0);
    },

    setProgress: function(percentage) {
        percentage = parseFloat(percentage);
        this._throbber.text(format_percent(percentage));
    },

    disableLink: function(e) {
        // cancels the event
        e.preventDefault();
        return false;
    },
    
    showNoResults: function() {
        this._noResults.show();
    },
    
    hideNoResults: function() {
        this._noResults.hide();
    }
    
};



//
// Sidebar job metadata renderer
//

Splunk.preview.MetadataView = function() {
    this.context = ".previewMetadata #metadata_body";
};
Splunk.preview.MetadataView.prototype =  {

    render: function(results) {
        
        //
        // render the timeline
        //

        var timeline_data = [];
        var timeline_dates = [];
        var max_count = 0;
        var earliestTime = results.buckets[0].earliest_time;
        var latestTime = results.buckets[results.buckets.length-1].earliest_time;
        
        $.each(results.buckets, function(idx, bucket) {
            timeline_data.push((bucket.total_count == 0 ? null : bucket.total_count));
            timeline_dates.push(format_datetime_microseconds(bucket.earliest_time, 'short'));
            max_count = Math.max(max_count, bucket.total_count);
        });
        
        if (parseInt(results.buckets[0].duration,10) >= 2419200) {
            // buckets longer than a month should only display month and year
            earliestTime = format_date(earliestTime, 'M/yyyy');
            latestTime = format_date(latestTime, 'M/yyyy');
        }
        else {
            earliestTime = format_datetime(earliestTime, 'short');
            latestTime = format_datetime(latestTime, 'short');
        }
        
        this.chart = new Highcharts.Chart({
            chart: {
                renderTo: 'chart_container',
                type: 'column',
                height: 75,
                animation: false,
                spacingTop: 10,
                spacingRight: 5,
                spacingBottom: 10,
                spacingLeft: 1,
                backgroundColor: '#edede7'
            },
            credits: {
                enabled: false
            },
            title: {
                text: null
            },
            legend: {
                enabled: false
            },
            plotOptions: {
                column: {
                    animation: false,
                    shadow: false,
                    groupPadding: 0,
                    pointPadding: 0,
                    borderWidth: 0,
                    minPointLength: 2
                }
            },
            xAxis: {
                title: null,
                categories: timeline_dates,
                labels: {enabled: false},
                lineWidth: 1,
                lineColor: '#999'
            },
            yAxis: {
                title: null,
                gridLineWidth: 0,
                lineWidth: 1,
                lineColor: '#999',
                /* tickPixelInterval: 200, */
                max: max_count,
                labels: {
                    style: {
                        fontSize: '9px',
                        color: '#333'
                    }
                }
            },
            tooltip: {
                borderWidth: 1,
                formatter: function() {
                    return (this.x + ": <b>" + this.y + "</b>");
                },
                style: {
                    padding: '3px'
                }
            },
            series: [{
                name: _('Event count'),
                data: timeline_data
            }],
            colors: [
                {linearGradient: [0, 0, 0, 500], stops: [[0, '#6FAA1A'],[1, '#447800']]}
            ]
        });

        $('#chart_range').empty()
            .append($('<span/>').text(earliestTime).addClass('start_time'))
            .append($('<span/>').text(latestTime).addClass('end_time'));


        //
        // render stats
        //

        $('#stats_num_events').text(format_number(results.stats.count));
        $('#stats_total_bytes').text(format_number(results.file.size));
        $('#stats_bytes_read').text(format_number(results.file.read));
        if (!results.file.isComplete) {
            var note;
            if (results.file.isCompressed) {
                note = _('Only a portion of your compressed file used for preview.');
            } else {
                note = sprintf(
                    _('Only the first %sB used for preview.'),
                   format_number(results.file.read)
                );
            }
            $('#preview_truncate_note').text(note).show();

        } else {
            $('#preview_truncate_note').hide();
        
        }
        
        
        //
        // render linecount table
        //

        var linecounts = $('#metadata_linecounts').html('');
        $.each(results.stats.linecount_table, function(idx, row) {
            linecounts.append($('<tr/>')
                .append($('<td/>').text(format_number(row[0])))
                .append($('<td/>').text(format_number(row[1]) + ' (' + format_percent(row[2]) + ')'))
            );
        });

    },
    
    clear: function() {
       this.clearThrobber();
        if (this.chart && this.chart.destroy && this.chart.renderTo) {
            this.chart.destroy();
        }
        $('#chart_range').html('');
        $('#stats_num_events').text('');
        $('#stats_total_bytes').text('');
        $('#stats_bytes_read').text('');
        $('#metadata_linecounts').html('');
        $('#preview_truncate_note').html('').hide();
    },
    
    showThrobber: function() {
        $('.metaLoader').show();
    },

    clearThrobber: function() {
        $('.metaLoader').hide();
    }


};



//
// props.conf configurator
//

Splunk.preview.ConfigurationView = function() {
    this.context = ".previewConfig";
    this.settingsShown = false;
    this.advancedMode = false;
    this.simpleFormData = null;
    this.advancedFormData = null;
    this._inheritedText = '';
    this.displayMode = 0;
    this.EXTRACTION_DELIMITER = {'csv':',', 'tsv':'tab', 'psv':'|'};
};
Splunk.preview.ConfigurationView.prototype = {

    render: function(tz_data) {
        var that = this;
        // initialize tabs
        function switch_tabs(obj) {
            $('.tab-content').hide();
            $('.tabs a').removeClass("selected");
        
            $('#'+obj.attr('rel')).show();
            obj.addClass("selected");        
        };
        $('.tabs a').click($.proxy(function(evt){
            switch_tabs($(evt.target));
            this.advancedMode = (evt.target.rel == 'tab_advanced');
        }, this));
        switch_tabs($('.defaulttab'));
        
        // handler for the line-breaking switcher
        $('input[name=lb_type]').change(function(){
            if ( $(this).val() == 'regex' ) {
                $('#lb_line_breaker').prop('disabled', false);
            } else {
                $('#lb_line_breaker').prop('disabled', true);

            }
        }); 
        
        // timestamp radio handler
        $('input[name=ts_type]').change(function(){
            $('#ts_type_curtime_val').val('');
            $('#ts_time_prefix').prop('disabled', true);
            $('input#ts_extends').prop('checked', false);
            $('input#ts_extends').prop('disabled', false);
            $('#ts_max_lookahead').prop('disabled', true);
            $('#chars_pattern').text(_('chars into the event'));
            $('#timestamp_neverextends').show();
            $('input,select','#timestamp_format').prop('disabled', false);

            if ($(this).val() == 'pre_pattern') {
                $('#ts_time_prefix').prop('disabled', false);
                $('#chars_pattern').text(_('chars past the pattern'));
            } else if ($(this).val() == 'never_more_into') {
                $('#ts_max_lookahead_into').prop('disabled', false);
            } else if ($(this).val() == 'curtime') {
                $('#ts_type_curtime_val').prop('disabled', false);
                $('#ts_type_curtime_val').val('CURRENT');
                $('input#ts_extends').prop('disabled', true);
                $('#timestamp_neverextends').hide();
                $('input,select','#timestamp_format').prop('disabled', true);
            }
        });
        
        // structured timestamp radio handler
        $('input[name=str_ts_type]').change(function(){
            //$('#str_ts_type_curtime_val').prop('disabled', true);
            $('#str_ts_type_curtime_val').val('');
            $('#str_timestamp_loc_auto').prop('disabled', true);
            $('#str_timestamp_fields').prop('disabled', true);
            $('input,select','#timestamp_format').prop('disabled', false);
            if ($(this).val() == '') {
                $('#str_timestamp_loc_auto').prop('disabled', false);
            } else if ($(this).val() == 'struct_fields') {
                $('#str_timestamp_fields').prop('disabled', false);
            } else if ($(this).val() == 'curtime') {
                $('#str_ts_type_curtime_val').prop('disabled', false);
                $('#str_ts_type_curtime_val').val('current');
                $('input,select','#timestamp_format').prop('disabled', true);
            }
        });
        
        $('input#ts_extends').click(function() {
            if ($('input#ts_extends').is(':checked')) {
                $('input#ts_max_lookahead').prop('disabled', false).removeClass('disabled_text');
            } else {
                $('input#ts_max_lookahead').prop('disabled', true).addClass('disabled_text');
            }
        });
        
        // structured headers radio handler
        $('input[name=hdr_type]').change(function(){
            $('#hdr_auto').prop('disabled', true);
            $('#hdr_pattern').prop('disabled', true);
            $('#hdr_line').prop('disabled', true);
            $('#hdr_direct').prop('disabled', true);
            if ($(this).val() == '') {
                $('#hdr_auto').prop('disabled', false);
            } else if ($(this).val() == 'pattern') {
                $('#hdr_pattern').prop('disabled', false);
            } else if ($(this).val() == 'line') {
                $('#hdr_line').prop('disabled', false);
            } else if ($(this).val() == 'direct') {
                $('#hdr_direct').prop('disabled', false);
            }
        });
        
    
        $('#settings_layout').show();
        this.settingsShown = true;
        
        $('#simple_config_form').unbind('keypress').bind('keypress', function(event){
            if(event.keyCode==13){
                ctrlr.handleApply(event);
            }
        });
        
        $('#str_tab').parent('li').hide();
        $('#str_tab_headers').parent('li').hide();
        $('#ts_tab').parent('li').show();
        $('#timestamp_location').hide();
        $('input','#timestamp_location').prop('disabled',true);            
        $('#str_timestamp_location').hide();
        $('input','#str_timestamp_location').prop('disabled',true);
        $('#timestamp_format').show();
        
        if (this.displayMode == 0) { // unstructured
            $('#eb_tab').parent('li').show();
            $('#str_tab').parent('li').hide();
            $('#str_tab_headers').parent('li').hide();
            
            $('.events_table').show();
            $('.str_events_table').hide();
            
            $('#timestamp_location').show();
            $('input','#timestamp_location').prop('disabled',false);            
            $('#str_timestamp_location').hide();
            switch_tabs($('#eb_tab'));
        
        } else if (this.displayMode == 1) { // tabular
            $('#eb_tab').parent('li').hide();
            $('#str_tab').parent('li').show();
            $('#str_tab_headers').parent('li').show();
            
            $('.events_table').hide();
            $('.eventTooltip').hide();
            $('.str_events_table').show();
            
            $('#str_timestamp_location').show();
            $('input','#str_timestamp_location').prop('disabled',false);
            switch_tabs($('#str_tab'));
        } else if (this.displayMode == 2) { // JSON
            $('#eb_tab').parent('li').hide();
            $('#str_tab').parent('li').hide();
            $('#str_tab_headers').parent('li').hide();
            
            $('.events_table').hide();
            $('.eventTooltip').hide();
            $('.str_events_table').show();
            
            $('#str_timestamp_location').show();
            $('input','#str_timestamp_location').prop('disabled',false);
            switch_tabs($('#ts_tab'));
        } else if (this.displayMode == 3) { // w3c
            $('#eb_tab').parent('li').hide();
            $('#str_tab').parent('li').hide();
            $('#ts_tab').parent('li').hide();
            $('#str_tab_headers').parent('li').hide();
            
            $('.events_table').hide();
            $('.eventTooltip').hide();
            $('.str_events_table').show();
            
            $('#timestamp_format').hide();
            switch_tabs($('#adv_tab'));
        }
        
        $('span.info-icon', this.context).tipTip({
            delay: 0,
            fadeIn: 0,
            maxWidth: '500px',
            defaultPosition: 'right'
        });
        
        $('#str_field_delimiter_select').on('change', function() {
            if ($(this).val() == 'custom') {
                $('#str_field_delimiter').val('');
                $('#str_field_delimiter').show();
                $('#hdr_field_delimiter').val('');
                $('#hdr_field_delimiter').show();
            } else {
                $('#str_field_delimiter').val($(this).val());
                $('#str_field_delimiter').hide();
                $('#hdr_field_delimiter').val($(this).val());
                $('#hdr_field_delimiter').hide();
            }
        });
        
        $('#hdr_field_delimiter_select').on('change', function() {
            if ($(this).val() == 'custom') {
                $('#hdr_field_delimiter').val('');
                $('#hdr_field_delimiter').show();
            } else {
                $('#hdr_field_delimiter').val($(this).val());
                $('#hdr_field_delimiter').hide();
            }
        });

    },
    
    // returns form values serialized as JSON object
    getSimpleSettings: function() {
        var output = {};
        var serialized = $("#simple_config_form").serializeArray();
        $.each(serialized, function() {
            if (output[this.name] !== undefined) {
                if (!output[this.name].push) {
                    output[this.name] = [output[this.name]];
                }
                output[this.name].push(this.value || '');
            } else {
                output[this.name] = this.value || '';
            }
        });
        return output;
    },
    
    getAdvancedSettings: function() {
        //SPL-68420 remove leading and trailing spaces for key=val pair
        var str =  $("#text_props_advanced").val();
        var n = str.indexOf("=");
        if(n < 2)  return str;
        return str.substr(0, n).trim() + "=" + str.substr(n + 1).trim() ;
    },
    
    resetSettings: function() {
        if (this.isAdvancedMode()) {
            $("#text_props_advanced").val('');
        } else {
            $('#simple_config_form')[0].reset();
            $('.disabled_by_default').prop('disabled',true);
        }
        this.updateSettings();
    },
    
    updateSettings: function() {
        this.advancedFormData = this.getAdvancedSettings();
        this.simpleFormData = this.getSimpleSettings();
    },
    
    settingsChanged: function() {
        return (
            this.advancedFormData != this.getAdvancedSettings()
            || !Splunk.util.objectSimilarity(this.simpleFormData, this.getSimpleSettings())
        );
    },
    
    isAdvancedMode: function() {
        return this.advancedMode;
    },
    
    setDisplayMode: function(mode) {
        $('#display_mode_switch').val(mode);
        this.displayMode = mode;
        this.render();
    },
    
    disableDisplayMode: function() {
        var selected = $('#display_mode_switch option:selected').text().toLowerCase() + ': ';
        $('#display_mode_switch').replaceWith(selected);
    },
    
    // handles the initial set of properties determined by the preview backend
    loadProps: function(settings) {
        var rows = [];
        var k;
        var isFirst = true;
        for (k in settings.toSourcetypeSettings('explicit')) {
            if (isFirst) {
                rows.push(_('# your settings'));
                isFirst = false;
            }       
            var val = settings.get(k);
            if (val === '' || val === null) {
                continue;
            }
            rows.push(k + '=' + val);
        }

        if (rows.length > 0) {
            rows.push('');
        }

        isFirst = true;
        for (k in settings.toSourcetypeSettings('preset')) {
            if (isFirst) {
                rows.push(_('# set by detected source type'));
                isFirst = false;
            }                
            var val = settings.get(k);
            if (val === '' || val === null) {
                continue;
            }
            rows.push(k + '=' + val);
        }

        // initialize advanced form
        $('#text_inherited_advanced').val(rows.join('\n'));
        
        
        // iterate through known settings and initialize simple forms
        for (k in settings.toSourcetypeSettings('merged')) {
            var val = (settings.get(k) != null ? settings.get(k) : '');
            if (k == 'SHOULD_LINEMERGE') {
                if (val !== '') {
                    $('input#lb_type_single').prop('checked',true);
                }
            } else if (k == 'BREAK_ONLY_BEFORE') {
                if (val !== '') {
                    $('input#radio_regex').prop('checked',true);
                    $('input[name=BREAK_ONLY_BEFORE]').val(val);
                    $('input[name=BREAK_ONLY_BEFORE]').prop('disabled',false);
                }
            } else if (k == 'TIME_PREFIX') {
                if (val !== '') {
                    $('input#ts_type_pattern').prop('checked',true);
                    $('input#ts_time_prefix').val(val);
                    $('input#ts_time_prefix').prop('disabled',false);
                }
            } else if (k == 'MAX_TIMESTAMP_LOOKAHEAD') {
                if (settings.get('TIME_PREFIX')) {
                    $('input#ts_prefaced_past').prop('checked',true);
                    $('input#ts_max_lookahead_past').val(val);
                    $('input#ts_max_lookahead_past').prop('disabled',false);
                } else {
                    $('input#ts_type_never').prop('checked',true);
                    $('input#ts_max_lookahead_into').val(val);
                    $('input#ts_max_lookahead_into').prop('disabled',false);
                }
            } else if (k == 'TIMESTAMP_FIELDS') {
                if (val !== "") {
                    $('input#str_ts_struct_fields').prop('checked',true);
                    $('input#str_timestamp_fields').prop('disabled',false);
                    $('input#str_timestamp_fields').val(val);
                }
            } else if (k == 'DATETIME_CONFIG') {
                if (val.toLowerCase() == 'current') {
                    $('input#ts_type_curtime').prop('checked',true);
                    $('input#str_ts_type_curtime').prop('checked',true);
                    $('input,select','#timestamp_format').prop('disabled', true);
                }
            } else if (k == 'TIME_FORMAT') {
                $('input#ts_time_format').val(val);
            } else if (k == 'TZ') {
                $('select#ts_tz').find('option[value="'+val+'"]').prop("selected",true);
            } else if (k == 'INDEXED_EXTRACTIONS') {
                if (!val) {
                    continue;
                }
                var delim = this.EXTRACTION_DELIMITER[val.toLowerCase()];
                if (!settings.get('FIELD_DELIMITER')) {
                    this._setCustomPopdown(delim, '#str_field_delimiter_select', '#str_field_delimiter');
                }
                if (!settings.get('HEADER_FIELD_DELIMITER')) {
                    this._setCustomPopdown(delim, '#hdr_field_delimiter_select', '#hdr_field_delimiter');
                }
            } else if (k == 'PREAMBLE_REGEX') {
                $('input#str_preamble_regex').val(val);
            } else if (k == 'FIELD_DELIMITER') {
                this._setCustomPopdown(val, '#str_field_delimiter_select', '#str_field_delimiter');
            } else if (k == 'FIELD_QUOTE') {
                $('select#str_field_quote').find('option[value="'+val+'"]').prop("selected",true);
            } else if (k == 'HEADER_FIELD_DELIMITER') {
                this._setCustomPopdown(val, '#hdr_field_delimiter_select', '#hdr_field_delimiter');
            } else if (k == 'HEADER_FIELD_QUOTE') {
                $('select#hdr_field_quote').find('option[value="'+val+'"]').prop("selected",true);
            } 
        }
        
        // Headers - Location radio:
        //  clear all, then select and populate in order of a setting's priority
        $('input#hdr_direct').val('');
        $('input#hdr_line').val('');
        $('input#hdr_pattern').val('');
        if (settings.get('FIELD_NAMES')) {
            $('input#hdr_direct_radio').prop('checked',true);
            $('input#hdr_direct').prop('disabled',false);
            $('input#hdr_direct').val(settings.get('FIELD_NAMES'));
        } else if (settings.get('HEADER_FIELD_LINE_NUMBER')) {
            if (settings.get('HEADER_FIELD_LINE_NUMBER') == 0) {
                $('input#hdr_auto_radio').prop('checked',true);
            } else {
                $('input#hdr_line_radio').prop('checked',true);
                $('input#hdr_line').prop('disabled',false);
                $('input#hdr_line').val(settings.get('HEADER_FIELD_LINE_NUMBER'));
            }
        } else if (settings.get('FIELD_HEADER_REGEX')) {
            $('input#hdr_pattern_radio').prop('checked',true);
            $('input#hdr_pattern').prop('disabled',false);
            $('input#hdr_pattern').val(settings.get('FIELD_HEADER_REGEX'));
        }
        
        
    },
    
    _setCustomPopdown: function(val, $select, $textfield) {
        if (val == '' || typeof val == 'undefined') {
            // if empty or undefined - select the first
            $('option', $select).first().prop("selected",true);
            return;
        }
        var vals = $($select+'>option').map(function() { return $(this).val(); });
        if ($.inArray(val, vals) > -1) {
            // if value is found among select's values, then pick it in the select. 
            $('option', $select).filter(function() { return $(this).val() == val; }).prop("selected",true);
            $($textfield).hide();
        } else {
            // otherwise choose 'custom' value of select and show the custom textfield
            $($select).find('option[value="custom"]').attr("selected",true);
            $($textfield).val(val);
            $($textfield).show();
        }
    },
    
    clear: function() {
        $(this.context).empty();
    }
};

//
// popup manager for initial sourcetype selection mode
//

Splunk.preview.SourcetypeModeView = function() {
    this.context = "#st_select_popup";
    this.radioset = "st_type";
    this.presets = "#st_type_preset";
    this.popupInstance = null;
    this.presetValues = [];
    this.autoSourcetype = null;
};
Splunk.preview.SourcetypeModeView.prototype = {

    render: function(ctrlr) {
        $('.errors', this.context).hide();

        this.popupInstance = new Splunk.Popup($(this.context), {
            title: _('Set source type'),
            pclass: 'set_st_popup',
            buttons: [
                {
                    label: _('Cancel'),
                    type: 'secondary',
                    callback: function() {
                        ctrlr.goFilePicker();
                    }
                },
                {
                    label: _('Continue'),
                    type: 'primary',
                    callback: $.proxy(this.handleSubmit, this)
                }
            ]
        });

        var container = this.popupInstance.getPopup();
        $(document).unbind('keydown.Popup');
        
        // build the preset sourcetype list
        var select = $(this.presets, container);

        $.map(this.presetValues, function(item) {
            select.append($('<option/>').val(item).text(item));
        });
        select.bind('change', function() {
            $('#st_type_existing', container).prop('checked', true);
        });

        if (this.autoSourcetype) {
            
            // set the auto sourcetype, if any
            $('#st_type_auto_value', container).text(this.autoSourcetype);
            $('#st_type_auto', container).prop('checked', true);

        } else {
            
            $('#st_type_auto_wrapper', container).hide();
            $('#st_type_not_found_message', container).show();
            $('#st_type_new', container).prop('checked', true);

        }

        // SPL-44000 IE8 fix
        $('label', this.context).click($.proxy(function(e){ 
            e.preventDefault(); 
            $("#"+$(e.target).attr("for"), this.context).click().change();
        },this));
        
    },

    getSelectionValue: function() {
        return $('input[name=' + this.radioset + ']:checked', this.popupInstance.getPopup()).val();
    },
    
    getPresetValue: function() {
        return $(this.presets + ' option:selected').val();
    },

    handleSubmit: function(evt) {
        if (this.getSelectionValue() == "existing" && this.getPresetValue() == "")  {
            $('.errors', this.context).text(_('No existing source types selected.')).show();
            return false;
        }
        $(this).trigger('submit');
        this.close();
    },

    bind: function(evt, callback) {
        return $(this).bind(evt, callback);
    },
    
    close: function() {
        this.popupInstance.destroyPopup();
    }

};



//
// popup manager for sourcetype save dialog
//

Splunk.preview.SourcetypeConfirmView = function() {
    this.context = "#st_confirm_popup";
    this.popupInstance = null;
};
Splunk.preview.SourcetypeConfirmView.prototype = {

    render: function(settings, continue_to, return_to) {
        $('.errors', this.context).hide();        
        this.popupInstance = new Splunk.Popup($(this.context), {
            title: _('Review settings'),
            buttons: [
                {
                    label: _('Cancel'),
                    type: 'secondary',
                    callback: function() { 
                        return this.close();
                    }.bind(this)
                },             
                {
                    label: _('Exit without saving'),
                    type: 'secondary',
                    callback: function() { 
                        window.document.location = return_to;
                    }
                },
                {
                    label: _('Save source type'),
                    type: 'primary',
                    callback: $.proxy(ctrlr.handleSubmit, ctrlr)
                }
            ]
        });

        var container = this.popupInstance.getPopup();
        $(document).unbind('keydown.Popup');
        $('#st_confirm_form').unbind('keypress').bind('keypress', function(event){
            if(event.keyCode==13){
                event.preventDefault();
                ctrlr.handleSubmit();
            }
        });
                
        var list = [];
        var k;
        for (k in settings.toSourcetypeSettings()) {
            var val = settings.get(k);
            if (val === '') {
                continue;
            }
            list.push(k + '=' + val);
        }
        $('#st_props', container).val('[]\n' + list.join('\n'));
        
        list = [];
        for (k in settings.toSourcetypeSettings('inherited')) {
            var val = settings.get(k);
            if (val === '') {
                continue;
            }
            list.push(k + '=' + val);
        }
        $('#text_props_default', container).val(list.join('\n'));
        
        
        $('#st_name', container).bind('keyup', function(evt) {
            var name = $('#st_name, container').val().replace(/\n/g,'');
            var propsText = $('#st_props', container).val().replace(/^\[(.*)\]/, '['+name+']');
            $('#st_props', container).val(propsText);
        });
        
        $('#st_props_default', container).click(function() {
            $('#text_props_default', container).toggle();
        });       
    },
    
    close: function() {
        this.popupInstance.destroyPopup();
    },
    
    showError: function(err) {
        $('.errors').text(err).show();
        setPreviewHeight();
    },
    
    clearErrors: function() {
        $('.errors', this.context).empty().hide();
        setPreviewHeight();
    }
    

};

//
// popup manager for sourcetype success dialog
//

Splunk.preview.SourcetypeSuccessView = function() {
    this.context = "#st_success_popup";
    this.popupInstance = null;
};
Splunk.preview.SourcetypeSuccessView.prototype = {

    render: function(st_name, continue_to, return_to) {
        $('span#success_msg', this.context).append(Splunk.util.escapeHtml(st_name));
        this.popupInstance = new Splunk.Popup($(this.context), {
            title: _('Sourcetype saved'),
            buttons: [
                {
                    label: _('Exit'),
                    type: 'secondary',
                    callback: function() { 
                        window.document.location = return_to;
                    }
                },
                {
                    label: _('Create input'),
                    type: 'primary',
                    callback: function() { 
                        window.document.location = continue_to;
                    }
                }
            ]
        });
        $(document).unbind('keydown.Popup');
    },
    
    close: function() {
        this.popupInstance.destroyPopup();
    }
    
};


var setPreviewHeight = function() {
    var $preview = $('.preview'), 
    $header = $('.header'), 
    $messages = $('.messaging'),
    $error = $('#main_error_panel');
    var newHeight = $(window).height() - $header.height() - $messages.height() - $error.height();
    $preview.height( newHeight + 'px');
};
