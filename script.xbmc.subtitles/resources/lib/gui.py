# -*- coding: utf-8 -*-

import os
import re
import sys
import xbmc
import urllib
import socket
import xbmcvfs
import xbmcgui
import unicodedata
import tempfile

from utilities import *

STATUS_LABEL   = 100
LOADING_IMAGE  = 110
SUBTITLES_LIST = 120
SERVICES_LIST  = 150
CANCEL_DIALOG  = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )

_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__      = sys.modules[ "__main__" ].__addon__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__profile__    = sys.modules[ "__main__" ].__profile__ 

SERVICE_DIR    = os.path.join(__cwd__, "resources", "lib", "services")

class GUI( xbmcgui.WindowXMLDialog ):
        
  def __init__( self, *args, **kwargs ):        
    pass

  def onInit( self ):
    self.on_run()

  def on_run( self ):
    if not xbmc.getCondVisibility("VideoPlayer.HasSubtitles"):
      self.getControl( 111 ).setVisible( False )
    try:
      self.list_services()
    except:
      self.newWindow = False
      self.list_services()
      
    try:
      self.Search_Subtitles()
    except:
      errno, errstr = sys.exc_info()[:2]
      xbmc.sleep(2000)
      self.close()      

  def set_allparam(self):       
    self.list           = []
    service_list        = []
    self.stackPath      = []
    service             = ""
    self.man_search_str = ""   
    self.newWindow      = True
    self.temp           = False
    self.rar            = False
    self.stack          = False
    self.autoDownload   = False
    movieFullPath       = urllib.unquote(xbmc.Player().getPlayingFile()).decode('utf-8')# Full path of a playing file
    path                = __addon__.getSetting( "subfolder" ) == "true"                 # True for movie folder
    self.sub_folder     = xbmc.translatePath(__addon__.getSetting( "subfolderpath" )).decode("utf-8")   # User specified subtitle folder
    self.year           = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
    self.season         = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
    self.episode        = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
    self.mansearch      =  __addon__.getSetting( "searchstr" ) == "true"                # Manual search string??
    self.parsearch      =  __addon__.getSetting( "par_folder" ) == "true"               # Parent folder as search string
    self.language_1     = languageTranslate(__addon__.getSetting( "Lang01" ), 4, 0)     # Full language 1
    self.language_2     = languageTranslate(__addon__.getSetting( "Lang02" ), 4, 0)     # Full language 2  
    self.language_3     = languageTranslate(__addon__.getSetting( "Lang03" ), 4, 0)     # Full language 3
    self.tmp_sub_dir    = os.path.join( __profile__ ,"sub_tmp" )                        # Temporary subtitle extraction directory   
    self.stream_sub_dir = os.path.join( __profile__ ,"sub_stream" )                     # Stream subtitle directory    

    if ( movieFullPath.find("http") > -1 ):
      if not xbmcvfs.exists(self.stream_sub_dir):
        os.makedirs(self.stream_sub_dir)
      else:
        rem_files(self.stream_sub_dir)
      self.sub_folder = self.stream_sub_dir
      self.temp = True

    elif ( movieFullPath.find("rar://") > -1 ):
      self.rar = True
