import xml.dom
import xml.dom.minidom
import re, string
import random, hashlib
import json
import world_api

# Returns xywh always
def parseGeometryString(s):
        match = re.match(r"(?:xywh:)?([\d\.]+),([\d\.]+),([\d\.]+),([\d\.]+)", s)
        if match:
            x = float(match.groups()[0])
            y = float(match.groups()[1])
            w = float(match.groups()[2])
            h = float(match.groups()[3])
            return (x,y,w,h)

        match = re.match(r"xyxy:([\d\.]+),([\d\.]+),([\d\.]+),([\d\.]+)", s)
        if match:
            x1 = float(match.groups()[0])
            y1 = float(match.groups()[1])
            x2 = float(match.groups()[2])
            y2 = float(match.groups()[3])
            return (x1,y1,x2-x1,y2-y1)
        return (0,0,0,-1)

class DynamicScreen:
    def __init__(self, elem=None):
        self.elem = None
        self.slide = None
        if elem:
            self.fromDOM(elem)

    def render(self, state):
        ds = RenderSlide()
        self.slide.logic.render(ds, state)
        return ds

    def fromDOM(self, elem):
        self.elem = elem

        # Create a slide based on the <content> tag.
        self.slide = Slide()
        self.slide.fromDOM(elem.getElementsByTagName("content")[0])

    def __getstate__(self):
        return {"slide": self.slide}

    def __setstate__(self, state):
        self.__init__()
	self.slide = state["slide"]

class DynamicScreenRef:
    def __init__(self, elem=None):
        self.elem = elem

    def s_to_pts(self, s):
        pts = []
        for match in re.finditer(r"\(([\d\-\.]*),([\d\-\.]*)\)", s):
            pts.append((float(match.groups()[0]),float(match.groups()[1]), 1.0))
        return pts

    def getmap(self):
        map_elem = self.elem.getElementsByTagName("map")[0]
        mtype = map_elem.getAttribute("type")
        if mtype == "linear_2":
            to_pts_str = map_elem.getAttribute("to")
            points = self.s_to_pts(to_pts_str)
            return {"type": "3d_2", "values": points}
        elif mtype == "raw3d":
            values = json.loads(map_elem.getAttribute("values"))
            return {"type": "3d", "values": values}
        elif mtype == "raw":
            values = json.loads(map_elem.getAttribute("values"))
            return {"type": "2d", "values": values}
        else:
            print "Unknown DynamicScreenRef map type '%s'"%mtype
            return {"type": "unknown"}
        return {"type": "linear", "values": values}

    def render(self, render_slide, state):
        dynscr = state["__lyst"]["dynamic_screens"].get(self.elem.getAttribute("id"), None)
        if not dynscr:
            print "WARNING: No dynamic screen '%s'"%self.elem.getAttribute("id")
            return
        s = dynscr.render(state)
        render_slide.dynamic_screens.append({"content": s, "map": self.getmap()})
        pass

class DynamicScreenNode:
    def __init__(self, elem):
        self.dynscr = DynamicScreenRef(elem)

    def render(self, dest_slide, state):
        #print "Rendering dynamic screen..."
        self.dynscr.render(dest_slide, state)

class HotspotTemplate:
    def __init__(self, elem=None):
        self.geometry = ""#(0,0,0,-1) # xywh is the standard
        self.cursor = ""
        self.id = ""
        if elem:
            self.fromDOM(elem)

    def fromDOM(self, elem):
        self.geometry = elem.getAttribute("geometry")
        self.cursor = elem.getAttribute("cursor")
        if not self.cursor or self.cursor == "":
            self.cursor == "grab"

# TODO: Make this not global.
hotspot_Templates = {}

