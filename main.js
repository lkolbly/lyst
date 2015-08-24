// Go check to see if the CDN servers are reachable.
// "cdns" is an array of objects with the "regex", "world" and "server" attributes.
jQuery.support.cors = true;

var game_CDN_Name = "";

function buildCDNs(cdns) {
    cdns2 = [];
    for (var i=0; i<cdns.length; i++) {
	$.ajax({
	    server: cdns[i].server,
	    url: cdns[i].server+"/index",
	    dataType: "json",
	    cache: false,
	    type: "GET",
	    success: function(data) {
		// Let's use this CDN for what they say they'll handle.
		//alert(data);
		//var line_re = /(\w+):\s*(.*)=>(.*)/.exec(data);
		//cdns2.push({"game": line_re[0], "from": line_re[1], "to": line_re[2]});
		for (var j=0; j<data.length; j++) {
		    var data2 = data;
		    data2[j].server = this.server;
		    cdns2.push(data2[j]);
		}
		//alert("yolo");
	    },
	    error: function(a, estr, ethrown) {
		// I don't care what the error was, don't use the CDN.
		alert("Issue connecting to a CDN '"+this.url+"'. "+estr+ethrown+" "+a.responseText);
	    }
	});
    }
    console.log(cdns2);
    return cdns2;
}

//var Game_CDNs = [{"server": "http://pillow.rscheme.org/lyst/cdn"}];

// Lambda passed to Mustache to convert URLs to a CDN equivalent
function URLToCDN(text, render) {
    //alert(text);
    console.log(Game_CDNs);
    var s = render(text);
    for (var i=0; i<Game_CDNs.length; i++) {
	// See if this one supports our game
	if (Game_CDNs[i].game === game_CDN_Name &&
	    Game_CDNs[i].res === getResolution()) {
	    s = Game_CDNs[i].server + "/" + game_CDN_Name + "" + s;
	    break;
	}
    }
    return s;
}

function checkBrowser()
{
    console.log("Browser version: "+$.browser.version);
    if (!$.browser.mozilla) {
	return false;
    }
    var major = $.browser.version.split(".")[0];
    if (major+0 < 19) {
	return false;
    }
    return true;
}

// Check to see if the mute cookie is set
function getCookie(c_name)
{
var i,x,y,ARRcookies=document.cookie.split(";");
for (i=0;i<ARRcookies.length;i++)
{
  x=ARRcookies[i].substr(0,ARRcookies[i].indexOf("="));
  y=ARRcookies[i].substr(ARRcookies[i].indexOf("=")+1);
  x=x.replace(/^\s+|\s+$/g,"");
  if (x==c_name)
    {
    return unescape(y);
    }
  }
    return null;
}

function setCookie(c_name, value, exdays) {
    var exdate = new Date();
    exdate.setDate(exdate.getDate() + exdays);
    var c_value=escape(value) + ((exdays==null) ? "" : "; expires="+exdate.toUTCString());
    document.cookie = c_name + "=" + c_value;
}

// Where we store our audio files
function AudioStore() {
    this.is_muted = false;
    this.audioElements = {};
    this.add = function (aid, uri) {
	var key = hex_md5(aid);
	if (key in this.audioElements) {
	    //return;
	}
	this.audioElements[key] = document.createElement("audio");
	this.audioElements[key].setAttribute("src", "/sounds/"+uri);
	this.audioElements[key].load();
	if (this.is_muted) {
	    this.audioElements[key].muted = true;
	}
    };
    this.play = function (aid) {
	var key = hex_md5(aid);
	if (key in this.audioElements)
	    this.audioElements[key].pause();
	this.audioElements[key] = document.createElement("audio");
	this.audioElements[key].setAttribute("src", "/sounds/"+aid);
	this.audioElements[key].load();
	this.audioElements[hex_md5(aid)].play();
    };
    this.volume = function (aid, volume) {
	if (getCookie("mute") === "true") {
	    volume = 0.0;
	}
	this.audioElements[hex_md5(aid)].volume = volume;
	//alert(volume);
    };
    this.looping = function (aid, is_looping) {
	this.audioElements[aid].loop = is_looping;
	console.log(is_looping);
	if (is_looping) {
	    $(this.audioElements[aid]).on("ended", function() {
		//console.log("Looping some audio!");
		$(this).get(0).currentTime = 0;
		$(this).get(0).play();
	    });
	}
    };
    this.addFromJson = function (o) {
	this.add(o.filename, o.filename);
	this.volume(o.filename, o.volume);
	this.looping(hex_md5(o.filename), o.loop);
	return o.filename;
    };
    this.playFromJson = function (o) {
	var aid = hex_md5(o.filename);
	if (hex_md5(o.filename) in this.audioElements) {
	    this.audioElements[hex_md5(o.filename)].pause();
	    this.looping(aid, o.loop);
	    this.audioElements[hex_md5(o.filename)].volume = o.volume;
	} else {
	    aid = this.addFromJson(o);
	}
	this.audioElements[hex_md5(o.filename)].play();
    };
    this.mute = function () {
	console.log("Muting.");
	for (var key in this.audioElements) {
	    this.audioElements[key].muted = true;
	}
	this.is_muted = true;
    };
    this.unmute = function () {
	console.log("Unmuting.");
	for (var key in this.audioElements) {
	    this.audioElements[key].muted = false;
	}
	this.is_muted = false;
    };
}

