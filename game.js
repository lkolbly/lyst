function setIframeSize() {
		    var window_w = $(window).width();
		    var window_h = $(window).height();
		    var ar = window_w / (window_h+0.0);
		    if (ar > 1.5) {
			var frame_w = window_h * 1.5;
			var frame_h = window_h;
			var frame_x = (window_w - frame_w)/2.0;
			var frame_y = 0;
		    } else {
			var frame_w = window_w;
			var frame_h = window_w / 1.5;
			var frame_x = 0;
			var frame_y = (window_h - frame_h)/2.0;
		    }
		    frame_w = frame_w - 5;
		    frame_h = frame_h - 5;

		    $("iframe").css({"border": "none", "padding": 0, "margin": 0, "width": frame_w+"px", "height": frame_h+"px", "margin-left": frame_x+"px", "margin-top": frame_y+"px"});
}

window.onload = function() {
    if (true) {
	$("#dialog-confirm").dialog({
	    resizable: false,
	    width: 500,
	    modal: true,
	    buttons: {
		"Okay": function() {
		    $("body").append("<iframe width=\"100%\" height=\"100%\" src=\"/game.html\"></iframe>");
		    //alert("hi");
		    setIframeSize();
		    $(this).dialog("destroy").remove();
		},
		"Disable Letterbox": function() {
		    window.location = "/game.html";
		}
	    }
	});
    } else {
	window.location = "/game.html";
    }
}

$(window).resize(function(){
    setIframeSize();
});
