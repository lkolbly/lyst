from twisted.internet import reactor
from twisted.web.server import Site, resource
from twisted.web.static import File
from twisted.python import log
from autobahn.wamp import WampServerFactory, \
                               WampServerProtocol, \
                               exportRpc
from autobahn.websocket import listenWS
import json, uuid, sys, os, re, datetime
import world2 as world
import xml.dom
import xml.dom.minidom
import ConfigParser
import mongoengine

log.startLogging(sys.stdout)

# Parse the config file (if there is one)
config = ConfigParser.ConfigParser()
config.read("config.cfg")

db_server = None
if config.has_option("Database", "server"):
   db_server = config.get("Database", "server")

# Connect to the database
class DBGame(mongoengine.EmbeddedDocument):
   state = mongoengine.DictField()
   uid = mongoengine.StringField()
   cur_slide = mongoengine.StringField()
   world_id = mongoengine.StringField()
   save_time = mongoengine.DateTimeField()

class DBUser(mongoengine.Document):
   username = mongoengine.StringField(required=True)
   fullname = mongoengine.StringField(required=True)
   email = mongoengine.StringField(required=True)
   pw_hash = mongoengine.StringField(required=True)
   #uid_list = mongoengine.ListField(mongoengine.StringField())
   game_list = mongoengine.ListField(mongoengine.EmbeddedDocumentField(DBGame))
   cookies = mongoengine.ListField(mongoengine.StringField())

mongoengine.connect("lyst")

# Each player has a uid, so that they can save state across connections
player_Index = {}
player_Index_Locks = []
lyst_Player_Worlds = {}

#lyst_States = {}

#dom = xml.dom.minidom.parse("../worlds/lasa/world.xml")
#lyst_States["lasa"] = world.State()
#lyst_States["lasa"].fromDOM(dom)
#lyst_States["lasa"].reset()