function muteVideos() {
    $("video").each(function() {
	$(this).prop("muted", true);
    });
}

function unmuteVideos() {
    $("video").each(function() {
	$(this).prop("muted", false);
    });
}

var audioStore = new AudioStore();
if (getCookie("lyst-mute") === "1") {
    audioStore.mute();
    muteVideos();
} else {
    audioStore.unmute();
    unmuteVideos();
    $("#mute-button").attr("src", "css/images/unmute.png");
}

function audioSetMuteButtonImage() {
    if (audioStore.is_muted) {
	$("#mute-button").attr("src", "css/images/mute.png");
    } else {
	$("#mute-button").attr("src", "css/images/unmute.png");
    }
}

function muteClicked() {
    if (audioStore.is_muted) {
	audioStore.unmute();
	unmuteVideos();
	$("#mute-button").attr("src", "css/images/unmute.png");
	setCookie("lyst-mute", 0);
    } else {
	audioStore.mute();
	muteVideos();
	$("#mute-button").attr("src", "css/images/mute.png");
	setCookie("lyst-mute", 1);
    }
}

// Convert a normal URL to an URL containing the user's prefs
function resify(url, render) {
    return "/"+getResolution()+render(url);
}

function getResolution() {
    var c = getCookie("lyst-resolution");
    if (c === null) {
	setResolution("1280x854");
	return "1280x854";
    }
    return c;
}

function setResolution(res) {
    setCookie("lyst-resolution", res, 365);
}

// Where we keep our templates
function TemplateStore() {
    this.templates = {};
    this.addTemplate = function (tid, uri) {
	templates = this.templates;
	$.ajax({url: uri, dataType: 'text'}).done(function (msg) {
	    //console.log(msg);
	    templates[hex_md5(tid)] = msg;
	});
    };
    this.renderTemplate = function (tid, state) {
	state["CDNify"] = function() { return URLToCDN; };
	state["Resify"] = function() { return resify; };
	t = this.templates[hex_md5(tid)];
	//console.log(t);
	return Mustache.to_html(t, state);
    };
}

// WAMP session object
var ws_Sess = null;
var template_Store = new TemplateStore();
template_Store.addTemplate("slide", "templates/slide.template");
template_Store.addTemplate("image", "templates/image.template");
template_Store.addTemplate("game_selection", "templates/game-selection.template");
template_Store.addTemplate("fullsizeItem", "templates/item-fullsize.template");

// An image store to keep images in
// DEPRECATED b/c of the new caching method (HTML5 manifest)
function ImageStore() {
    this.images = {};

    // Makes sure that the image is in our database.
    // Note that it may use whatever caching mechanisms it likes.
    this.addImage = function (uri) {
	//alert(hex_md5(uri));
	console.log("Loading "+uri);
	if (hex_md5(uri) in this.images) {
            //alert("PResent!");
            return;
	}
	var img = new Image();
	img.src = "/pictures/"+uri;
	this.images[hex_md5(uri)] = img;
    };

    // This function gets an image in base64 format, for the localStorage cache
    this.getImageBase64 = function (uri) {
	$.get("/pictures/"+uri+"?codec=b64", function(data) {
	    localStorage.setItem("img:"+hex_md5(uri), data);
	    var img = new Image();
	    img.src = "data:image/png,base64,"+data;
	    this.images[hex_md5(uri)] = img;
	});
    };
}