#      self.temp = True
      movieFullPath = movieFullPath[6:]
      if path:
        self.sub_folder = os.path.dirname(os.path.dirname( movieFullPath ))
    
    elif ( movieFullPath.find("stack://") > -1 ):
      self.stackPath = movieFullPath.split(" , ")
      movieFullPath = self.stackPath[0][8:]
      self.stack = True

    if not path:
      if len(self.sub_folder) < 1 :
        self.sub_folder = os.path.dirname( movieFullPath )

    if path and not self.rar and not self.temp:
      if self.sub_folder.find("smb://") > -1:
        if self.temp:
          dialog = xbmcgui.Dialog()
          self.sub_folder = dialog.browse( 0, _( 766 ), "files")
        else:
          self.sub_folder = os.path.dirname( movieFullPath )
      else:
        self.sub_folder = os.path.dirname( movieFullPath )
    
    if self.episode.lower().find("s") > -1:                                 # Check if season is "Special"             
      self.season = "0"                                                     #
      self.episode = self.episode[-1:]                                      #

    self.tvshow    = unicodedata.normalize('NFKD',
                      unicode(unicode(xbmc.getInfoLabel
                      ("VideoPlayer.TVshowtitle"), 'utf-8'))
                      ).encode('ascii','ignore')                            # Show
    self.title     = unicodedata.normalize('NFKD', 
                      unicode(unicode(xbmc.getInfoLabel
                      ("VideoPlayer.Title"), 'utf-8'))
                      ).encode('ascii','ignore')                            # Title

    if self.tvshow == "":
      if str(self.year) == "":
        title, season, episode = regex_tvshow(False, self.title)
        if episode != "":
          self.season = str(int(season))
          self.episode = str(int(episode))
          self.tvshow = title
        else:
          self.title, self.year = xbmc.getCleanMovieTitle( self.title )
    else:
      self.year = ""

    self.file_original_path = urllib.unquote ( movieFullPath )              # Movie Path

    if __addon__.getSetting( "disable_hash_search" ) == "true":
      self.temp = True

    if (__addon__.getSetting( "fil_name" ) == "true"):                   # Display Movie name or search string
      self.file_name = os.path.basename( movieFullPath )
    else:
      if (len(str(self.year)) < 1 ) :
        self.file_name = self.title.encode('utf-8')
        if (len(self.tvshow) > 0):
          self.file_name = "%s S%.2dE%.2d" % (self.tvshow.encode('utf-8'), int(self.season), int(self.episode) )
      else:
        self.file_name = "%s (%s)" % (self.title.encode('utf-8'), str(self.year),)    

    if not xbmcvfs.exists(self.tmp_sub_dir):
      os.makedirs(self.tmp_sub_dir)
    else:
      rem_files(self.tmp_sub_dir)

    if (__addon__.getSetting( "auto_download" ) == "true") and (__addon__.getSetting( "auto_download_file" ) != os.path.basename( movieFullPath )):
        self.autoDownload = True
        __addon__.setSetting("auto_download_file", "")

    for name in os.listdir(SERVICE_DIR):
      if os.path.isdir(os.path.join(SERVICE_DIR,name)) and __addon__.getSetting( name ) == "true":
        service_list.append( name )
        service = name

    if len(self.tvshow) > 0:
      def_service = __addon__.getSetting( "deftvservice")
    else:
      def_service = __addon__.getSetting( "defmovieservice")
      
    if service_list.count(def_service) > 0:
      service = def_service

    if len(service_list) > 0:  
      if len(service) < 1:
        self.service = service_list[0]
      else:
        self.service = service  

      self.service_list = service_list
      self.next = list(service_list)
      self.controlId = -1
      self.subtitles_list = []

      log( __name__ ,"Manual Search : [%s]"        % self.mansearch)
      log( __name__ ,"Default Service : [%s]"      % self.service)
      log( __name__ ,"Services : [%s]"             % self.service_list)
      log( __name__ ,"Temp?: [%s]"                 % self.temp)
      log( __name__ ,"Rar?: [%s]"                  % self.rar)
      log( __name__ ,"File Path: [%s]"             % self.file_original_path)
      log( __name__ ,"Year: [%s]"                  % str(self.year))
      log( __name__ ,"Tv Show Title: [%s]"         % self.tvshow)
      log( __name__ ,"Tv Show Season: [%s]"        % self.season)
      log( __name__ ,"Tv Show Episode: [%s]"       % self.episode)
      log( __name__ ,"Movie/Episode Title: [%s]"   % self.title)
      log( __name__ ,"Subtitle Folder: [%s]"       % self.sub_folder)
      log( __name__ ,"Languages: [%s] [%s] [%s]"   % (self.language_1, self.language_2, self.language_3,))
      log( __name__ ,"Parent Folder Search: [%s]"  % self.parsearch)
      log( __name__ ,"Stacked(CD1/CD2)?: [%s]"     % self.stack)
  
    return movieFullPath

  def Search_Subtitles( self, gui = True ):
    self.subtitles_list = []
    if gui:
      self.getControl( SUBTITLES_LIST ).reset()
      self.getControl( LOADING_IMAGE ).setImage( xbmc.translatePath( os.path.join( SERVICE_DIR, self.service, "logo.png") ) )

    exec ( "from services.%s import service as Service" % (self.service))
    self.Service = Service
    if gui:
      self.getControl( STATUS_LABEL ).setLabel( _( 646 ) )
    msg = ""
    socket.setdefaulttimeout(float(__addon__.getSetting( "timeout" )))
    try: 
      self.subtitles_list, self.session_id, msg = self.Service.search_subtitles( self.file_original_path, self.title, self.tvshow, self.year, self.season, self.episode, self.temp, self.rar, self.language_1, self.language_2, self.language_3, self.stack )
    except socket.error:
      errno, errstr = sys.exc_info()[:2]
      if errno == socket.timeout:
        msg = _( 656 )
      else:
        msg =  "%s: %s" % ( _( 653 ),str(errstr[1]), )
    except:
      errno, errstr = sys.exc_info()[:2]
      msg = "Error: %s" % ( str(errstr), )
    socket.setdefaulttimeout(None)
    if gui:
      self.getControl( STATUS_LABEL ).setLabel( _( 642 ) % ( "...", ) )

    if not self.subtitles_list:
      if ((__addon__.getSetting( "search_next" )== "true") and (len(self.next) > 1)):
        xbmc.sleep(1500)
        self.next.remove(self.service)
        self.service = self.next[0]
        try:
          select_index = self.service_list.index(self.service)
        except IndexError:
          select_index = 0
        if gui:  
          self.getControl( SERVICES_LIST ).selectItem( select_index )
        log( __name__ ,"Auto Searching '%s' Service" % (self.service,) )
        self.Search_Subtitles(gui)
      else:
        self.next = list(self.service_list)
        if gui:
          select_index = 0
          if msg != "":
            self.getControl( STATUS_LABEL ).setLabel( msg )
          else:
            self.getControl( STATUS_LABEL ).setLabel( _( 657 ) )
          if self.newWindow:
            window_list = SERVICES_LIST
            try:
              select_index = self.service_list.index(self.service)
            except IndexError:
              select_index = 0
          else:
            window_list = SUBTITLES_LIST
            self.list_services()   
          if gui:
            self.setFocusId( window_list )
            self.getControl( window_list ).selectItem( select_index )
    else:
      if not self.newWindow: self.list_services()
      subscounter = 0
      itemCount = 0
      for item in self.subtitles_list:
        if self.autoDownload and item["sync"] and  (item["language_name"] == languageTranslate(languageTranslate(self.language_1,0,2),2,0)):
          self.Download_Subtitles(itemCount, True, gui)
          __addon__.setSetting("auto_download_file", os.path.basename( self.file_original_path ))
          return True
          break
        else:
          if gui:
            listitem = xbmcgui.ListItem( label=item["language_name"], label2=item["filename"], iconImage=item["rating"], thumbnailImage=item["language_flag"] )
            if item["sync"]:
              listitem.setProperty( "sync", "true" )
            else:
              listitem.setProperty( "sync", "false" )
            self.list.append(subscounter)
            subscounter = subscounter + 1                                    
            self.getControl( SUBTITLES_LIST ).addItem( listitem )
        itemCount += 1
      
      if gui:
        self.getControl( STATUS_LABEL ).setLabel( '%i %s '"' %s '"'' % (len ( self.subtitles_list ), _( 744 ), self.file_name,) ) 
        self.setFocusId( SUBTITLES_LIST )
        self.getControl( SUBTITLES_LIST ).selectItem( 0 )
      return False

  def Download_Subtitles( self, pos, auto = False, gui = True ):
    if gui:
      if auto:
        self.getControl( STATUS_LABEL ).setLabel(  _( 763 ) )
      else:
        self.getControl( STATUS_LABEL ).setLabel(  _( 649 ) )
    zip_subs = os.path.join( self.tmp_sub_dir, "zipsubs.zip")
    zipped, language, file = self.Service.download_subtitles(self.subtitles_list, pos, zip_subs, self.tmp_sub_dir, self.sub_folder,self.session_id)
    sub_lang = str(languageTranslate(language,0,2))

    if zipped :
      self.Extract_Subtitles(zip_subs,sub_lang, gui)
    else:
      sub_ext  = os.path.splitext( file )[1]
      sub_name = os.path.splitext( os.path.basename( self.file_original_path ) )[0]
      if (__addon__.getSetting( "lang_to_end" ) == "true"):
        file_name = "%s.%s%s" % ( sub_name, sub_lang, sub_ext )
      else:
        file_name = "%s%s" % ( sub_name, sub_ext )
      file_from = file.replace('\\','/')
      file_to = os.path.join(self.sub_folder, file_name).replace('\\','/')
      # Create a files list of from-to tuples so that multiple files may be
      # copied (sub+idx etc')
      files_list = [(file_from,file_to)]
      # If the subtitle's extension sub, check if an idx file exists and if so
      # add it to the list
      if ((sub_ext == ".sub") and (os.path.exists(file[:-3]+"idx"))):
          log( __name__ ,"found .sub+.idx pair %s + %s" % (file_from,file_from[:-3]+"idx"))
          files_list.append((file_from[:-3]+"idx",file_to[:-3]+"idx"))
      for cur_file_from, cur_file_to in files_list:
         subtitle_set,file_path  = copy_files( cur_file_from, cur_file_to )
      # Choose the last pair in the list, second item (destination file)
      if subtitle_set:
        subtitle = files_list[-1][1]
        xbmc.Player().setSubtitles(subtitle.encode("utf-8"))
        self.close()
      else:
        if gui:
          select_index = 0
          self.getControl( STATUS_LABEL ).setLabel( _( 654 ) )
          if self.newWindow:
            window_list = SERVICES_LIST
            try:
              select_index = self.service_list.index(self.service)
            except IndexError:
              select_index = 0
          else:
            window_list = SUBTITLES_LIST
            self.list_services()   
          self.setFocusId( window_list )
          self.getControl( window_list ).selectItem( select_index )

  def Extract_Subtitles( self, zip_subs, subtitle_lang, gui = True ):
    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip_subs,self.tmp_sub_dir,)).encode('utf-8'))
    xbmc.sleep(1000)
    files = os.listdir(self.tmp_sub_dir)
    sub_filename = os.path.basename( self.file_original_path )
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass" ]
    subtitle_set = False
    if len(files) < 1 :
      if gui:
        self.getControl( STATUS_LABEL ).setLabel( _( 654 ) )
        if self.newWindow:  
          self.setFocusId( SERVICES_LIST )
          try:
            select_index = self.service_list.index(self.service)
          except IndexError:
            select_index = 0
          self.getControl( SERVICES_LIST ).selectItem( select_index )
        else:
          self.list_services()
    else :
      if gui:
        self.getControl( STATUS_LABEL ).setLabel(  _( 652 ) )
      subtitle_set = False
      movie_sub = False
      episode = 0
      for zip_entry in files:
        if os.path.splitext( zip_entry )[1] in exts:
          subtitle_file, file_path = self.create_name(zip_entry,sub_filename,subtitle_lang)
          if len(self.tvshow) > 0:
            title, season, episode = regex_tvshow(False, zip_entry)
            if not episode : episode = -1
          else:
            if os.path.splitext( zip_entry )[1] in exts:
              movie_sub = True
          if ( movie_sub or int(episode) == int(self.episode) ):
            if self.stack:
              try:
                for subName in self.stackPath:
                  if (re.split("(?x)(?i)\CD(\d)", zip_entry)[1]) == (re.split("(?x)(?i)\CD(\d)", urllib.unquote ( subName ))[1]):
                    subtitle_file, file_path = self.create_name(zip_entry,urllib.unquote ( os.path.basename(subName[8:]) ),subtitle_lang)
                    subtitle_set,file_path = copy_files( subtitle_file, file_path ) 
                if re.split("(?x)(?i)\CD(\d)", zip_entry)[1] == "1":
                  subToActivate = file_path
              except:
                subtitle_set = False              
            else:
              subtitle_set,subToActivate = copy_files( subtitle_file, file_path )

      if not subtitle_set:
        for zip_entry in files:
          if os.path.splitext( zip_entry )[1] in exts:
            subtitle_file, file_path = self.create_name(zip_entry,sub_filename,subtitle_lang)
            subtitle_set,subToActivate  = copy_files( subtitle_file, file_path )

    if subtitle_set :
      xbmc.Player().setSubtitles(subToActivate.encode("utf-8"))
      self.close()
    else:
      if gui:
        select_index = 0
        self.getControl( STATUS_LABEL ).setLabel( _( 654 ) )
        if self.newWindow:
          window_list = SERVICES_LIST
          try:
            select_index = self.service_list.index(self.service)
          except IndexError:
            select_index = 0
        else:
          window_list = SUBTITLES_LIST
          self.list_services()   
        self.setFocusId( window_list )
        self.getControl( window_list ).selectItem( select_index )

  def create_name(self,zip_entry,sub_filename,subtitle_lang): 
    if self.temp:
      name = "temp_sub"
    else:
      name = os.path.splitext( sub_filename )[0]
    if (__addon__.getSetting( "lang_to_end" ) == "true"):
      file_name = "%s.%s%s" % ( name, subtitle_lang, os.path.splitext( zip_entry )[1] )
    else:
      file_name = "%s%s" % ( name, os.path.splitext( zip_entry )[1] )
    return os.path.join(self.tmp_sub_dir, zip_entry), os.path.join(self.sub_folder, file_name)

  def list_services( self ):
    self.list = []
    if self.newWindow:
      window_list = SERVICES_LIST
      win_label   = "%s"
    else:
      window_list = SUBTITLES_LIST   
      win_label   = "[COLOR=FF0084ff]%s%s[/COLOR]" % (_( 610 ), "%s")

    self.getControl( window_list ).reset()
  
    for serv in self.service_list:
      listitem = xbmcgui.ListItem( win_label % serv )
      self.list.append(serv)
      listitem.setProperty( "man", "false" )
      self.getControl( window_list ).addItem( listitem )

    if self.mansearch :
        listitem = xbmcgui.ListItem( win_label % _( 612 ) )
        listitem.setProperty( "man", "true" )
        self.list.append("Man")
        self.getControl( window_list ).addItem( listitem )

    if self.parsearch :
        listitem = xbmcgui.ListItem( win_label % _( 747 ) )
        listitem.setProperty( "man", "true" )
        self.list.append("Par")
        self.getControl( window_list ).addItem( listitem )
      
    listitem = xbmcgui.ListItem( win_label % _( 762 ) )
    listitem.setProperty( "man", "true" )
    self.list.append("Set")
    self.getControl( window_list ).addItem( listitem )    

  def keyboard(self, parent):
    dir, self.year = xbmc.getCleanMovieTitle(self.file_original_path, self.parsearch)
    if not parent:
      try:
        subhelper = open(tempfile.gettempdir() + '/subhelper.dat')
        srchstr = subhelper.read()
        subhelper.close()
      except:
        srchstr = None
      if srchstr:
        pass
      elif self.man_search_str != "":
        srchstr = self.man_search_str
      else:
        srchstr = "%s (%s)" % (dir,self.year,)  
      kb = xbmc.Keyboard(srchstr, _( 751 ), False)
      text = self.file_name
      kb.doModal()
      if (kb.isConfirmed()): text, self.year = xbmc.getCleanMovieTitle(kb.getText())
      self.title = text
      self.man_search_str = text
    else:
      self.title = dir   

    log( __name__ ,"Manual/Keyboard Entry: Title:[%s], Year: [%s]" % (self.title, self.year,))
    if self.year != "" :
      self.file_name = "%s (%s)" % (self.file_name, str(self.year),)
    else:
      self.file_name = self.title   
    self.tvshow = ""
    self.next = list(self.service_list)
    self.Search_Subtitles() 

  def onClick( self, controlId ):
    if controlId == SUBTITLES_LIST:
      if self.newWindow:
        self.Download_Subtitles( self.getControl( SUBTITLES_LIST ).getSelectedPosition() )
      else:
        selection = str(self.list[self.getControl( SUBTITLES_LIST ).getSelectedPosition()])
        if selection.isdigit():
          log( __name__ , "Selected : [%s]" % (selection, ) )
          self.Download_Subtitles( int(selection) )
          
    elif controlId == SERVICES_LIST:
      xbmc.executebuiltin("Skin.Reset(SubtitleSourceChooserVisible)")
      selection = str(self.list[self.getControl( SERVICES_LIST ).getSelectedPosition()]) 
      self.setFocusId( 120 )
   
      if selection == "Man":
        self.keyboard(False)
      elif selection == "Par":
        self.keyboard(True)
      elif selection == "Set":
        __addon__.openSettings()
        self.set_allparam()
        self.on_run()        
      else:
        self.service = selection
        self.next = list(self.service_list)
        self.Search_Subtitles()      

  def onFocus( self, controlId ):
    if controlId == 150:
      try:
        select_index = self.service_list.index(self.service)
      except IndexError:
        select_index = 0
      self.getControl( SERVICES_LIST ).selectItem(select_index)
    self.controlId = controlId
    try:
      if controlId == 8999:
        self.setFocusId( 150 )
    except:
      pass

  def onAction( self, action ):
    if ( action.getId() in CANCEL_DIALOG):
      self.close()

