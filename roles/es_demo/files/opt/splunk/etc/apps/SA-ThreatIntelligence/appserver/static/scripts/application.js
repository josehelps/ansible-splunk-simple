
/**
 * SA-ThreatIntelligence application.js 
 */ 

// Incident Review Tooltips
$(document).ready(function() {
    $('.urgency span[title]').qtip({ style: { name: 'cream', tip: true } });
    $('.status span[title]').qtip( { style: { name: 'cream', tip: true } });
});

// Incident Review Toggle
function toggleIRDetails(event_hash) {
	var hiddenID = '#' + event_hash;
    var toggleID = hiddenID + '-toggle';
    var toggleText = $(toggleID).text();
	
    if ( toggleText.indexOf('View details') != -1 ) {
        $(toggleID).text('Hide details');
    }
    else {
        $(toggleID).text('View details');
    }
    
    $(hiddenID).slideToggle(200);
    
    return false;
}