var image_Store = new ImageStore();

var item_Fullsizes = {};

function openItem(item_id) {

    // Get the fullsize spec for the item
    console.log(item_Fullsizes[item_id]);
    var full = item_Fullsizes[item_id];
    if (full.type === "image") {
	var img_src = full.src;
	$("body").append(template_Store.renderTemplate("fullsizeItem", {img_src: img_src, item_id: item_id}));

	// Load it
	$("#item-overlay").dialog({ modal: true });
    } else if (full.type === "slide") {
	// Request that this slide be rendered
	ws_Sess.call("renderDynamicSlide", [full.src],
	    function (slide) {
		console.log("Rendering item slide "+slide);
		$("body").append("<div id='item-overlay' style='margin:0;padding:0;width:60%;height:60%' title='Item "+item_id+"'></div>");

		// Let's check to see if they set the width
		var aspect = 1.0;
		if ("aspect" in full) {
		    aspect = full.aspect;
		}
		var width = 0.0;
		var height = 0.0;
		if ("setWidth" in full) {
		    width = full.setWidth;
		    height = width / aspect + 30;
		} else if ("setHeight" in full) {
		    height = full.setHeight + 30;
		    width = (height-30) * aspect;
		} else {
		    // Maximize it...
		    var window_aspect = $(window).width() / $(window).height();
		    if (aspect < window_aspect) {
			// We're bound by the height
			height = $(window).height();
			width = height * aspect;
		    } else {
			// We're bound by the width
			width = $(window).width();
			height = width / aspect;
		    }
		}
		console.log(width+","+height+" "+aspect);

		// Load it
		$("#item-overlay").dialog({ modal: true, resizeable: false, minWidth: width, minHeight: height /*, width: "100%", height: "500px"*/ });
		$("#item-overlay").on("dialogclose", function (event, ui) {
		    $("#item-overlay").remove();
		});

		renderSlideTo(slide, "#item-overlay", false);
	    },
	    function (error) {
	    }
	);
    }
    resizeAllRelatives();
}

function resizeAllRelatives() {
    $(".geometry-adjustable").each(function (index) {
	var x,y,w,h;
	var re = /-?\d+(\.\d+)?/g;
	var a = $(this).attr("geometry").match(re);
	x = a[0];
	y = a[1];
	w = a[2];
	h = a[3];
	$(this).css({'width':($(window).width()*w/100)+"px", 'height':($(window).height()*h/100)+"px", 'margin-left':($(window).width()*x/100)+"px", 'margin-top':($(window).height()*y/100)+"px"});
    });
};

function transpose_matrix(m) {
    var matrix2 = [m[0], m[4], m[8], m[12],
		   m[1], m[5], m[9], m[13],
		   m[2], m[6], m[10],m[14],
		   m[3], m[7], m[11],m[15]];
    return matrix2;
};