# Now to the network interface
class RpcServerProtocol(WampServerProtocol):
   def __init__(self):
      #WampServerProtocol.__init__(self)
      self.hasConnection = False
      self.player = None
      self.uid = None
      self.gid = None
      self.state = None
      self.username = None
      self.game_id = None
      self.world_id = None
      print "Init!"

   def connectionLost(self, reason):
      print "Lost connection to player %s, due to %s"%(self.uid,reason)
      self.hasConnection = False
      if self.uid:
         player_Index_Locks.remove(self.uid)
         del player_Index[self.uid]
      self.uid = None
      self.player = None
      self.state = None
      WampServerProtocol.connectionLost(self, reason)

   @exportRpc("add")
   def add(self, x, y):
      return x + y

   @exportRpc
   def saveGame(self):
      g = DBGame(state=self.lyst_state.statePureDict(), uid=self.gid, cur_slide=self.player.cur_slide_id, world_id=self.world_id, save_time=datetime.datetime.now())
      u = DBUser.objects(username=self.username).first()
      for i in range(len(u.game_list)):
         if u.game_list[i].uid == g.uid:
            u.game_list[i] = g
            u.save()
            return 0
      u.game_list.append(g)
      u.save()

      # Tell them we saved the game...
      return json.dumps({"world": self.world_id})

   @exportRpc
   def generateUid(self):
      print "Generating uuid"
      return "asdf"#str(uuid.uuid4())

   @exportRpc
   def registerUser(self, obj):
      # TODO: Scrub the fields
      pw_hash = obj["password"]

      u = DBUser.objects(username=obj["username"]).first()
      if u:
         return {"error": "User already exists."}

      # Add the user to the database
      print "Registering user %s"%obj
      u = DBUser(username=obj["username"], game_list=[], email=obj["email"], pw_hash=pw_hash, fullname=obj["fullname"])
      u.save()
      return {}

   @exportRpc
   def userLogin(self, username, password):
      print "User %s logged in."%username

      u = DBUser.objects(username=username).first()
      if not u:
         #u = DBUser(username=username, game_list=[])
         #u.save()
         print "No such user %s"%username
         return {"error": "yes"}
      if password != u.pw_hash:
         print "Incorrect password for %s"%username
         return {"error": "yes"}

      self.username = username

      # Create a *new* cookie for this connection.
      cookie = str(uuid.uuid4())
      u.cookies.append(cookie)
      u.save()

      # Generate a list of games this user has saved + New Game options.
      games = []
      for g in u.game_list:
         games.append({"id": "saved:%s"%g["uid"], "desc": "World %s save game at %s"%(g.world_id, g.save_time.strftime("%x %X"))})
      worlds = open("../worlds/index").readlines()
      for w in worlds:
         w = w.strip(" \r\n")
         games.append({"id": "new:%s"%w, "desc": "A new game in world %s."%w})
      #games.append({"id": "new:lasa", "desc": "A new game in world LASA."})
      return {"games": games, "cookie": cookie, "username": username}
      return self.generateUid()

   @exportRpc
   def userLoginCookie(self, username, cookie):
      u = DBUser.objects(username=username).first()
      if not u:
         print "No such user '%s'"%username
         return {"error": "yes"}
      if cookie not in u.cookies:
         print "Cookie '%s' is not valid for user %s"%(cookie, username)
         return {"error": "yes"}

      self.username = username

      # Generate a list of games this user has saved + New Game options.
      games = []
      for g in u.game_list:
         games.append({"id": "saved:%s"%g["uid"], "desc": "World %s save game at %s"%(g.world_id, g.save_time.strftime("%x %X"))})
      worlds = open("../worlds/index").readlines()
      for w in worlds:
         w = w.strip(" \r\n")
         games.append({"id": "new:%s"%w, "desc": "A new game in world %s."%w})
      #games.append({"id": "new:lasa", "desc": "A new game in world LASA."})
      return {"games": games, "cookie": cookie, "username": username}
      return self.generateUid()
      return self.userLogin("lane", "foobar")

   @exportRpc
   def chooseGame(self, game_id):
      uid = self.generateUid()
      m = re.match(r"saved:(.*)", game_id)
      if m:
         uid = m.groups()[0]
      self.game_id = game_id
      return uid

   @exportRpc
   def startGame(self, uid):
      if uid in player_Index and False:
         if uid in player_Index_Locks:
            print "Player %s tried to login twice."%uid
            return 1
         player_Index_Locks.append(uid)
         self.player = player_Index[uid]
         self.uid = uid
         print "Player %s logged in again."%uid
      else:
         player_Index_Locks.append(uid)
         player_Index[uid] = world.Player()
         self.player = player_Index[uid]
         self.player.id = uid
         self.uid = uid
         print "Player %s initialized."%uid

      m = re.match(r"saved:(.*)", self.game_id)
      if not m:

         m = re.match(r"new:(.*)", self.game_id)
         dom = xml.dom.minidom.parse("../worlds/%s/world.xml"%m.groups()[0])
         self.world_id = "lasa"
         self.sendRpc({"action": "setCDNGameName", "name": m.groups()[0]})
         self.lyst_state = world.State()
         self.lyst_state.fromDOM(dom)
         self.lyst_state.reset()
         self.lyst_state.addPlayer(self.player)
         self.lyst_state.addInterface(self)
         self.gid = str(uuid.uuid4())

         m = re.match(r"new:(.*)", self.game_id)
         lyst_Player_Worlds[uid] = m.groups()[0]#"lasa"#world_id
      else:
         u = DBUser.objects(username=self.username).first()
         g = None
         for g2 in u.game_list:
            if g2.uid == uid:
               g = g2
               self.gid = g2.uid
               break
         d = g.state

         world_id = g.world_id
         self.world_id = world_id
         print "Putting player in world %s"%world_id
         dom = xml.dom.minidom.parse("../worlds/%s/world.xml"%world_id)
         self.sendRpc({"action": "setCDNGameName", "name": world_id})
         self.lyst_state = world.State()
         self.lyst_state.fromDOM(dom)
         self.lyst_state.stateFromDict(d)
         self.player.cur_slide_id = g.cur_slide
         self.lyst_state.addPlayer(self.player)
         self.lyst_state.addInterface(self)
         lyst_Player_Worlds[uid] = g.world_id
         pass

      if not self.game_id:
         # This shouldn't happen...
         pass

      self.slideClick(0)
      return 0

   @exportRpc
   def login(self, uid):
      if uid in player_Index and False:
         if uid in player_Index_Locks:
            print "Player %s tried to login twice."%uid
            #return 1
         player_Index_Locks.append(uid)
         self.player = player_Index[uid]
         self.uid = uid
         print "Player %s logged in again."%uid
         return open("../worlds/index").read()

      player_Index_Locks.append(uid)
      player_Index[uid] = world.Player()
      self.player = player_Index[uid]
      self.player.id = uid
      self.uid = uid
      print "Player %s logged in."%uid

      return open("../worlds/index").read()

   @exportRpc
   def chooseWorld(self, world_id, uid):
      print "They chose world %s"%world_id
      #self.player.world = world.LystWorld("../worlds/%s/world.xml"%world_id)
      #self.lyst_state = lyst_States[world_id]

      # We're doing single player mode, so create a new state.
      dom = xml.dom.minidom.parse("../worlds/lasa/world.xml")
      self.lyst_state = world.State()
      self.lyst_state.fromDOM(dom)
      self.lyst_state.reset()
      self.lyst_state.addPlayer(self.player)

      lyst_Player_Worlds[uid] = world_id

      self.slideClick(0)

      return 0

   @exportRpc
   def slideClick(self, id):
      print "Clicked on: ",id
      if id != 0:
         #self.player.clickOnHotspot(id)
         delta_slide = self.lyst_state.triggerHotspot(self.player.id, id)

         # Note that certain hotspots are better handled by applying a delta
         # to the already rendered slide.
         if delta_slide:
            # Blech. Ideally I would have some sort of third type for this.
            if isinstance(delta_slide, dict):
               self.sendRpc({"action": "loadDynScr", "delta": delta_slide})
            else:
               print delta_slide.json()
               self.sendRpc({"action": "loadDeltaSlide", "delta": delta_slide.json()})
            print "Telling client to apply a delta slide"
            return 0
      #print self, self.player
      #print self.player.world, self.player.currentSlide
      #slide = self.player.world.get_slide(self.player.currentSlide)
      slide = self.lyst_state.render(self.player.id)
      #print slide.json()
      self.sendRpc({"action": "loadSlide", "slide": slide.json()})
      print "Telling them to load a new slide."

      return 0

   @exportRpc
   def renderDynamicSlide(self, dyn_id):
      slide = self.lyst_state.renderDynamicScreen(dyn_id)
      #self.sendRpc(slide.json())
      return slide.json()

   @exportRpc
   def itemDrag(self, obj):
      item_id = obj["id"]
      item_pos = obj["pos"]
      print "%s was dragged to %s"%(item_id, item_pos)
      self.lyst_state.itemDragged(self.player.id, item_id, item_pos)
      slide = self.lyst_state.render(self.player.id)
      self.sendRpc({"action": "loadSlide", "slide": slide.json()})
      return 0

   def sendRpc(self, payload):
      if not self.hasConnection:
         return
      #print "Sending RPC..."
      self.sendMessage(json.dumps([9, payload]))

   def onSessionOpen(self):
      self.registerForRpc(self, "http://example.com/simple/calc#")
      self.registerForPubSub("http://example.com/calcevent#evt1")
      #reactor.callLater(2, self.sendRpc, {"action": "loadSlide", "slide": {"image": 5}})
      self.hasConnection = True
 
