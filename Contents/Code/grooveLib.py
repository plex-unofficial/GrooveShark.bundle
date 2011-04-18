# -*- coding: utf-8 -*-
import sys, os, pickle, traceback, string, urllib, time, random, shutil, uuid, hashlib
import re, string, urllib, urllib2, socket

try:
  from PMS import JSON
except:
  try:
    import json
  except:
    print "no json support!"


from PMS import *

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import thread

#
# By Jesper Toft <jesper@bzimage.dk>
#
# Spawns an HTTPd on 127.0.0.1:<random> to handle the song requests.
#

PLUGIN_MAIN     = 'http://listen.grooveshark.com/'

CLIENT_REV = "20100211.28"

CACHE_INTERVAL = 36000


def JSONdumps(obj):
  try:
    return json.dumps(obj)
  except:
    try:
      return JSON.StringFromObject(obj)
    except:
      return None

def JSONloads(obj):
  try:
    return json.loads(obj)
  except:
    try:
      return JSON.ObjectFromString(obj)
    except:
      return None


class GrooveREQ(BaseHTTPRequestHandler):
  def do_GET(self):
    global theGrooveLib
    # Find song ID from request.
    try:
      songID = re.compile("/(.*).mp3").findall(self.path)[0]
    except:
      self.send_response(404)
      return
    
    res = theGrooveLib.getStreamInfo(songID)
    
    streamKey = res["streamKey"]
    streamServer = res["streamServer"]
    streamServerID = res["streamServerID"]
    
    self.send_response(200)
    self.send_header('Content-Type','audio/mpeg')
    self.end_headers()
    
    headers = {
      "Content-Type": "application/x-www-form-urlencoded"
    }
    url = "http://" + streamServer + "/stream.php"
    
    socket.setdefaulttimeout(5)
    try:
      fs = urllib2.urlopen(urllib2.Request(url, "streamKey=" + streamKey, headers))
    except:
      return
    
    # Stream the audio!
    n = 0
    while 1:
      s = fs.read(8192)
      if not s:
        break
      try:
        n = n + len(s)
        self.wfile.write(s)
      except:
        break
    return

  def do_POST(self):
    self.send_response(404)
    return

class GrooveHTTPD(HTTPServer):
  def get_request(self):
    self.run = True
    self.socket.settimeout(None)
    return HTTPServer.get_request(self)

  def serve(self):
    self.run = True
    while self.run:
      self.socket.settimeout(10)
      self.handle_request()
    Log("HTTPd Out!")

class GrooveLib:
  def __init__(self):
    global theGrooveLib
    theGrooveLib = self
    Log("Starting..")
    self.httpd = GrooveHTTPD( ('0.0.0.0', 0), GrooveREQ)
    sk = self.httpd.socket.getsockname()
    thread.start_new_thread(self.httpd.serve, ())
    
    self.url = "http://localhost:" + str(sk[1]) + "/"
    
    Log("Getting session..")
    body = urllib2.urlopen(urllib2.Request(PLUGIN_MAIN)).read()
    self.sessionID = re.compile("sessionID: *'([^']*)'",re.M | re.DOTALL).findall(body)[0]
    self.hostname  = re.compile( "hostname: *'([^']*)'",re.M | re.DOTALL).findall(body)[0]
    self.startTime = re.compile("startTime: *'([^']*)'",re.M | re.DOTALL).findall(body)[0]
    self.uuid = uuid.uuid4()
    self.token = None
    Log("Getting Token")
    self.token = self.generateToken()
  
  def generateToken(self):
    self.secretKey = hashlib.md5(self.sessionID).hexdigest()
    params = {
      "secretKey": self.secretKey
    }
    headers = {
      "Content-Type": "application/json"
    }
    hdr = self.makeHeader("getCommunicationToken", params);
    url = "https://" + self.hostname + "/service.php"
    reply = urllib2.urlopen(urllib2.Request(url, hdr, headers)).read()
    return JSONloads(reply)['result']
    
  def createToken(self, method):
    r = "123456"
    s = method + ":" + self.token + ":theColorIsRed:" + r
    return r + hashlib.sha1(s).hexdigest()
  
  def makeHeader(self, method, params):
    request = {
      "method" : method
    }
    request["parameters"] = params
    request["header"] = {
      "client": "gslite",
      "clientRevision": CLIENT_REV,
      "session": self.sessionID,
    }
    if self.token is not None:
      request["header"]["token"] = self.createToken(method)
    return JSONdumps(request)
    
  def makeRequest(self, method, params, sortKey = None):
    headers = {
      "Content-Type": "application/json"
    }
    groove_url = "http://" + self.hostname + "/more.php?" + method
    
    body = urllib2.urlopen(urllib2.Request(groove_url, self.makeHeader(method,params), headers)).read()
    try:
      result = JSONloads(body)
    except:
      return None
    
    res = result["result"]
    
    # Return  : Used by Search (Artist and Songs)
    # Result  : Used by Popular lists
    # songs   : Yet an other layer on Songs by artist search
    Fields = ["Return", "Result", "Songs", "songs" ]
    
    for Field in Fields:
      try:
        newRes = res[Field]
      except:
        newRes = res
      
      res = newRes
      
    if sortKey is not None:
      res.sort(lambda x,y:cmp(x[sortKey],y[sortKey]))
    return res
  
  def popularSongs(self):
    return self.makeRequest("popularGetSongs", {})

  def getStreamInfo(self, songID):
    params = {
      "prefetch": 0,
      "songID": int(songID)
    }
    res = self.makeRequest("getStreamKeyFromSongID", params);
    res = res["result"]
    return res