function generate_perspective_matrix(points) {
    var c_x = (points[0][0]+points[1][0]+points[2][0]+points[3][0])/4.0;
    var c_y = (points[0][1]+points[1][1]+points[2][1]+points[3][1])/4.0;
    var bb1_x = c_x;
    var bb1_y = c_y;
    var bb2_x = c_x;
    var bb2_y = c_y;
    var i;
    for (i=0; i<4; i++) {
	if (points[i][0] < bb1_x) bb1_x = points[i][0];
	if (points[i][1] < bb1_y) bb1_y = points[i][1];
	if (points[i][0] > bb2_x) bb2_x = points[i][0];
	if (points[i][1] > bb2_y) bb2_y = points[i][1];
    };

    var t1 = points[0];
    var t2 = points[1];
    var t3 = points[2];
    var t4 = points[3];

    var values = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
    var dx1, dx2, dx3, dy1, dy2, dy3;
    dx1 = t2[0] - t4[0]
    dx2 = t3[0] - t4[0]
    dx3 = t1[0] - t2[0] + t4[0] - t3[0]

    dy1 = t2[1] - t4[1]
    dy2 = t3[1] - t4[1]
    dy3 = t1[1] - t2[1] + t4[1] - t3[1]

    if (dx3 == 0.0 && dy3 == 0.0) {
        values[0] = t2[0] - t1[0]
        values[1] = t4[0] - t2[0]
        values[3] = t1[0]
        values[4] = t2[1] - t1[1]
        values[5] = t4[1] - t2[1]
        values[7] = t1[1]
        values[12] = 0.0
        values[13] = 0.0
    } else {
        var det1 = dx3 * dy2 - dy3 * dx2
        var det2 = dx1 * dy2 - dy1 * dx2

        if (det2 == 0.0) {
            values[12] = 1.0
        } else {
            values[12] = det1 / det2
	}

        det1 = dx1 * dy3 - dy1 * dx3

        if (det2 == 0.0) {
            values[13] = 1.0
        } else {
            values[13] = det1 / det2
	}

        values[0] = t2[0] - t1[0] + values[12] * t2[0]
        values[1] = t3[0] - t1[0] + values[13] * t3[0]
        values[3] = t1[0]

        values[4] = t2[1] - t1[1] + values[12] * t2[1]
        values[5] = t3[1] - t1[1] + values[13] * t3[1]
        values[7] = t1[1]
    };
    return transpose_matrix(values);
};

function build_scale_matrix(w, h) {
    var m = [1.0/w,0,0,0, 0,1.0/h,0,0, 0,0,1,0, 0,0,0,1];
    return m;
};

function mult_matrix(m1, m2) {
    var i,j,k;
    var m = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
    for (i=0; i<4; i++) {
	for (j=0; j<4; j++) {
	    m[i*4+j] = 0.0
	    for (k=0; k<4; k++) {
		m[i*4+j] += m2[i*4+k] * m1[k*4+j];
	    }
	}
    }
    return m;
};

function build_transform(map) {
    console.log("Map: "+map.type);
    if (map.type === "3d_2") {
	values = map.values;
	var w = $(window).width();
	var h = $(window).height();
	console.log("Generating matrix:");
	//console.log(generate_perspective_matrix(values));

	values = generate_perspective_matrix(values);
	values = mult_matrix(values, build_scale_matrix(w,h));

	console.log(values);
	var s = "matrix3d("+values[0]+","+values[1]+","+values[2]+","+values[3]+","+values[4]+","+values[5]+","+values[6]+","+values[7]+","+values[8]+","+values[9]+","+values[10]+","+values[11]+","+values[12]+","+values[13]+","+values[14]+","+values[15]+")";
	return s;
	return "";
    }
    if (map.type === "linear" || map.type === "3d") {
	values = map.values;
	var w = $(window).width();
	var h = $(window).height();

	values[0] = values[0];
	values[1] = values[1];
	values[2] = values[2];
	values[3] = values[3];

	values[4] = values[4];
	values[5] = values[5];
	values[6] = values[6];
	values[7] = values[7];

	values[8] = values[8];
	values[9] = values[9];
	values[10] = values[10];
	values[11] = values[11];

	values[12] = values[12] * w;
	values[13] = values[13] * h;
	values[14] = values[14];
	values[15] = values[15];

	var s = "matrix3d("+values[0]+","+values[1]+","+values[2]+","+values[3]+","+values[4]+","+values[5]+","+values[6]+","+values[7]+","+values[8]+","+values[9]+","+values[10]+","+values[11]+","+values[12]+","+values[13]+","+values[14]+","+values[15]+")";
	return s;
    } else if (map.type == "2d") {
	var values = map.values;
	var s = "matrix("+values[0]+","+values[1]+","+values[2]+","+values[3]+","+values[4]+","+values[5]+")";
	return s;
    } else {
	// What could this be?
    }
}

