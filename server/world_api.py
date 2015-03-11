import world2
import hashlib, random, os
# TODO: world2's data structure should be moved to this file.

class Image:
    def __init__(self, x, y, w, h, img_name, id=None):
        self.spec = {"x": x*100, "y": y*100, "w": w*100, "h": h*100, "src": img_name}
        if id:
            self.spec["id"] = id

class Item:
    def __init__(self, id=None):
        self.id = id
        self.thumbnail = ""
        self.fullsize = ""
        self.default_location = ""

    def getLocation(self, state):
        if not self.id:
            return ""
        return state["item:"+self.id].location

class Hotspot:
    def __init__(self):
        self.geometry = ""
        self.cursor = ""
        self.id = ""
        self.action = ""
        self.api_callbacks = {}
        self.options = []

    """
    def setAPICall(self, method, args):
        self.api_callback = {"method": method, "args": args}

    def addOption(self, option):
        self.options.append(option)
    """

    def getAPICall(self, on="hotspotClicked"):
        return self.api_callbacks.get(on, None)

    def setAPICall(self, method, args, on="hotspotClicked"):
        #self.api_callback = {"method": method, "args": args}
        self.api_callbacks[on] = {"method": method, "args": args}

    def addOption(self, option):
        self.options.append(option)

    def json(self):
        h = world2.Hotspot()
        h.fromAPI(self)
        return h.json()

def makeHotspot(geometry, action):
    hs = Hotspot()
    hs.geometry = geometry
    hs.cursor = "fwd"
    hs.action = action
    return hs

class Sound:
    def __init__(self):
        self.file = ""
        self.volume = 1.0
        self.looping = False

    def json(self):
        return {"filename": self.file, "volume": self.volume, "loop": self.looping}

class DeltaEvent:
    def __init__(self):
        self.type = None

    def json(self):
        return {}

class DSNewImage(DeltaEvent):
    def __init__(self, image):
        self.img_def = image.spec

    def json(self):
        return {"action": "NewImage", "image": self.img_def}

class DSRemoveImage(DeltaEvent):
    def __init__(self, img_id):
        self.img_id = img_id

    def json(self):
        return {"action": "RemoveImage", "img_id": self.img_id}

class DSPlaySound(DeltaEvent):
    def __init__(self, snd_file, volume=1.0):
        self.snd_id = snd_file
        self.volume = volume

    def json(self):
        snd = Sound()
        snd.file = self.snd_id
        snd.volume = self.volume
        return {"action": "PlaySound", "snd": snd.json()}

# Used to move the thinking into the API.
class DSCustomEvent(DeltaEvent):
    def __init__(self, j):
        self.j = j

    def json(self):
        return self.j

class DeltaSlide:
    def __init__(self):
        self.event_sequence = []
        pass

    def add(self, e):
        self.event_sequence.append(e)

    def json(self):
        events_json = []
        for e in self.event_sequence:
            events_json.append(e.json())
        return {"events": events_json}

class Slide:
    def __init__(self):
        self.images = []
        self.src_img = ""
        self.hotspots = []
        self.sounds = []

    def setImage(self, img_name):
        self.src_img = img_name

    def addImage(self, x, y, w, h, img_name, id=None):
        j = {"x": x*100, "y": y*100, "w": w*100, "h": h*100, "src": img_name}
        if id:
            j["id"] = id
        self.images.append(j)

    def addSVGImage(self, x,y,w,h, img_data, id=None):
        j = {"x": x*100, "y": y*100, "w": w*100, "h": h*100, "src": "<SVG>", "svg_data": img_data}
        if id:
            j["id"] = id
        self.images.append(j)

    def addHotspot(self, hs, hs2=None):
        if hs2:
            hs = makeHotspot(hs, hs2)
            self.addHotspot(hs)
            pass
        else:
            self.hotspots.append(hs)

    def addSound(self, filename, volume=1.0, looping=False):
        s = Sound()
        s.file = filename
        s.volume = volume
        s.looping = looping
        self.sounds.append(s)

    def addText(self, s, x=0.0, y=0.0, font="", kern=0.1, cwidth=0.1, cheight=0.1, ids=None):
        cnt = 0
        for c in s:
            id = None
            if ids:
                if "%i" in ids:
                    id = ids.replace("%i", str(cnt))
                if "%c" in ids:
                    id = ids.replace("%c", c)
            self.addImage(x,y,cwidth,cheight, font%c, id=id)
            x += kern
            cnt += 1
        pass

# Generates a "temporary" runtime image file, relative to the CWD.
def makeTmpImage(type="png"):
    DIRECTORY = "../pictures/tmp/"
    try:
        os.mkdir(DIRECTORY)
    except OSError:
        pass
    return "%s/%s.%s"%(DIRECTORY, hashlib.sha256("%.10f"%random.random()).hexdigest(), type)

def makeTmpImage2(type="png"):
    DIRECTORY = "tmp"
    try:
        os.mkdir(DIRECTORY)
    except OSError:
        pass
    return "%s/%s.%s"%(DIRECTORY, hashlib.sha256("%.10f"%random.random()).hexdigest(), type)

def schedule(delay, fn, *args):
    world2.schedule(delay, fn, *args)
    pass

def sendDeltaSlide(ds):
    # Pass this up to main.py
    ds.json()
    pass
