//http://www.mail-archive.com/discuss@jquery.com/msg04261.html
jQuery.fn.reverse = [].reverse;

// sorts a jQuery list obj with sortDescending a bool
function sortList(list, sortDescending) {
    var listitems = list.children('li:visible').get();
    listitems.sort(function(a, b) {
       var compA = $(a).text().toUpperCase();
       var compB = $(b).text().toUpperCase();
       if (sortDescending) {
          return (compA < compB) ? 1 : (compA > compB) ? -1 : 0;
       } else {
          return (compA < compB) ? -1 : (compA > compB) ? 1 : 0;
       }
    });
    $.each(listitems, function(idx, itm){ 
        list.append(itm); 
    });
}

// adds a specific attr set to an input object 
// and appends it to the provided helper
function addInput(helper, attrObj, value) {
    if (!( $(helper).children('input').size() > 0 )) {
        $('<input>')
            .attr(attrObj)
            .val(value)
            .appendTo(helper);
    }
}

function filterText(search_text, input, target) {
    var regex = new RegExp(search_text.replace('*', '.*'), 'i');
    $(target).children().each( function () {
        if ($(this).html().search(regex) == -1) {
            $(this).css('display', 'none');
        } else {
            $(this).css('display', '');
        }
    });
}

function toggleSort(list, target, desc) {
    desc = !desc;
    sortList(list, desc);
    if (desc === false) {
        $(target).text('Sort (desc)');
    } else {
        $(target).text('Sort (asc)');
    }
    return desc;
}

function isVisible(text, filter_text) {
    if (!(filter_text) || filter_text == null || filter_text == '') {
        return true;
    }
    var regex = new RegExp(filter_text.replace('*', '.*'), 'i');
    if (text.search(regex) == -1){
        return false;  
    } else {
        return true;
    } 
}

function bindLists() {
    $('#winevtlog_enabled li').unbind('click').click(function (event){
        enabledToDisabled(event.target);
        event.preventDefault();
    }).disableSelection();
    $('#winevtlog_disabled li').unbind('click').click(function (event){
        disabledToEnabled(event.target);
        event.preventDefault();
    }).disableSelection();
}

function enabledToDisabled(target) {
    var id = '#' + $(target).attr('id');
    $(target).parent().remove(id);
    $(target).children().remove();
    $(target).unbind('click').click( function(event) {
        disabledToEnabled(event.target);
    });
    if (!(isVisible($(target).html(), $('#disable_filter').val()))) {
        $(target).css('display', 'none');
    }
    $('#winevtlog_disabled').prepend(target);
}

function disabledToEnabled(target) {
    var id = '#' + $(target).attr('id');
    $(target).parent().remove(id);
    addInput(target, {'type':'hidden','name':'winevtlogs'}, $(target).attr('id'));
    $(target).unbind('click').click( function(event) {
        enabledToDisabled(event.target);
    });
    if (!(isVisible($(target).html(), $('#enable_filter').val()))) {
        $(target).css('display', 'none');
    }
    $('#winevtlog_enabled').prepend(target);
}

$(document).ready(function (){
    var enable_desc = false,
        disable_desc = false,
        search_text = {'enabled' : null, 'disabled': null},
        snapshot = {'enabled': null, 'disabled': null, 'radio': null};
    snapshot.enabled = $('#winevtlog_enabled').html();
    snapshot.disabled = $('#winevtlog_disabled').html();
    snapshot.radio = $('input[type=radio]:checked');
    // disable buttons on form submit and change text
    $('#windows_form').submit(function (event){
	if ($('#winevtlog_enabled li').size() > 63) {
            $('<p>').attr('class', 'errorText')
                 .text('Error: cannot monitor more than 63 event logs on one machine.')
                 .appendTo($('.WindowsError')[0]); 
	    event.preventDefault();
        } else {
            $('#windows_submit').attr('disabled', 'disabled').val('Please wait...')
                .next().attr('disabled', 'disabled');
        }
    });
    // need to override reset behavior to handle evtlogs and not
    // break the filter inputs functionality (reset will nuke them)
    $('#windows_reset').click(function (event){
        $('.errorText').hide().html('');
        $('#winevtlog_enabled').html(snapshot.enabled);
        $('#winevtlog_disabled').html(snapshot.disabled);
        $.each(snapshot.radio, function(){
            $(this).attr('checked', 'checked'); 
        });
        $('#enable_filter').val('');
        $('#disable_filter').val('');
        bindLists();
        event.preventDefault();
    });
    // binding for clicks in the enabled or disabled lists
    bindLists();
    // hook up the filters 
    // use type watch to avoid firing tons of events
    $('#enable_filter').typeWatch({
        callback: function() { 
                      search_text.enabled = $('#enable_filter').val(); 
                      filterText(search_text.enabled, '#enable_filter', '#winevtlog_enabled'); 
                      $('#winevtlog_enabled').scrollTop(0);
                  },
        wait: 600,
        captureLength: -1,
        highlight: false 
    });
    $('#disable_filter').typeWatch({
        callback: function() { 
                      search_text.disabled = $('#disable_filter').val(); 
                      filterText(search_text.disabled, '#disable_filter', '#winevtlog_disabled'); 
                      $('#winevtlog_disabled').scrollTop(0);
                  },
        wait: 600,
        captureLength: -1,
        highlight: false 

    });
    // hook up clicks on the filter clears
    $('#enable_filter_clear').click(function (event) {
        if (!($('#enable_filter').val() == '')) {    
            $('#enable_filter').val('');
            $('#winevtlog_enabled li').css('display', '');
            enable_desc = toggleSort($('#winevtlog_enabled'), 
                '#winevtlog_enable_sort', !enable_desc);
        }
        event.preventDefault();
    });
    $('#disable_filter_clear').click(function (event) {
        if (!($('#disable_filter').val() == '')) {    
            $('#disable_filter').val('');
            $('#winevtlog_disabled li').css('display', '');
            disable_desc = toggleSort($('#winevtlog_disabled'), 
                '#winevtlog_disable_sort', !disable_desc);
        }
        event.preventDefault();
    });
    // hook up sorting
    $('#winevtlog_enable_sort').click(function (event) {
        enable_desc = toggleSort($('#winevtlog_enabled'), 
            event.target, enable_desc);
        event.preventDefault();
    });
    $('#winevtlog_disable_sort').click(function (event) {
        disable_desc = toggleSort($('#winevtlog_disabled'), 
            event.target, disable_desc);
        event.preventDefault();
    });
    // hook up enable/disable all
    $('#winevtlog_enable_move').click(function (event) {
        $('#winevtlog_enabled li:visible').each(function () {
            enabledToDisabled(this); 
        });
        event.preventDefault();
    });
    $('#winevtlog_disable_move').click(function (event) {
        $('#winevtlog_disabled li:visible').each(function () {
            disabledToEnabled(this); 
        });
        event.preventDefault();
    });
});