function renderSlideTo(slide, dest_div, has_frills) {
    console.log(slide);
    var has_image = true;
    if (slide.image.src.length == 0) {
	has_image = false;
    }
    var s = template_Store.renderTemplate("slide", {slide: slide, has_frills: has_frills, has_image: has_image});
    $(dest_div).html(s);

    if (has_frills) {
	$('#items').enscroll({
	    showOnHover: true,
	    zIndex: 1001,
	    verticalTrackClass: 'track3',
	    verticalHandleClass: 'handle3'
	});
	audioSetMuteButtonImage();
    }

    for (var i=0; i<slide.dynamic_screens.length; i++) {
	// Create a new div, and apply the CSS transform to it.
	var newdiv_name = "newdiv_"+i;
	var w = $(window).width();
	var h = $(window).height();
	$(dest_div+" > #main").prepend("<div id='"+newdiv_name+"' style='z-index:-100;position:fixed;width:100%;height:100%;transform-style:preserve-3d;-moz-transform-origin:0px 0px;-moz-transform:matrix("+w+",0.0,0.0,"+h+",0.0,0.0) "+build_transform(slide.dynamic_screens[i].map)+"'></div>");

	// Render into the div
	renderSlideTo(slide.dynamic_screens[i].content, "#"+newdiv_name, false);
    }
    $(".hotspot").unbind("click");
    $(".hotspot").click(function () {
	ws_Sess.call("slideClick", [this.id], function(){});
    });
}

var red_Overlay_Enabled = false;

// The 'slide' object holds information about the image and the hotspots.
function loadSlide(slide) {
    renderSlideTo(slide, "body", true);
    var x = ws_Sess;
    ws_Sess = x;
    $(".item").click(function () {
	openItem(this.id);
    });
    $(".item").draggable({
	opacity: 0.7,
	helper: function( event ) {
            var e = $(this).clone().appendTo("body").show();
	    e.css("z-index", 10000);
	    e.css("margin-left", 0);
	    e.css("margin-top", 0);
	    return e;
	    return $("<img src='"+$(this).attr("src")+"'/>");
	},
	cursor: "url('cursors/grab.cur'), default",
	cursorAt: {top: 0, left: 0},
	stop: function(ev, ui) {
	    ws_Sess.call("itemDrag",
			 [{id: this.id, pos: {top: ui.position.top/$(window).height(), left: ui.position.left/$(window).width()}}]);
	    console.log(ui.position.top);
	    $(ui).remove();
	}
    });
    resizeAllRelatives();

    // Add all of the item fullsize descriptors
    var i = 0;
    for (i=0; i<slide.items.length; i++) {
	item_Fullsizes[slide.items[i].id] = slide.items[i].fullsize;
    }

    // Now deal with the sounds
    for (i=0; i<slide.sounds.length; i++) {
	//console.log(slide.sounds[i]);
	audioStore.playFromJson(slide.sounds[i]);
    }

    $(".video > video").bind("loadedmetadata", function() {
	var dx = $(window).width() / $(this).get(0).videoWidth;
	var tx = $(window).width() / 2 - $(this).parent().width() / 2;
	var dy = $(window).height() / $(this).get(0).videoHeight;
	var ty = $(window).height() / 2 - $(this).parent().height() / 2 + 8;
	var trans = "translate("+tx+"px,"+ty+"px) scaleX("+dx+") scaleY("+dy+")";
	$(this).parent().css("-moz-transform", trans);

	if (audioStore.is_muted) {
	    muteVideos();
	} else {
	    unmuteVideos();
	}
    });

    // Now deal with the "actions"
    for (i=0; i<slide.actions.length; i++) {
	if (slide.actions[i].action === "triggerHotspot") {
	    var h_id = slide.actions[i].hs_id;
	    setTimeout(function () {
		$("#"+h_id).trigger("click");
	    }, slide.actions[i].delay * 1000.0);
	}
    }

    // And finally, the save game button.
    $("#save-game-button").button().click(function() {
	ws_Sess.call("saveGame", [], function (result) {
	    // Create a dialog to tell the user it worked.
	    $("body").append("<div id='dialog-game-saved'><p>The game was saved!</p></div>");
	    $("#dialog-game-saved").dialog({
		resizeable: true,
		modal: true,
		buttons: {
		    "Okay": function () {
			$(this).dialog("close");
		    }
		}
	    });
	}, function (error) {
	    $("body").append("<div id='dialog-game-saved'><p>The game could not be saved due to an error.</p></div>");
	    $("#dialog-game-saved").dialog({
		resizeable: true,
		modal: true,
		buttons: {
		    "Okay": function () {
			$(this).dialog("close");
		    }
		}
	    });
	});
    });

    $("#logout-button").button().click(function() {
	signout();
    });

    $("#resolution-selector").val(getResolution());
    $("#resolution-selector").change(function () {
	setResolution($(this).val());
    });
}

