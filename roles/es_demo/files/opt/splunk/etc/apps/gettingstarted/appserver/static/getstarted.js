$(function(){
    $(".gsTOCLink").click(function(){
        $('.gsDetails').hide();
        var divToShow=$(this).attr("divToShow");
        $(divToShow).show();
        $('.gsTOCLink').removeClass("gsTOCLinkHighlighted");
        $(this).addClass("gsTOCLinkHighlighted");
        return false;
    });
    
    $(".gsExpandLink").click(function(){
        $('.gsExpandDetails').hide();
        var divToShow=$(this).attr("divToShow");
        $(divToShow).show();
        $('.gsExpandLink').removeClass("gsExpandLinkHighlighted");
        $(this).addClass("gsExpandLinkHighlighted");
        return false;
    });
    
    $(".gsMoreLink").click(function(){
        if($(this).hasClass("gsMoreLinkOpen")){
            $(this).removeClass("gsMoreLinkOpen");
            $(this).next(".gsMoreInfo").hide();
        } else{
            $(this).addClass("gsMoreLinkOpen");
            $(this).next(".gsMoreInfo").show();
        }
        return false;
    });
})