class Hotspot:
    def __init__(self):
        self.elem = None
        self.id = ""

        self.is_from_api = False
        self.api = None # The actual API object

        self.api_callbacks = {}
        self.options = []
        pass

    def fromAPI(self, hs):
        self.is_from_api = True
        self.api = hs
        self.id = hashlib.md5(str(random.randint(0,1000000))).hexdigest()
        self.api_callbacks = hs.api_callbacks
        self.options = hs.options
        pass

    def fromDOM(self, elem):
        self.elem = elem
        self.id = hashlib.md5(str(random.randint(0,1000000))).hexdigest()#elem.getAttribute("id")
	if self.elem.getAttribute("dragMethod"):
            self.setAPICall(self.elem.getAttribute("dragMethod"), {}, on="itemDragged")
	if self.elem.getAttribute("clickMethod"):
            self.setAPICall(self.elem.getAttribute("clickMethod"), {}, on="hotspotClicked")

    def getAction(self):
        if self.is_from_api:
            return self.api.action
        return self.elem.getAttribute("action")

    def getAPICall(self, on="hotspotClicked"):
        return self.api_callbacks.get(on, None)

    def setAPICall(self, method, args, on="hotspotClicked"):
        #self.api_callback = {"method": method, "args": args}
        self.api_callbacks[on] = {"method": method, "args": args}

    def parseGeometryString(self, s):
        match = re.match(r"(?:xywh:)?([\d\.]+),([\d\.]+),([\d\.]+),([\d\.]+)", s)
        if match:
            x = float(match.groups()[0])
            y = float(match.groups()[1])
            w = float(match.groups()[2])
            h = float(match.groups()[3])
            return (x,y,w,h)

        match = re.match(r"xyxy:([\d\.]+),([\d\.]+),([\d\.]+),([\d\.]+)", s)
        if match:
            x1 = float(match.groups()[0])
            y1 = float(match.groups()[1])
            x2 = float(match.groups()[2])
            y2 = float(match.groups()[3])
            return (x1,y1,x2-x1,y2-y1)
        return (0,0,0,-1)

    def json(self):
        if self.is_from_api:
            geo_str = self.api.geometry
            cursor = self.api.cursor
            template = None
        else:
            geo_str = self.elem.getAttribute("geometry")
            cursor = self.elem.getAttribute("cursor")
            template = hotspot_Templates.get(self.elem.getAttribute("template"), None)

        if template:
            if template.geometry != "":
                geo_str = template.geometry
            if template.cursor != "":
                cursor = template.cursor

        x,y,w,h = self.parseGeometryString(geo_str)
        if x == 0 and y == 0 and w == 0 and h == -1:
            print "Got a geo_str: %s"%geo_str
        if not cursor:
            cursor = "grab"
        return {"width": w*100, "height": h*100, "x": x*100, "y": y*100, "id": self.id, "w": int(w*100), "h": int(h*100), "cursor": cursor}

    # Do we contain the given point?
    def contains(self, x, y):
        js = self.json()
        x *= 100
        y *= 100
        print x,y,js
        if x>js["x"] and x<js["width"]+js["x"] and y>js["y"] and y<js["height"]+js["y"]:
            return True
        return False

class Video:
    def __init__(self, elem):
        self.elem = None

    def json(self):
        return {"src": self.elem.getAttribute("src")}

class Player:
    def __init__(self):
        self.cur_slide_id = "credits-1"#"noc-1-forward"#"radio-dial"#"biotech-select-primers"
        self.cur_slide = None # The actual rendered object
        self.items = [] # Items we have

class Expression:
    def __init__(self, expr):
        # Parse expr!
        self.expr = expr

        self.variables = None
        pass

    # Converts dot notation to bracket notation ("noc.kvm[0].screen" => "[noc][kvm][0][screen]")
    def convert_variable_name(self, val1):
        var_elems = val1.split(".")
	var_reference = ""
	for e in var_elems:
            m2 = re.match(r"([a-zA-Z_]+)\[(\d+)\]", e)
	    if m2:
                var_reference += "[\"%s\"][%s]"%(m2.groups()[0], m2.groups()[1])
	    else:
                var_reference += "[\"%s\"]"%e
	return var_reference

    # Single value, single operator, single value.
    def evaluateBasicExprRE(self, expr):
        variables = self.variables
        #print expr.groups()
        match = re.match(r"((?:(?:\w*):)?)((?:[a-z]|[A-Z])[\w\.-]*)\s*( is in |==|>|>=|<|<=)\s*((?:(?:[a-z]|[A-Z])[\w-]*)|\d*)", expr.groups()[0]) # God, I love regex.
        if match:
            #print match.groups()
            ns_spec = match.groups()[0]
            val1 = match.groups()[1]
            op = match.groups()[2]
            val2 = match.groups()[3]

            if op == " is in " and ns_spec == "item:":
                # Do something special...
                #print "We have an item: ",variables["item:"+val1]
                loc = variables["item:"+val1].location
                #print loc,val2
		print "Checking to see if %s is in %s (location=%s)"%(val1,val2,loc)
                if loc == val2:
                    return "True"
                else:
                    return "False"
                return "True"

            if val1 == "true": val1 = True
            elif ns_spec == "":
                if val1 in variables:
		    val1 = variables[val1]
		else:
                    var_reference = self.convert_variable_name(val1)
		    print "%s converted to %s (==%s)"%(val1, var_reference, eval("variables%s"%var_reference))#variables[var_reference])
		    val1 = eval("variables%s"%var_reference)#variables[var_reference]
            elif val1[0] in string.digits and "." in val1: val1 = float(val1)
            elif val1[0] in string.digits and "." not in val1:val1 = int(val1)
            else: val1 = variables["%s:%s"%(ns_spec,val1)]

            if val2 == "true": val2 = True
            elif val2 == "false": val2 = False
            elif val2[0] in string.digits and "." in val2: val2 = float(val2)
            elif val2[0] in string.digits and "." not in val2:val2 = float(val2)
            else:
                if val2 in variables:
		    val2 = variables["%s"%val2]
		else:
                    var_reference = self.convert_variable_name(val2)
		    print "%s converted to %s (==%s)"%(val2, var_reference, eval("variables%s"%var_reference))#variables[var_reference])
		    val2 = eval("variables%s"%var_reference)#variables[var_reference]

            #print "%s%s%s"%(val1,op,val2)
            if eval("%s%s%s"%(val1,op,val2)):
                return "True"
            else:
                return "False"
        return "True"

    def evaluate(self, variables):
        self.variables = variables

        if '(' not in self.expr:
            expr = self.evaluateBasicExprRE(re.match(r"([^\(]*)", self.expr))
        else:
            # Start from the bottom. Solve smallest parenthesis.
            expr = self.expr
            while '(' in expr:
                expr = re.sub(r"\(([^)(]*)\)", self.evaluateBasicExprRE, expr)

        # Now solve all of the "or" and "and" parens.
        expr = re.sub(r"True or False", "True", expr)
        expr = re.sub(r"True or True", "True", expr)
        expr = re.sub(r"False or True", "True", expr)
        expr = re.sub(r"False or False", "False", expr)

        expr = re.sub(r"True and True", "True", expr)
        expr = re.sub(r"True and False", "False", expr)
        expr = re.sub(r"False and True", "False", expr)
        expr = re.sub(r"False and False", "False", expr)

        #print expr
        expr = expr.strip("()")
        if expr == "True":
            return True
        else:
            return False
        return True