class Picture(resource.Resource):
   isLeaf = True
   def render_GET(self, request):
      path = "../worlds/lasa/%s/%s"%("/".join(request.prepath), "/".join(request.postpath))
      if "JPG" in path or "jpg" in path:
         request.setHeader("Content-Type", "image/jpeg")
      elif "png" in path:
         request.setHeader("Content-Type", "image/png")
      elif "cur" in path:
         request.setHeader("Content-Type", "image/png")
      #request.setHeader("cache-control", "public")
      return open(path).read()

class CDNResource(resource.Resource):
   isLeaf = True
   def render_GET(self, request):
      try:
         cdn_data = open("../cdn_list").read()
      except:
         cdn_data = "[]"
      return "var Game_CDNs = %s;"%cdn_data

class Root(resource.Resource):
   isLeaf = False
   def getChild(self, name, request):
      print "Name: %s"%name
      if name == "index.html" or name == "":
         return self
      elif name == "cdns":
         return CDNResource()
      #elif name == "pictures" or name == "sounds":
      #   return Picture()
      elif name == "templates" or name == "pictures" or name == "sounds" or name == "cursors" or name == "css" or name == "js":
         return self
      return self

   def resizeImage(self, file_a, file_b, size):
      if "jpg" in file_a or "JPG" in file_b:
         from PIL import Image
         im = Image.open(file_a)
         im = im.resize((int(size[0]), int(size[1])))
         im.save(file_b)
         pass
      else:
         open(file_b, "w").write(open(file_a).read())

   def render_GET(self, request):
      # We need to figure out the disk path to the resource
      uid = request.getCookie("lyst_user_uid")
      #print uid, lyst_Player_Worlds
      if uid in lyst_Player_Worlds:
         world_name = lyst_Player_Worlds[uid]
      elif "world" in request.args:
         world_name = request.args["world"][0]
      else:
         world_name = ""
      if len(request.prepath) > 1:
         if request.prepath[1] == "pictures" and request.prepath[0] != "full" and request.prepath[0] != "null":
            # Let's resize it
            import tempfile
            path = "../worlds/%s/%s"%(world_name,"/".join(request.prepath[1:]))
            tf = tempfile.mkstemp(suffix=".%s"%request.prepath[-1].split(".")[-1])
            os.close(tf[0])
            foobar = request.prepath[0]
            if foobar == "null":
               foobar = "full"
            self.resizeImage(path, tf[1], foobar.split("x"))
            path = tf[1]
         elif request.prepath[1] == "pictures" or request.prepath[1] == "videos":
            path = "../worlds/%s/%s"%(world_name,"/".join(request.prepath[1:]))
         elif request.prepath[0] == "sounds":
            path = "../worlds/%s/sounds/%s"%(world_name,"/".join(request.prepath[1:]))
         else:
            path = "../%s"%("/".join(request.prepath))
      else:
         path = "../%s"%("/".join(request.prepath))
      print path, request.prepath, request.postpath

      # Now, serve the content
      try:
         if "css" in path:
            request.setHeader("Content-Type", "text/css")
         elif "js" in path:
            request.setHeader("Content-Type", "application/javascript")
         elif "JPG" in path or "jpg" in path:
            request.setHeader("Content-Type", "image/jpeg")
         elif "png" in path:
            request.setHeader("Content-Type", "image/png")
         elif "cur" in path:
            request.setHeader("Content-Type", "image/png")
         elif "manifest" in path:
            request.setHeader("Content-Type", "text/cache-manifest")
         elif "webm" in path:
            request.setHeader("Content-Type", "video/webm")
         elif "ogg" in path:
            request.setHeader("Content-Type", "audio/ogg")
         elif "wav" in path:
            request.setHeader("Content-Type", "audio/wav")
         elif ".ico" in path:
            request.setHeader("Content-Type", "image/x-icon")
         elif "mp3" in path:
            request.setHeader("Content-Type", "audio/mpeg")
         if "html" not in path:
            request.setHeader("Expires", "Mon, 31 Dec 2035 12:00:00 GMT")
         return open(path).read()
      except IOError:
         print "Got an error serving '%s'"%path
         request.setResponseCode(404)
         return "<html><body>Not found!</body></html>"
      print request.prepath
      return open("./%s"%("".join(request.prepath))).read()

if __name__ == '__main__':
   factory = WampServerFactory("ws://localhost:9000", debugWamp=True)
   factory.protocol = RpcServerProtocol
   listenWS(factory)

   #webdir = File("../")
   #web = Site(webdir)
   web = Site(Root())
   reactor.listenTCP(9001, web)

   reactor.run()
