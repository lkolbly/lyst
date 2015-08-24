"""from twisted.internet import reactor
from twisted.web.server import Site, resource
from twisted.web.static import File
from twisted.python import log"""

"""from autobahn.wamp import WampServerFactory, \
                               WampServerProtocol, \
                               exportRpc
from autobahn.websocket import listenWS"""
#from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
#from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
import asyncio
import websockets

import json, uuid, sys, os, re, datetime
import world2 as world
import xml.dom
import xml.dom.minidom
import configparser
import mongoengine
import logging

logging.getLogger('websockets.server').setLevel(logging.DEBUG)

#log.startLogging(sys.stdout)

# Parse the config file (if there is one)
config = configparser.ConfigParser()
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

def exportRpc(fn):
   return fn

# Now to the network interface
#class RpcServerProtocol(WampServerProtocol):
class RpcServerProtocol:
   def __init__(self, websocket):
      #ApplicationSession.__init__(self, config)
      #WampServerProtocol.__init__(self)
      #WebSocketServerProtocol.__init__(self)
      self.hasConnection = True
      self.websocket = websocket
      self.player = None
      self.uid = None
      self.gid = None
      self.state = None
      self.username = None
      self.game_id = None
      self.world_id = None
      print("Init!")

      self.__exported_rpc_functions = {
         "add": self.add,
         "userLogin": self.userLogin,
         "userLoginCookie": self.userLoginCookie,
         "renderDynamicSlide": self.renderDynamicSlide,
         "itemDrag": self.itemDrag,
         "saveGame": self.saveGame,
         "chooseGame": self.chooseGame,
         "startGame": self.startGame,
         "registerUser": self.registerUser,
         "slideClick": self.slideClick
      }

   def callFunction(self, fn, args):
      return self.__exported_rpc_functions[fn](*tuple(args))

   def onDisconnect(self):
      print("Lost connection to player %s"%(self.uid))
      self.hasConnection = False
      if self.uid:
         player_Index_Locks.remove(self.uid)
         del player_Index[self.uid]
      self.uid = None
      self.player = None
      self.state = None

   def sendRpc(self, payload):
      asyncio.async(self.websocket.send(json.dumps(payload)))

   def add(self, x, y):
      return x + y

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

   def generateUid(self):
      print("Generating uuid")
      return str(uuid.uuid4())

   def registerUser(self, obj):
      # TODO: Scrub the fields
      pw_hash = obj["password"]

      u = DBUser.objects(username=obj["username"]).first()
      if u:
         return {"error": "User already exists."}

      # Add the user to the database
      print("Registering user %s"%obj)
      u = DBUser(username=obj["username"], game_list=[], email=obj["email"], pw_hash=pw_hash, fullname=obj["fullname"])
      u.save()
      return {}

   def userLogin(self, username, password):
      print("User %s logged in."%username)

      u = DBUser.objects(username=username).first()
      if not u:
         print("No such user %s"%username)
         return {"error": "yes"}
      if password != u.pw_hash:
         print("Incorrect password for %s"%username)
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
      return {"games": games, "cookie": cookie, "username": username}

   def userLoginCookie(self, username, cookie):
      u = DBUser.objects(username=username).first()
      if not u:
         print("No such user '%s'"%username)
         return {"error": "yes"}
      if cookie not in u.cookies:
         print("Cookie '%s' is not valid for user %s"%(cookie, username))
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
      return {"games": games, "cookie": cookie, "username": username}

   def chooseGame(self, game_id):
      uid = self.generateUid()
      m = re.match(r"saved:(.*)", game_id)
      if m:
         uid = m.groups()[0]
      self.game_id = game_id
      return uid

   def startGame(self, uid):
      if uid in player_Index and False:
         if uid in player_Index_Locks:
            print("Player %s tried to login twice."%uid)
            return 1
         player_Index_Locks.append(uid)
         self.player = player_Index[uid]
         self.uid = uid
         print("Player %s logged in again."%uid)
      else:
         player_Index_Locks.append(uid)
         player_Index[uid] = world.Player()
         self.player = player_Index[uid]
         self.player.id = uid
         self.uid = uid
         print("Player %s initialized."%uid)

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
         print("Putting player in world %s"%world_id)
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

   def login(self, uid):
      if uid in player_Index and False:
         if uid in player_Index_Locks:
            print("Player %s tried to login twice."%uid)
            #return 1
         player_Index_Locks.append(uid)
         self.player = player_Index[uid]
         self.uid = uid
         print("Player %s logged in again."%uid)
         return open("../worlds/index").read()

      player_Index_Locks.append(uid)
      player_Index[uid] = world.Player()
      self.player = player_Index[uid]
      self.player.id = uid
      self.uid = uid
      print("Player %s logged in."%uid)

      return open("../worlds/index").read()

   def chooseWorld(self, world_id, uid):
      print("They chose world %s"%world_id)
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

   def slideClick(self, id):
      print("Clicked on: ",id)
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
               print(delta_slide.json())
               self.sendRpc({"action": "loadDeltaSlide", "delta": delta_slide.json()})
            print("Telling client to apply a delta slide")
            return 0

      slide = self.lyst_state.render(self.player.id)
      json_data = slide.json()
      print("Check check...")
      self.sendRpc({"action": "loadSlide", "slide": json_data})
      print("Telling them to load a new slide.")

      return 0

   def renderDynamicSlide(self, dyn_id):
      slide = self.lyst_state.renderDynamicScreen(dyn_id)
      #self.sendRpc(slide.json())
      return slide.json()

   def itemDrag(self, obj):
      item_id = obj["id"]
      item_pos = obj["pos"]
      print("%s was dragged to %s"%(item_id, item_pos))
      self.lyst_state.itemDragged(self.player.id, item_id, item_pos)
      slide = self.lyst_state.render(self.player.id)
      self.sendRpc({"action": "loadSlide", "slide": slide.json()})
      return 0

@asyncio.coroutine
def websocketHandler(websocket, path):
   print("%s"%path)
   protocol = RpcServerProtocol(websocket)
   while 1:
      x = yield from websocket.recv()
      if x == None:
         break
      # Do what they say.
      obj = json.loads(x)
      res = protocol.callFunction(obj["action"], obj["args"])
      print(res)
      if res != None and "callback_id" in obj:
         yield from websocket.send(json.dumps({"_cb_id": obj["callback_id"], "result": res}))

if __name__ == '__main__':
   start_server = websockets.serve(websocketHandler, 'localhost', 9000, subprotocols=['binary'])
   asyncio.get_event_loop().run_until_complete(start_server)
   asyncio.get_event_loop().run_forever()