#e = Expression("(locker-2-isopen==true) or (locker-2-isopen==false)")
#print e.evaluate({"locker-2-isopen": True})
#exit()

class LogicNode:
    def __init__(self):
        self.elem = None # For now we will parse on the fly
        self.parent_if_result = False
        self.parent_is_if = False
        self.children = []
        pass

    def parseExpression(self, expr, state):
        e = Expression(expr)
        return e.evaluate(state)

    # Finds all applicable RenderNodes
    def render(self, dest_slide, state):
        print self.elem.localName
        if self.elem.localName == "if":
            # Evaluate some expression!
            result = self.parseExpression(self.elem.getAttribute("expr"), state)

            # Propogate it to our children
            for c in self.children:
                c.setIfResult(result)
                c.parent_is_if = True
            self.renderChildren(dest_slide, state)
            pass
        elif self.elem.localName == "then":
            # A passthrough! (maybe)
            if self.parent_if_result:
                self.renderChildren(dest_slide, state)
            pass
        elif self.elem.localName == "else":
            # A passthrough! (maybe)
            if not self.parent_if_result:
                self.renderChildren(dest_slide, state)
        elif self.parent_is_if:
            if self.parent_if_result:
                self.renderChildren(dest_slide, state)
        else:
            self.renderChildren(dest_slide, state)
        return state

    def renderChildren(self, dest_slide, state):
        for c in self.children:
            c.render(dest_slide, state)

    # If the parent is an if statement, and we're a "then" statement, this is
    # how we convey the result of the if statement.
    def setIfResult(self, result):
        self.parent_if_result = result

    def fromDOM(self, elem):
        self.elem = elem
        for c in elem.childNodes:
            if c.nodeType == xml.dom.Node.ELEMENT_NODE:
                if c.prefix == "cond":
                    #print "Found condition %s"%c.tagName
                    n = LogicNode()
                    n.fromDOM(c)
                elif c.prefix == "api":
                    #print "Found api node %s"%c.tagName
                    n = APINode()
                    n.fromDOM(c)
                elif c.localName == "dynamic_screen":
                    n = DynamicScreenNode(c)
                else:
                    #print "Found renderer %s"%c.tagName
                    n = RenderNode()
                    n.fromDOM(c)
                self.children.append(n)
        pass

    def __getstate__(self):
        return None#{"asdf": "asdf"}

