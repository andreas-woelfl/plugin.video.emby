#################################################################################################
# CreateFiles
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os, sys
import json
import time
from calendar import timegm
from datetime import datetime

import string
import unicodedata

from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.etree import ElementTree
from xml.dom import minidom
import xml.etree.cElementTree as ET

from DownloadUtils import DownloadUtils
from API import API
from PlayUtils import PlayUtils
import Utils as utils
from ReadEmbyDB import ReadEmbyDB


addon = xbmcaddon.Addon(id='plugin.video.emby')
addondir = xbmc.translatePath(addon.getAddonInfo('profile'))
dataPath = os.path.join(addondir,"library")
movieLibrary = os.path.join(dataPath,'movies')
tvLibrary = os.path.join(dataPath,'tvshows')
musicvideoLibrary = os.path.join(dataPath,'musicvideos')

class CreateFiles():   
    def createSTRM(self,item):
        item_type=str(item.get("Type")).encode('utf-8')
        if item_type == "Movie":
            itemPath = os.path.join(movieLibrary,item["Id"])
            strmFile = os.path.join(itemPath,item["Id"] + ".strm")

        if item_type == "MusicVideo":
            itemPath = os.path.join(musicvideoLibrary,item["Id"])
            strmFile = os.path.join(itemPath,item["Id"] + ".strm")

        if item_type == "Episode":
            itemPath = os.path.join(tvLibrary,item["SeriesId"])
            if str(item.get("IndexNumber")) != None:
                filenamestr = self.CleanName(utils.convertEncoding(item.get("SeriesName"))) + " S" + str(item.get("ParentIndexNumber")) + "E" + str(item.get("IndexNumber")) + " (" + item["Id"] + ").strm"
            else:
                filenamestr = self.CleanName(utils.convertEncoding(item.get("SeriesName"))) + " S0E0 " + self.CleanName(utils.convertEncoding(item.get("Name"))) + " (" + item["Id"] + ").strm"
            strmFile = os.path.join(itemPath,filenamestr)

        changes = False
        if not xbmcvfs.exists(strmFile):
            changes = True
            xbmcvfs.mkdir(itemPath)
            text_file = open(strmFile, "w")
            
            playUrl = "plugin://plugin.video.emby/?id=" + item["Id"] + '&mode=play'

            text_file.writelines(playUrl)
            text_file.close()
            
            #set timestamp on file - this will make sure that the dateadded field is properly set
            if item.get("DateCreated") != None:
                try:
                    timestamp = time.mktime(datetime.strptime(item.get("DateCreated").split(".")[0]+"GMT", "%Y-%m-%dT%H:%M:%S%Z").timetuple())
                    os.utime(strmFile,(timestamp,timestamp))
                except:
                    pass
        return changes
            
    def createNFO(self,item):
        downloadUtils = DownloadUtils()
        timeInfo = API().getTimeInfo(item)
        userData=API().getUserData(item)
        people = API().getPeople(item)
        mediaStreams=API().getMediaStreams(item)
        studios = API().getStudios(item)
        userid = downloadUtils.getUserId()
        port = addon.getSetting('port')
        host = addon.getSetting('ipaddress')
        server = host + ":" + port  
        item_type=str(item.get("Type"))
        
        if item_type == "Movie":
            itemPath = os.path.join(movieLibrary,item["Id"])
            nfoFile = os.path.join(itemPath,item["Id"] + ".nfo")
            rootelement = "movie"
        if item_type == "MusicVideo":
            itemPath = os.path.join(musicvideoLibrary,item["Id"])
            nfoFile = os.path.join(itemPath,item["Id"] + ".nfo")
            rootelement = "musicvideo"
        if item_type == "Series":
            itemPath = os.path.join(tvLibrary,item["Id"])
            nfoFile = os.path.join(itemPath,"tvshow.nfo")
            rootelement = "tvshow"
        if item_type == "Episode":
            itemPath = os.path.join(tvLibrary,item["SeriesId"])
            if str(item.get("ParentIndexNumber")) != None:
                filenamestr = self.CleanName(utils.convertEncoding(item.get("SeriesName"))) + " S" + str(item.get("ParentIndexNumber")) + "E" + str(item.get("IndexNumber")) + " (" + item["Id"] + ").nfo"
            else:
                filenamestr = self.CleanName(utils.convertEncoding(item.get("SeriesName"))) + " S0E0 " + self.CleanName(utils.convertEncoding(item["Name"])) + " (" + item["Id"] + ").nfo"
            nfoFile = os.path.join(itemPath,filenamestr)
            rootelement = "episodedetails"
            
            
        changes = False
        if not xbmcvfs.exists(nfoFile):
            changes = True
            utils.logMsg("MB3 Syncer","creating NFO file " + nfoFile,2)
            xbmcvfs.mkdir(itemPath)        
            root = Element(rootelement)
            SubElement(root, "id").text = item["Id"]
            SubElement(root, "uniqueid").text = item["Id"]

            if item.get("Tag") != None:
                for tag in item.get("Tag"):
                    SubElement(root, "tag").text = tag
            
            SubElement(root, "thumb").text = API().getArtwork(item, "Primary")
            
            if item_type == 'Series':
                seasonData = ReadEmbyDB().getTVShowSeasons(item["Id"])
                if seasonData != None:
                    for season in seasonData:
                        if season.has_key("IndexNumber"):
                            seasonart = API().getArtwork(season, "Primary")
                            if seasonart != None:
                                SubElement(root, "thumb",{"type":"season","aspect":"poster","season":str(season["IndexNumber"])}).text = seasonart
                            seasonart2 = API().getArtwork(season, "Banner")
                            if seasonart2 != None:
                                SubElement(root, "thumb",{"type":"season","aspect":"banner","season":str(season["IndexNumber"])}).text = seasonart2
            
            SubElement(root, "fanart").text = API().getArtwork(item, "Backdrop")
            SubElement(root, "title").text = utils.convertEncoding(item["Name"])
            SubElement(root, "originaltitle").text = utils.convertEncoding(item["Name"])
            SubElement(root, "sorttitle").text = utils.convertEncoding(item["SortName"])
            
            if userData.get("LastPlayedDate") != None:
                SubElement(root, "lastplayed").text = userData.get("LastPlayedDate")
            else:
                SubElement(root, "lastplayed").text = ""

            if item.has_key("Album"):
                SubElement(root, "album").text = item["Album"]
                
            if item.has_key("Artist"):
                SubElement(root, "artist").text = item["Artist"][0]
            
            if item.has_key("OfficialRating"):
                SubElement(root, "mpaa").text = item["OfficialRating"]
            
            if item.get("CriticRating") != None:
                rating = int(item.get("CriticRating"))/10
                SubElement(root, "rating").text = str(rating)
            
            if item.get("DateCreated") != None:
                dateadded = item["DateCreated"].replace("T"," ")
                dateadded = dateadded.replace(".0000000Z","")
                SubElement(root, "dateadded").text = dateadded
            
            if userData.get("PlayCount") != None:
                SubElement(root, "playcount").text = userData.get("PlayCount")
                if int(userData.get("PlayCount")) > 0:
                    SubElement(root, "watched").text = "true"
            
            if timeInfo.get("ResumeTime") != None:
                resume_sec = int(round(float(timeInfo.get("ResumeTime"))))*60
                total_sec = int(round(float(timeInfo.get("TotalTime"))))*60
                if resume_sec != 0:
                    resume = SubElement(root, "resume")
                    SubElement(resume, "position").text = str(resume_sec)
                    SubElement(resume, "total").text = str(total_sec)
            
            if item_type == "Episode":
                SubElement(root, "season").text = str(item.get("ParentIndexNumber"))
                SubElement(root, "episode").text = str(item.get("IndexNumber"))
                
            SubElement(root, "year").text = str(item.get("ProductionYear"))
            if item.get("PremiereDate") != None:
                premieredatelist = (item.get("PremiereDate")).split("T")
                premieredate = premieredatelist[0]
                SubElement(root, "firstaired").text = premieredate
                SubElement(root, "premiered").text = premieredate
                SubElement(root, "aired").text = premieredate
                
            if(timeInfo.get('Duration') != "0"):
                SubElement(root, "runtime").text = str(timeInfo.get('Duration'))
            
            SubElement(root, "plot").text = utils.convertEncoding(API().getOverview(item))
            
            if item.get("ShortOverview") != None:
                SubElement(root, "outline").text = utils.convertEncoding(item.get("ShortOverview"))
            
            if item.get("TmdbCollectionName") != None:
                SubElement(root, "set").text = item.get("TmdbCollectionName")
            
            if item.get("ProviderIds") != None:
                if item.get("ProviderIds").get("Imdb") != None:
                    SubElement(root, "imdbnumber").text = item
            
            if people.get("Writer") != None:
                for writer in people.get("Writer"):
                    SubElement(root, "credits").text = utils.convertEncoding(writer)
            
            if people.get("Director") != None:
                for director in people.get("Director"):
                    SubElement(root, "director").text = utils.convertEncoding(director)
            
            if item.get("Genres") != None:
                for genre in item.get("Genres"):
                    SubElement(root, "genre").text = utils.convertEncoding(genre)
            
            if studios != None:
                for studio in studios:
                    SubElement(root, "studio").text = utils.convertEncoding(studio).replace("/", "&")
                    
            if item.get("ProductionLocations") != None:
                for country in item.get("ProductionLocations"):
                    SubElement(root, "country").text = utils.convertEncoding(country)

            #trailer link
            trailerUrl = None
            if item.get("LocalTrailerCount") != None and item.get("LocalTrailerCount") > 0:
                itemTrailerUrl = "http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + item.get("Id") + "/LocalTrailers?format=json"
                jsonData = downloadUtils.downloadUrl(itemTrailerUrl, suppress=False, popup=0 )
                if(jsonData != ""):
                    trailerItem = json.loads(jsonData)
                    if trailerItem[0].get("LocationType") == "FileSystem":
                        trailerUrl = "plugin://plugin.video.emby/?id=" + trailerItem[0].get("Id") + '&mode=play'
                        SubElement(root, "trailer").text = trailerUrl
            
            #add streamdetails
            fileinfo = SubElement(root, "fileinfo")
            streamdetails = SubElement(fileinfo, "streamdetails")
            video = SubElement(streamdetails, "video")
            SubElement(video, "duration").text = str(mediaStreams.get('totaltime'))
            SubElement(video, "aspect").text = mediaStreams.get('aspectratio')
            SubElement(video, "codec").text = mediaStreams.get('videocodec')
            SubElement(video, "width").text = str(mediaStreams.get('width'))
            SubElement(video, "height").text = str(mediaStreams.get('height'))
            SubElement(video, "duration").text = str(timeInfo.get('Duration'))
            
            audio = SubElement(streamdetails, "audio")
            SubElement(audio, "codec").text = mediaStreams.get('audiocodec')
            SubElement(audio, "channels").text = mediaStreams.get('channels')
            
            #add people
            if item.get("People") != None:
                for actor in item.get("People"):
                    if(actor.get("Type") == "Actor"):
                        actor_elem = SubElement(root, "actor")
                        SubElement(actor_elem, "name").text = utils.convertEncoding(actor.get("Name"))
                        SubElement(actor_elem, "type").text = utils.convertEncoding(actor.get("Role"))
                        SubElement(actor_elem, "thumb").text = downloadUtils.imageUrl(actor.get("Id"), "Primary", 0, 400, 400)
            
            # Some devices such as Mac are using an older version of python
            try:
                 # 2.7 and greater
                ET.ElementTree(root).write(nfoFile, xml_declaration=True)
            except:
                 # <2.7
                ET.ElementTree(root).write(nfoFile)
           

        return changes
    
    def copyThemeMusic(self,item):
        downloadUtils = DownloadUtils()
        userid = downloadUtils.getUserId()
        port = addon.getSetting('port')
        host = addon.getSetting('ipaddress')
        server = host + ":" + port  
        item_type=str(item.get("Type"))
        
        if item_type == "Movie":
            itemPath = os.path.join(movieLibrary,item["Id"])
            themeFile = os.path.join(itemPath,"theme.mp3")
        if item_type == "Series":
            itemPath = os.path.join(tvLibrary,item["Id"])
            themeFile = os.path.join(itemPath,"theme.mp3")
            
            
        if not xbmcvfs.exists(themeFile):
            utils.logMsg("MB3 Syncer","creating Theme file " + themeFile,2)
            #theme music link
            themeMusicUrl = "http://" + server + "/mediabrowser/Items/" + item["Id"] + "/ThemeSongs?format=json"
            jsonData = downloadUtils.downloadUrl(themeMusicUrl, suppress=False, popup=0 )
            if(jsonData != ""):
                themeMusic = json.loads(jsonData)           
                if(themeMusic != None and themeMusic["TotalRecordCount"] > 0):
                    themeItems = themeMusic["Items"]
                    if themeItems[0] != None:
                        mediasources = themeItems[0]["MediaSources"]
                        if mediasources[0]["Container"] == "mp3":
                            themeUrl =  PlayUtils().getPlayUrl(server,themeItems[0]["Id"],themeItems[0])
                            xbmcvfs.copy(themeUrl,themeFile)
                            
    def copyExtraFanart(self,item):
        downloadUtils = DownloadUtils()
        userid = downloadUtils.getUserId()
        port = addon.getSetting('port')
        host = addon.getSetting('ipaddress')
        server = host + ":" + port  
        item_type=str(item.get("Type"))
        
        if item_type == "Movie":
            itemPath = os.path.join(movieLibrary,item["Id"])
            fanartDir = os.path.join(itemPath,"extrafanart" + os.sep)
        if item_type == "Series":
            itemPath = os.path.join(tvLibrary,item["Id"])
            fanartDir = os.path.join(itemPath,"extrafanart" + os.sep)
            
        if not xbmcvfs.exists(fanartDir):
            utils.logMsg("MB3 Syncer","creating extrafanart directory ",2)
            xbmcvfs.mkdir(fanartDir)
            fullItem = ReadEmbyDB().getFullItem(item["Id"])
            if(fullItem != None and fullItem["BackdropImageTags"] != None and len(fullItem["BackdropImageTags"]) > 1):
                  totalbackdrops = len(fullItem["BackdropImageTags"])
                  for index in range(1,totalbackdrops):
                      backgroundUrl =  API().getArtwork(fullItem, "Backdrop",str(index))
                      fanartFile = os.path.join(fanartDir,"fanart" + str(index) + ".jpg")
                      xbmcvfs.copy(backgroundUrl,fanartFile)
        
    def CleanName(self, filename):
        validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
        return ''.join(c for c in cleanedFilename if c in validFilenameChars)
 