// TODO: At some point, I should look at either removing this or making it
// more flexible.
function loadDeltaSlide(ds) {
    ds.events.forEach(function (e) {
	if (e.action === "NewImage") {
	    // The action is to add a new image to the slide
	    var s = template_Store.renderTemplate("image", e.image);
	    $("#main").append(s);
	} else if (e.action === "RemoveImage") {
	    $("#"+e.img_id).remove();
	} else if (e.action === "PlaySound") {
	    audioStore.playFromJson(e.snd);
	} else if (e.action === "AnimateImage") {
	    if (e.animation === "translate") {
		console.log("Translating by "+(e.dx*$(window).width())+","+(e.dy*$(window).height()));
		move("#"+e.img_id).add("margin-left", e.dx*$(window).width()).add("margin-top", e.dy*$(window).height()).duration(e.dt).end();
	    } else if (e.animation === "rotation") {
		console.log("Rotating by "+e.dr);
		move("#"+e.img_id).rotate(e.dr).duration(e.dt).end();
	    }
	} else if (e.action === "ReplaceImage") {
	    $("#"+e.img_id).attr("src", "/full/pictures/"+e.src);
	} else if (e.action === "closeItem") {
	    console.log("Closing the dialog.");
	    $("#item-overlay").remove();
	}
    });
}

function loadDynScr(ds) {
    $("#item-overlay").empty();
    renderSlideTo(ds.delta.slide, "#item-overlay", false);
}

// A quick container to handle connection issues...
var connectionErrorScreen = function() {
    this.is_active = false;
    this.startError = function() {
	if (this.is_active) {
	    return;
	}
	this.is_active = true;
	// Create the dialog content
	$("body").append("<div class='ui-widget-overlay ui-front'></div><div id='error-overlay' title='WebSocket Error'><h1>Error</h1><p>An error has occurred with the WebSocket backend. If this box does not go away within a few seconds, you must reload.</p></div>");

	// Load it
	$("#error-overlay").dialog({ resizeable: false });
    };
    this.stopError = function() {
	if (!this.is_active) {
	    return;
	}
	this.is_active = false;
	$("#error-overlay").remove();
    };
};
var connection_Error_Screen = new connectionErrorScreen();

var is_first_load = true;

function chooseGame(game_id) {
    ws_Sess.call("chooseGame", [game_id], function(uid) {
	setCookie("lyst_user_uid", uid);

	// And now we wait
	ws_Sess.call("startGame", [uid]);
    });
};

function signout() {
    setCookie("lyst-user", null);
    setCookie("lyst-auth-cookie", null);
    location.reload();
};

