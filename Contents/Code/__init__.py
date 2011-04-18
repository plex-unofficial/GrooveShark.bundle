# -*- coding: utf-8 -*-
import sys, os, pickle, traceback, string, urllib, time, random, shutil
import re, string, urllib, urllib2, socket
from PMS import JSON
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import thread


from grooveLib import *

#
# By Jesper Toft <jesper@bzimage.dk>
#
# Spawns an HTTPd on 127.0.0.1:<random> to handle the song requests.
#

PLUGIN_PREFIX   = '/music/grooveshark'

CACHE_INTERVAL = 36000

####################################################################################################
def Start():
  global Groove
  Log("Starting")
  Groove = GrooveLib()
  Log(Groove.url)
  Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, 'GrooveShark', 'icon-default.png', 'art-default.png')
  Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
  MediaContainer.title1 = 'GrooveShark'
  MediaContainer.content = 'Items'
  MediaContainer.art = R('art-default.png')

####################################################################################################
def UpdateCache():
  pass
  
####################################################################################################
def MainMenu():
  dir = MediaContainer()

  dir.Append(Function(DirectoryItem(popularSongs, title="Popular Songs", summary="List of most popular songs") ))
  dir.Append(Function(DirectoryItem(popularSongs, title="Popular Songs - Sorted by Artist", summary="List of most popular songs"), sortKey="ArtistName" ))
  dir.Append(Function(SearchDirectoryItem(searchSong, title=L("Search for Song..."), prompt=L("Search for Songs"), thumb=R('search.png')) ))
  dir.Append(Function(SearchDirectoryItem(searchArtist, title=L("Search for Artist..."), prompt=L("Search for Artist"), thumb=R('search.png') )))
  
  return dir

def searchArtist(sender, query=''):
  params = {
    "type": "Artists",
    "query": query
  }
  return populateArtistList("getSearchResults", params)

def searchSong(sender, query=''):
  params = {
    "type": "Songs",
    "query": query
  }
  return populateSongList("getSearchResults", params)

def popularSongs(sender, sortKey=None):
  params = {
  }
  return populateSongList("popularGetSongs", params, sortKey)

def artistSongs(sender, artistID=None):
  params = {
    "artistID": artistID,
    "isVerified": 0,
    "offset": 0
  }
  return populateSongList("artistGetSongs",  params)

def populateArtistList(method, params, sortKey=None):
  global Groove
  dir = MediaContainer()
  
  artists = Groove.makeRequest(method, params, sortKey)
  
  for artist in artists:
    id = artist["ArtistID"]
    title = artist["Name"]
    art = None
    
    if artist["CoverArtFilename"] is not None:
      art = "http://beta.grooveshark.com/static/amazonart/m" + artist["CoverArtFilename"]
    dir.Append(Function(DirectoryItem(artistSongs, title=title), artistID=id ))
  
  return dir
  
def populateSongList(method, params, sortKey=None):
  global Groove
  dir = MediaContainer()
  
  songs = Groove.makeRequest(method, params, sortKey)
  
  for song in songs:
    try:
      id = song["SongID"]
      title = song["Name"]
      artist = song["ArtistName"]
      album = song["AlbumName"]
      art = None
      year = song["Year"]
      
      duration = None
      if song["CoverArtFilename"] is not None:
        art = "http://beta.grooveshark.com/static/amazonart/m" + song["CoverArtFilename"]
      if song["EstimateDuration"] is not None:
        duration = int(song["EstimateDuration"]) * 1000
      
      dir.Append(TrackItem(Groove.url + id + ".mp3", title=title, artist=artist, album=album, thumb=art, duration=duration))
    except:
      Log(song)
  
  return dir