class RenderNode:
    def __init__(self):
        self.elem = None
        pass

    def renderActionNode(self, dest_slide):
        if self.elem.getAttribute("type") == "fadeToNext":
            dest_slide.actions.append({"action": "fadeToNext",
                                       "tstart": float(self.elem.getAttribute("tstart")),
                                       "tend": float(self.elem.getAttribute("tend")),
                                       "dest": self.elem.getAttribute("dest")})
	elif self.elem.getAttribute("type") == "delay":
            wa_hs = world_api.makeHotspot("xyxy:0.0,0.0,0.0,0.0", self.elem.getAttribute("action"))
	    hs = Hotspot()
	    hs.fromAPI(wa_hs)
	    dest_slide.actions.append({"action": "triggerHotspot",
				       "hs_id": hs.id,
				       "delay": float(self.elem.getAttribute("delay"))})
	    dest_slide.addHotspot(hs)
	    print "Added a delay action to the current slide (h_id=%s)."%hs.id
            pass
        pass

    def render(self, dest_slide, state):
        #print "RenderNode: %s"%self.elem.tagName
        if self.elem.tagName == "image":
            dest_slide.src_img = self.elem.getAttribute("src")
        elif self.elem.tagName == "video":
            obj = {"src": "intro.webm"}
            dest_slide.videos.append(obj)
        elif self.elem.tagName == "hotspot":
            hs = Hotspot()
            hs.fromDOM(self.elem)
            dest_slide.addHotspot(hs)
        elif self.elem.tagName == "subimage":
            x,y,w,h = parseGeometryString(self.elem.getAttribute("pos"))
            src = self.elem.getAttribute("src")
            img = {"x":x*100, "y": y*100, "w": w*100, "h": h*100, "src": src}
            dest_slide.images.append(img)
            """dest_slide.images.append({"x":int(self.elem.getAttribute("x")*100),
                                      "y":int(self.elem.getAttribute("y")*100),
                                      "w":int(self.elem.getAttribute("w")*100),
                                      "h":int(self.elem.getAttribute("h")*100)})"""
        elif self.elem.tagName == "action":
            self.renderActionNode(dest_slide)
            pass
        pass

    def setIfResult(self, result):
        pass # We don't actually care...

    def fromDOM(self, elem):
        self.elem = elem
        pass

import sys
sys.path.append("../worlds/lasa")
import api

class APINode:
    def __init__(self):
        self.elem = None
        pass

    # TODO: At the moment, the API is allowed to write into state.
    # This is a little bit sketchy, and should be cleaned up in the future.
    def render(self, dest_slide, state):
        # Go find (and import) this world's API
        #import api

        # Generate the arguments (if any)
        args = {}
        for c in self.elem.childNodes:
            if c.nodeType == xml.dom.Node.ELEMENT_NODE:
                if c.prefix == "api" and c.localName == "arg":
                    args[c.getAttribute("key")] = c.getAttribute("value")

        if self.elem.localName == "generateSlide":
            #s = api.generateSlide(args, state)
            tocall = getattr(api, self.elem.getAttribute("method"))
            s = tocall(args, state)
            print s
            if s:
                dest_slide.fromAPISlide(s)
            pass

    def fromDOM(self, elem):
        self.elem = elem
        pass

class SlideLogic(LogicNode):
    def __init__(self):
        LogicNode.__init__(self)

# This contains information about a slide (logic, contents, etc.)
class Slide:
    def __init__(self):
        self.logic = None # A SlideLogic instance

    def fromDOM(self, elem):
        self.logic = SlideLogic()
        self.logic.fromDOM(elem)
        pass

# This contains the data to render a delta slide
class RenderDeltaSlide:
    def __init__(self):
        self.ds = None
        pass

    def fromAPI(self, s):
        self.ds = s.json()
        pass

    def json(self):
        return self.ds

# This contains only the data to render a slide
class RenderSlide:
    def __init__(self):
        self.id = ""
        self.hotspots = []
        self.src_img = None
        self.items = []
        self.images = [] # A list of images that aren't the main 'background'
        self.sounds = []
        self.videos = []
        self.actions = []
        self.dynamic_screens = []

    def fromAPISlide(self, s):
        print "Converting from API slide %s"%s.src_img
        self.hotspots = []
        self.items = []

        self.src_img = s.src_img
        #self.hotspots = s.hotspots
        for hs in s.hotspots:
            hs2 = Hotspot()
            hs2.fromAPI(hs)
            self.hotspots.append(hs2)
        self.images = s.images
        self.sounds = s.sounds
        pass

    def addSubimage(self, x, y, w, h, src):
        self.images.append({"x": x*100, "y": y*100, "w": w*100, "h": h*100, "src": src})

    def addHotspot(self, hs):
        self.hotspots.append(hs)

    def getHotspot(self, h_id):
        for i in self.hotspots:
            if i.id == h_id:
                return i

        # Try the dynamic screens...
        for ds in self.dynamic_screens:
            print ds
            hs = ds["content"].getHotspot(h_id)
            if hs:
                return hs
        return None

    def json(self):
        z_index = 0
        item_list = []
        for i in self.items:
            j = i.json()
            j["i"] = z_index
            item_list.append(j)
            z_index += 1
        image_list = []
        for i in self.images:
            i["i"] = z_index
            image_list.append(i)
            z_index += 1
        hs_list = []
        for v in self.hotspots:
            j = v.json()
            j["i"] = z_index
            hs_list.append(j)
            z_index += 1
	    print "Creating hotspot ",v.id
        snd_list = []
        for s in self.sounds:
            snd_list.append(s.json())
        vid_list = []
        for v in self.videos:
            vid_list.append(v)
        action_list = []
        for a in self.actions:
            action_list.append(a)
        dynamic_screen_list = []
        for ds in self.dynamic_screens:
            dynamic_screen_list.append({"content": ds["content"].json(), "map": ds["map"]})
        return {"id": self.id, "image": {"src": self.src_img}, "hotspots": hs_list, "items": item_list, "images": image_list, "videos": vid_list, "sounds": snd_list, "actions": action_list, "dynamic_screens": dynamic_screen_list}