window.onload = function() {
    if (!is_first_load) {
	return;
    }
    is_first_load = false;

    if (!checkBrowser()) {
	$("body").append("<div id='bad-browser'><p>Lyst only works with Firefox (version 19 and above). You don't have Firefox (or it's an older version).</p></div>'");
	$("#bad-browser").dialog({
	    resizeable: false,
	    width:"700px",
	    modal: true,
	    buttons: {
		"Get Firefox": function() {
		    window.location = "http://www.mozilla.org/";
		    $(this).dialog("close");
		},
		"I Don't Care": function() {
		    $(this).dialog("close");
		}
	    }
	});
    }

    Game_CDNs = buildCDNs(Game_CDNs);

    $("body").mousemove(function(event) {
	var w = event.pageX / $(window).width() * 100.0;
	var h = event.pageY / $(window).height() * 100.0;
	$("#debug-mouse-coords").html(w.toFixed(2)+"%x"+h.toFixed(2)+"%");
    });

    var wsuri;
    if (window.location.protocol === "file:") {
	wsuri = "ws://localhost:9000";
    } else {
	wsuri = "ws://" + window.location.hostname + ":9000";
    }

    var ws = new WebSocket(wsuri);
    ws.onmessage = function(event) {
	console.log(event.data);
	var o = JSON.parse(event.data);
	if (o._cb_id !== undefined) {
	    ws_Sess._cb_ids[o._cb_id](o.result);
	} else {
            console.log(o + " unsolicited by, action = " + o.action);
	    //console.log(ws_Sess);
            if (o.action === "loadSlide") {
		loadSlide(o.slide);
	    } else if (o.action === "loadDeltaSlide") {
		loadDeltaSlide(o.delta);
            } else if (o.action === "preloadImage") {
		image_Store.addImage(o.image_uri);
	    } else if (o.action === "loadDynScr") {
		loadDynScr(o);
	    } else if (o.action === "setCDNGameName") {
		game_CDN_Name = o.name;
            }
	}
    };
    ws.onopen = function(event) {
        ws_Sess = {
	    _cb_cnt: 0,
	    _cb_ids: {},
	    call: function(fn, args, cb) {
		console.log("Calling "+fn);
		if (cb !== undefined) {
		    var callback_id = this._cb_cnt++; // The ID they should callback at
		    this._cb_ids[callback_id] = cb;
		    ws.send(JSON.stringify({action: fn, callback_id: callback_id, args: args}));
		} else {
		    ws.send(JSON.stringify({action: fn, args: args}));
		}
	    }
	};
	
        console.log("Connected to " + wsuri);
	connection_Error_Screen.stopError();

	// If we have a login cookie, let's try to login with that.
	var user_cookie = getCookie("lyst-user");
	var auth_cookie = getCookie("lyst-auth-cookie");
	if (user_cookie === null || auth_cookie === null) {
	    // Stay the course
	} else {
	    // Try to authenticate
	    ws_Sess.call("userLoginCookie", [user_cookie, auth_cookie], function (games) {
			     console.log("auth cookies: "+user_cookie+", "+auth_cookie);
			     console.log(games);
			     if ("error" in games) {
				 // Simply don't do anything.
			     } else {
				 // Save the authentication cookies
				 setCookie("lyst-user", games["username"]);
				 setCookie("lyst-auth-cookie", games["cookie"]);

				 // Create a table to hold the different saved games
				 $("body").html(template_Store.renderTemplate("game_selection", games));
			     }
			 });
	}
    };
    ws.onclose = function(event) {
	console.log(event);
        ws_Sess = null;
	connection_Error_Screen.startError();
    };

    // Build the login form

    $("#register-form").submit(function() {
	if ($("#register-password").val() !== $("#register-password-confirm").val()) {
	    $("#error-banner").html("Passwords did not match.");
	} else {
	    var obj = {"username": $("#register-username").val(),
		       "fullname": $("#register-fullname").val(),
		       "password": $("#register-password").val(),
		       "email": $("#register-email").val()};
	    ws_Sess.call("registerUser", [obj], function (error) {
		if (error === 1) {
		    $("#error-banner").html("<p>There was an error creating the user.</p>");
		} else if ("error" in error) {
		    $("#error-banner").html("<p>"+error.error+"</p>");
		} else {
		    $("#error-banner").html("");
		    $("#good-banner").html("<p>User successfully created!</p>");
		    $("#register-username").val("");
		    $("#register-fullname").val("");
		    $("#register-password").val("");
		    $("#register-email").val("");
		    $("#register-password-confirm").val("");
		}
	    },
			 function (error) {
			     alert("An error occurred: "+error);
			 });
	}
	return false;
    });

    $("#login-form").submit(function() {
	// Kick off the WebSocket login stuff
	ws_Sess.call("userLogin", [$("#login-username").val(), $("#login-password").val()],
		     function (games) {
			 if ("error" in games) {
			     $("#error-banner").html("<p>No user found or invalid password</p>");
			 } else {
			     // Save the authentication cookies
			     setCookie("lyst-user", games["username"]);
			     setCookie("lyst-auth-cookie", games["cookie"]);

			     // Create a table to hold the different saved games
			     $("body").html(template_Store.renderTemplate("game_selection", games));
			 }
		     },
		     function (error) {
			 alert("An error occurred: "+error);
		     }
		    );
	return false;
    });
};

$(window).resize(function(){
    resizeAllRelatives();
});
