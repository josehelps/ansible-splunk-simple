$(document).ready(function (){
    $('#scripted_enable_all').click(function (event){
        $('.ScriptedEnable').attr('checked', 'checked');
        event.preventDefault();
    });
    $('#scripted_disable_all').click(function (event){
        $('.ScriptedDisable').attr('checked', 'checked');
        event.preventDefault();
    });
    $('#monitor_enable_all').click(function (event){
        $('.MonitorEnable').attr('checked', 'checked');
        event.preventDefault();
    });
    $('#monitor_disable_all').click(function (event){
        $('.MonitorDisable').attr('checked', 'checked');
        event.preventDefault();
    });
    $('#ta_unix_form').submit(function (event){
        $('#ta-unix_submit').attr('disabled', 'disabled').val('Please wait...')
            .next().attr('disabled', 'disabled');
    });
    $('#ta-unix_reset').click(function (event){
        $('.errorText').hide().html('');
    });
});
