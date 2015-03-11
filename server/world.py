import xml.dom.minidom as xml

lyst_Hotspot_Templates = {}

class LystHotspot:
    def __init__(self, element=None, h_id=None):
        self.left = 0
        self.top = 0
        self.width = 0
        self.height = 0
        self.id = h_id
        self.dest = None
        self.cursor = None
        if element:
            self.loadFromElement(element, h_id)

    def toJSON(self):
        o = {"width": self.width*100, "height": self.height*100, "x": self.left*100, "y":self.top*100, "id": self.id, "cursor": self.cursor}
        print o
        return o

    def fromTemplate(self, t):
        self.cursor = t.getAttribute("cursor")
        if len(self.cursor) == 0:
            self.cursor = "grab"
        geo = t.getAttribute("geometry")
        geo = geo.split(",")
        print geo
        self.left = float(geo[0])
        self.top = float(geo[1])
        right = float(geo[2])
        bottom = float(geo[3])
        self.width = right-self.left
        self.height = bottom-self.top

    def loadFromElement(self, h, h_id):
        template_id = h.getAttribute("template")
        print "template_id = %s"%template_id
        if len(template_id)>0 and template_id in lyst_Hotspot_Templates:
            t = lyst_Hotspot_Templates[template_id]
            print "Loading from %s"%t
            self.cursor = t.cursor
            self.left = t.left
            self.top = t.top
            self.width = t.width
            self.height = t.height

        geo = h.getAttribute("geometry")
        action = h.getAttribute("action")
        c = h.getAttribute("cursor")
        if len(c) > 0:
            self.cursor = c

        if not self.cursor:
            self.cursor = ""
        if len(self.cursor) == 0:
            self.cursor = "grab"
        self.dest = action[5:]
        if len(geo) > 0:
            geo = geo.split(",")
            print geo
            self.left = float(geo[0])
            self.top = float(geo[1])
            right = float(geo[2])
            bottom = float(geo[3])
            self.width = right-self.left
            self.height = bottom-self.top
        self.id = h_id
        pass

    def save(self, dom, e):
        e.setAttribute("geometry", "%f,%f,%f,%f"%(self.left,self.top,self.width+self.left,self.height+self.top))
        e.setAttribute("action", "link:%s"%(self.dest))
        e.setAttribute("cursor", self.cursor)
        pass

class LystSlide:
    def __init__(self, element=None):
        self.hotspots = []
        self.img_src = None
        self.id = None
        if element:
            self.loadFromElement(element)
        pass

    def toJSON(self):
        o = {"image": {"src": self.img_src}, "hotspots": []}
        for h in self.hotspots:
            o["hotspots"].append(h.toJSON())
        return o

    def loadFromElement(self, e):
        img = e.getElementsByTagName("image")[0]
        self.img_src = img.getAttribute("src")
        self.id = e.getAttribute("id")

        hotspots = e.getElementsByTagName("hotspot")
        cnt = 0
        for h in hotspots:
            h_id = "%s_hs%i"%(self.id,cnt)
            self.hotspots.append(LystHotspot(h, h_id))
            cnt += 1

    def get_hotspot(self, h_id):
        for h in self.hotspots:
            if h.id == h_id:
                return h
        return None

    def save(self, dom, e):
        e.setAttribute("id", self.id)

        img = dom.createElement("image")
        img.setAttribute("src", self.img_src)
        e.appendChild(img)
        for h in self.hotspots:
            h_elem = dom.createElement("hotspot")
            h.save(dom, h_elem)
            e.appendChild(h_elem)
        pass

# This class contains everything about a world
class LystWorld:
    def __init__(self, filename):
        dom = xml.parse(filename)

        # Parse out the hotspot templates
        templates = dom.getElementsByTagName("hotspot-template")
        for t in templates:
            id = t.getAttribute("id")
            hs = LystHotspot()
            hs.fromTemplate(t)
            lyst_Hotspot_Templates[id] = hs

        # Parse out the slides
        slides = dom.getElementsByTagName("slide")
        self.slides = []
        for s in slides:
            self.slides.append(LystSlide(s))
        pass

    def get_slide(self, slide_id):
        for s in self.slides:
            if s.id == slide_id:
                return s
        return None

    def save(self, filename):
        dom = xml.Document()
        world = dom.createElement("world")
        dom.appendChild(world)

        for s in self.slides:
            e = dom.createElement("slide")
            s.save(dom, e)
            world.appendChild(e)
            #e.setAttribute("id", s.id)

        print dom.toprettyxml()
        open(filename, "w").write(dom.toprettyxml())
        pass