"""
# This contains a single variable of state
class Variable:
    BOOL, INT = [1, 2]
    def __init__(self):
        self.id = ""
        self.type = Variable.BOOL
        self.val = False

    def fromDOM(self, elem):
        self.id = elem.getAttribute("id")
        t = elem.getAttribute("type")
        if t == "boolean":
            self.type = Variable.BOOL

        if elem.hasAttribute("initial"):
            if self.type == Variable.BOOL:
                if elem.getAttribute("initial") == "false":
                    self.val = False
                else:
                    self.val = True

    def toggle(self):
        if self.type == Variable.BOOL:
            self.val = not self.val
"""

class Item:
    def __init__(self):
        self.id = None
        self.elem = None

        self.location = ""

        self.api_obj = None

	# Used if we're saving a game
	self.must_ignore_elem = False
	self.json_store = None
        pass

    def fromAPI(self, i):
        self.api_obj = i
        self.location = i.default_location
        self.id = i.id
        pass

    def json(self):
        if self.api_obj is not None:
            return {"id": self.api_obj.id, "thumbnail": self.api_obj.thumbnail, "fullsize": self.api_obj.fullsize}

	if self.must_ignore_elem:
            return self.json_store

        e = self.elem.getElementsByTagName("thumbnail")
        thumb = e.item(0).getAttribute("src")
        e = self.elem.getElementsByTagName("fullsize")
        full = e.item(0).getAttribute("src")
        m = re.match(r"(.*)\:(.*)", full)
        obj = {"type": "image", "src": full}
        if m:
            if m.groups()[0] == "dynamic":
                # Note that the JS will request the slide to be rendered on demand
                obj = {"type": "slide", "src": m.groups()[1]}
                pass

	e = self.elem.getElementsByTagName("aspect").item(0)
	aspect = 1.0
	if e:
            m = re.match(r"([0-9\.]+):([0-9\.]+)", e.getAttribute("val"))
	    aspect = float(m.groups()[0]) / float(m.groups()[1])
	    obj["aspect"] = aspect

	e = self.elem.getElementsByTagName("width").item(0)
	if e:
            obj["setWidth"] = float(e.getAttribute("val"))

	e = self.elem.getElementsByTagName("height").item(0)
	if e:
            obj["setHeight"] = float(e.getAttribute("val"))
        return {"id": self.id, "thumbnail": thumb, "fullsize": obj}

    def fromDOM(self, elem):
        self.id = elem.getAttribute("id")
        self.elem = elem
        self.location = elem.getAttribute("default-location")

    def __getstate__(self):
        return {"json": self.json(), "location": self.location}

    def __setstate__(self, state):
        self.__init__()
        self.must_ignore_elem = True
        self.json_store = state["json"]
	self.location = state["location"]
        pass

def elemGetAttr(elem, key, default=None):
    if elem.hasAttribute(key):
        return elem.getAttribute(key)
    else:
        return default

import pickle

class APIClientInterface:
    def __init__(self, interface):
        self.interface = interface

    def sendDeltaSlide(self, ds):
        self.interface.sendRpc({"action": "loadDeltaSlide", "delta": ds.json()})
        pass

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        self.interface = None

