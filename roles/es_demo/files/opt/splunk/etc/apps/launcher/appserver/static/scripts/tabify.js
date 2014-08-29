/*******************
    tabification 
********************/

function tabify ( tabID ) { 

    var $tabID = (tabID.substr(0,1) == '#') ? $(tabID) : $('#' + tabID);
        
    if ( $tabID.children('li').children('a').length > 1 ) {
        $tabID.children('li').children('a').each(function(){
            tab = $(this).attr('href');
            if ( $(this).parent('li').is('.current') ) {
                $(tab).css('display','block');
            } else {
                $(tab).css('display','none');
            }
        }); 

        $tabID.bind('click', function(evt){
            var t = evt.target;
            
            if ( $(t).is('a') && !$(t).parent('li').is('.current') ) {
                $li = $(t).parent('li');
                $a = $(t);
            } else if ( $(t).is('li') && !$(t).is('.current') ) {
                $li = $(t);
                $a = $(t).children('a');   
            } else {
                 return false;
            }
            
            $current = $('.current', $tabID);
            shownTab = $current.children('a').attr('href');

            $(shownTab).css('display','none');
            $current.removeClass('current');
            
            $li.addClass('current');
            tabToShow = $a.attr('href');
            $(tabToShow).css('display','block');   
            
            $(t).blur();
            
            return false;
        });  
    }    
       
}