# This is the supreme container
class State:
    def __init__(self):
        # Static state
        self.slides = {}
        self.dynamic_screens = {} # A list so that we can track hotspots

        # Dynamic state
        self.players = {}
        self.state = {"has_red_overlay": True}
	self.interface = None

        # Lyst's internal state
        self.state["__lyst"] = {"dynamic_screens": {}, "player_items": []}

    def addInterface(self, interface):
        self.interface = interface
	self.state["__lyst"]["interface"] = APIClientInterface(interface)

    # Used to debug the pickling process to figure out what won't pickle.
    def debugPickle(self, topickle):
        for k,v in topickle.items():
		try:
                    print "%s: %s"%(k, len(pickle.dumps(v)))
		except:
                    print "*** Could not pickle %s"%k
		    did_work = False
	if not did_work:
                print "Finished trying everything, errors occurred."
	else:
                print "Finished trying everything, error-free"
        pass

    def statePureDict(self):
        #print "State: ", self.state
	#print "Slides: ", self.slides
	#open("state-out.save", "w").write("%s"%self.state)
	#open("slides-out.save", "w").write("%s"%self.slides)
	if False:
            did_work = True
	    for k,v in self.state.items():
                try:
                    print "%s: %s"%(k, len(pickle.dumps(v)))
		except:
                    print "*** Could not pickle %s"%k
		    self.debugPickle(v)
		    did_work = False
	    if not did_work:
                print "Finished trying everything, errors occurred."
	    else:
                print "Finished trying everything, error-free"

	return {"content": pickle.dumps(self.state)}
	#return {"slides": pickle.dumps(self.slides)}
	return {"content": pickle.dumps(self.state)}
        #return {"content": pickle.dumps(self.state), "slides": pickle.dumps(self.slides)}

    def stateFromDict(self, d):
        # The dom should be loaded by main.py
	#dom = xml.dom.minidom.parse("../worlds/lasa/world.xml")
	#self.fromDOM(dom)

	# Reset the state b/c the DOM sets the state, which is unwanted.
	self.state = {}
        self.state = pickle.loads(d["content"])
        #self.slides = pickle.loads(d["slides"])
	# TODO: This shouldn't rely on the world being LASA.
	dom = xml.dom.minidom.parse("../worlds/lasa/world.xml")
        for i in dom.getElementsByTagName("dynamic_screen"):
            if i.parentNode.nodeName == "world":
                self.dynamicScreenFromDOM(i)
            pass
        pass

    # Returns a Slide instance.
    def render(self, p_id):
        # Go find the relevant nodes
        cur_slide = self.slides[self.players[p_id].cur_slide_id]
        ds = RenderSlide()
        cur_slide.logic.render(ds, self.state)
        self.players[p_id].cur_slide = ds

        # Add the items
        ds.items = []
        for i in self.state["__lyst"]["player_items"]:
            ds.items.append(self.state["item:"+i])

	# This is a little bit hackish, but it gets the job done.
	print "Red overlay: ",self.state["has_red_overlay"]
	if self.state["has_red_overlay"]:
            ds.actions.append({"action": "setRedOverlay"})
	else:
            ds.actions.append({"action": "unsetRedOverlay"})

	# Another hack, even worse than the last.
	# TODO: Implement a <background-noise> tag.
	import world_api
	if "noc-" == self.players[p_id].cur_slide_id[:4]:
            snd = world_api.Sound()
	    snd.file = "noc-background.ogg"
	    snd.volume = 0.5
	    snd.looping = True
            ds.sounds.append(snd)
	else:
            snd = world_api.Sound()
	    snd.file = "noc-background.ogg"
	    snd.volume = 0.0
	    snd.looping = True
            ds.sounds.append(snd)

        return ds

    def evaluateHotspotAction(self, action):
        # For now, we only support <variable>+=<integer>
        print "Evaluating hotspot action %s"%action
        match = re.match(r"([a-zA-Z\.\-_\[\]0-9]+?)(\+=|-=|=)([\d\.\-]+|true|false)\(?(.*)\)?", action)
        if match:
            var_name = match.groups()[0]
            v = match.groups()[2]
            op = match.groups()[1]
            extra = match.groups()[3]

	    if v == "true":
                v = True
	    elif v == "false":
                v = False

            var_elems = var_name.split(".")
            var_reference = ""
            for e in var_elems:
                m2 = re.match(r"([a-zA-Z_]+)\[(\d+)\]", e)
                if m2:
                    var_reference += "[\"%s\"][%s]"%(m2.groups()[0], m2.groups()[1])
                else:
                    var_reference += "[\"%s\"]"%e
            print "%s => %s %s %s"%(var_name, var_reference, op, v)
            exec("self.state%s %s %s"%(var_reference,op,v))

            # Execute the (one or more) 'extra'(s)
            print "We have some extra data: '%s'"%extra
            for m2 in re.finditer(r"(\w*)\(([^\)]*),?\)", extra):
                fn = m2.groups()[0]
                g = m2.groups()[1:]
                if fn == "mod":
                    # The modulo operator!
                    print g
                    mod_factor = int(g[0])
                    exec("self.state%s = self.state%s %% %i"%(var_reference, var_reference, mod_factor))
                pass
            pass
        else:
            print "Could not understand '%s'"%action
        pass

    # Has the given player click on the given hotspot
    def triggerHotspot(self, p_id, h_id):
        slide = self.players[p_id].cur_slide
        hs = slide.getHotspot(h_id)
        is_from_ds = False
        ds_key = ""
        if not hs:
            for key, ds in self.dynamic_screens.items():
                for hss in ds.hotspots:
                    if hss.id == h_id:
                        hs = hss
                        is_from_ds = True
                        ds_key = key
                        break
            #hs = self.getDynamicScreen(h_id)

        # First, check if it has an API call...
	if not hs:
            # TODO: Fix this bug.
            print "WARNING: hs == None after pulled from dynamic screen"
	    return
        apicall = hs.getAPICall()
        if apicall:
            tocall = getattr(api, apicall["method"])
            retval = tocall(h_id, apicall["args"], self.state)
            if retval is not None:
                s = RenderDeltaSlide()
                s.fromAPI(retval)
                return s

        # Perform the default events...
        print "Triggering hotspot: ", hs.getAction()
        for a in hs.getAction().split(","):
            action = a.split(":")
            if action[0] == "state":
                if action[1] == "toggle":
                    self.state[action[2]] = not self.state[action[2]]
                elif action[1] == "eval":
                    # Shoot, it's an evaluation.
                    self.evaluateHotspotAction(action[2])
                elif action[1] == "set":
                    if action[3] == "true":
                        self.state[action[2]] = True
                    else:
                        self.state[action[2]] = False
            elif action[0] == "link":
                # Move to said panel by linking
                self.players[p_id].cur_slide_id = action[1]

		# Link also carries with it a sound. Let's play it.
                import world_api
                ds = world_api.DeltaSlide()
		ds.add(world_api.DSPlaySound("link.wav"))
                s = RenderDeltaSlide()
		s.fromAPI(ds)
		self.state["__lyst"]["interface"].sendDeltaSlide(s)
                pass
            elif action[0] == "move":
                # Move to said panel by moving
                self.players[p_id].cur_slide_id = action[1]
                pass
            elif action[0] == "take":
                # Take said item
                self.state["item:"+action[1]].location = "player:%s"%p_id
                #self.players[p_id].items.append(self.state["item:"+action[1]])
                #self.players[p_id].items.append(action[1])
		self.state["__lyst"]["player_items"].append(action[1])
                pass
	    elif action[0] == "play":
                import world_api
                ds = world_api.DeltaSlide()
		ds.add(world_api.DSPlaySound("link.wav"))
                s = RenderDeltaSlide()
		s.fromAPI(ds)
		self.state["__lyst"]["interface"].sendDeltaSlide(s)
                pass
	    elif action[0] == "action":
                if action[1] == "closeItem":
                    # Send a quick note to close the slide
                    import world_api
		    ds = world_api.DeltaSlide()
		    ds.add(world_api.DSCustomEvent({"action": "closeItem"}))
                    s = RenderDeltaSlide()
		    s.fromAPI(ds)
                    self.state["__lyst"]["interface"].sendDeltaSlide(s)
	    elif action[0] == "affectmain":
                is_from_ds = False
        print "(new) Current slide: %s"%(self.players[p_id].cur_slide)

        # We may only want to reload the dynamic screen it's from
        if is_from_ds:
            return {"type": "ds", "slide": self.renderDynamicScreen(ds_key).json()}
            pass

        pass

    def itemDragged(self, p_id, item_id, item_pos):
        # Find the hotspot the item was dragged to
        slide = self.players[p_id].cur_slide
        overlapping = []
        for hs in slide.hotspots:
            # Check to see if it's overlapping this hotspot.
            print hs.getAction(), hs.options
            if hs.contains(item_pos["left"],item_pos["top"]):
                # Does this hotspot allow taking items?
                if "can-takeitem" in hs.options:
                    # For now, they're keyed to the item.
                    #if hs.getAction() == "take:%s"%item_id:
                    overlapping.append(hs)
		elif "put:" in hs.getAction():
                    overlapping.append(hs)
		elif hs.getAPICall("itemDragged"):
                    overlapping.append(hs)
            pass

        print "There are %i hotspots overlapping %s"%(len(overlapping),item_pos)
        if len(overlapping) == 0:
            print "There are no overlapping hotspots that will take an item."
            return

        # Trigger an API callback for the topmost hotspot
        apicall = overlapping[-1].getAPICall("itemDragged")
        if apicall: # Disabled until the below code can be integrated
            tocall = getattr(api, apicall["method"])
            retval = tocall(item_id, overlapping[-1].id, apicall["args"], self.state)
            if retval:
                # Remove item, add to the slide
                self.state["item:"+item_id].location = self.players[p_id].cur_slide_id
		self.state["__lyst"]["player_items"].remove(item_id)
		print "Player's items: ", self.state["__lyst"]["player_items"], item_id
                print self.players[p_id].items, item_id
                for i in self.players[p_id].items:
                    if i.id == item_id:
                        self.players[p_id].items.remove(i)
                        break
                pass
        else:
            # We want to remove the item from inventory and add it to the slide
            self.state["item:"+item_id].location = self.players[p_id].cur_slide_id
	    self.state["__lyst"]["player_items"].remove(item_id)
            print self.players[p_id].items, item_id
            for i in self.players[p_id].items:
                if i.id == item_id:
                    self.players[p_id].items.remove(i)
                    break

    #def getDynamicScreen(self, dyn_id):
    #    print self.dynamic_screens
    #    return self.dynamic_screens["notebook"]

    def renderDynamicScreen(self, dyn_id):
        dynscr = self.state["__lyst"]["dynamic_screens"][dyn_id]
        s = dynscr.render(self.state)
        self.dynamic_screens[dyn_id] = s
        print "My dynamic screens: ", self.dynamic_screens
        return s

    # Loads the world from a DOM
    def fromDOM(self, dom):
        for h in dom.getElementsByTagName("hotspot-template"):
            self.hotspotTemplateFromDOM(h)

        for s in dom.getElementsByTagName("slide"):
            self.slideFromDOM(s)

        for v in dom.getElementsByTagName("state"):
            self.stateFromDOM(v)

        for i in dom.getElementsByTagName("item"):
            self.itemFromDOM(i)

        for i in dom.getElementsByTagName("dynamic_screen"):
            if i.parentNode.nodeName == "world":
                self.dynamicScreenFromDOM(i)
            pass

        for i in dom.getElementsByTagName("api:onCreation"):
            args = {}
            for c in i.childNodes:
                if c.nodeType == xml.dom.Node.ELEMENT_NODE:
                    if c.prefix == "api" and c.localName == "arg":
                        args[c.getAttribute("key")] = c.getAttribute("value")

            if i.localName == "onCreation":
                exec("d = api.%s(args, self.state)"%i.getAttribute("method"))
                if "items" in d:
                    for item in d["items"]:
                        self.itemFromAPI(item)
                pass

            pass

    def dynamicScreenFromDOM(self, elem):
        self.state["__lyst"]["dynamic_screens"][elem.getAttribute("id")] = DynamicScreen(elem)

    def hotspotTemplateFromDOM(self, elem):
        hotspot_Templates[elem.getAttribute("id")] = HotspotTemplate(elem)

    def itemFromAPI(self, i_def):
        i = Item()
        i.fromAPI(i_def)
        self.state["item:"+i.id] = i
        pass

    def itemFromDOM(self, elem):
        i = Item()
        i.fromDOM(elem)
        self.state["item:"+i.id] = i
        pass

    def stateFromDOM(self, elem):
        var_name = elem.getAttribute("id")
        var_type = elem.getAttribute("type")
        val = 0
        if var_type == "boolean":
            if elemGetAttr(elem, "initial", default="true") == "true":
                val = True
            else:
                val = False
        self.state[var_name] = val
        pass

    def slideFromDOM(self, elem):
        id = elem.getAttribute("id")
        self.slides[id] = Slide()
        self.slides[id].fromDOM(elem)
        pass

    # Reset/initialize the state
    def reset(self):
        pass

    def addPlayer(self,p):
        self.players[p.id] = p

from twisted.internet import reactor

def schedule(delay, fn, *args):
    reactor.callLater(delay, fn, *args)
    print "Scheduling task for %f seconds in the future"%delay
    pass

if __name__=="__main__":
    # For a demo, let's load it from a file
    dom = xml.dom.minidom.parse("world.xml")

    state = State()
    state.fromDOM(dom)
    state.reset()

    # Create a player
    p = Player()
    p.id = "lane"
    state.addPlayer(p)

    #s = {"locker-2-isopen": v1}

    # Attempt a render...
    #ds = RenderSlide()
    #state.slides['lockers'].logic.render(ds,state.state)
    ds = state.render(p.id)
    print ds.json()

    # Trigger a hotspot
    state.triggerHotspot(p.id, "open-locker")

    # Render again...
    print state.render(p.id).json()

    # Take the note...
    state.triggerHotspot(p.id, "take-note")
    print state.render(p.id).json()

    # Close the locker again...
    state.triggerHotspot(p.id, "open-locker")
    print state.render(p.id).json()
