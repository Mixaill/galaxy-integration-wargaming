import os
import subprocess
import xml.etree.ElementTree as ET

import helper

class WGCApplication():
    DETACHED_PROCESS = 0x00000008
    INFO_FILE = 'game_info.xml'
    METADATA_FILE = 'game_metadata\\metadata.xml'

    def __init__(self, folder):
        self._folder = folder

        gameinfo_file = os.path.join(self._folder, self.INFO_FILE)
        if not os.path.exists(gameinfo_file):
            raise AttributeError("%s does not exists" % gameinfo_file)

        metadata_file = os.path.join(self._folder, self.METADATA_FILE)
        if not os.path.exists(metadata_file):
            raise AttributeError("%s does not exists" % metadata_file)

        self._gameinfo = ET.parse(gameinfo_file).getroot()
        self._metadata = ET.parse(metadata_file).getroot()

    def GetId(self):
        return self._metadata.find('app_id').text
    
    def GetName(self):
        return self._metadata.find('shortcut_name').text

    def IsInstalled(self):
        return bool(self._gameinfo.find('game/installed').text)

    def GetExecutableName(self):
        return self._metadata.find('executable_name').text

    def GetExecutablePath(self):
        return os.path.join(self._folder, self.GetExecutableName())

    def RunExecutable(self):
        subprocess.Popen([self.GetExecutablePath()], creationflags=self.DETACHED_PROCESS)



class WGC():
    WGC_PROGRAMDATA_DIR = 'Wargaming.net\\GameCenter\\'
    WGC_PATH_FILE = 'Wargaming.net\\GameCenter\\data\\wgc_path.dat'
    WGC_APPSLOCATION_DIR = 'Wargaming.net\\GameCenter\\apps\\'
    WGC_EXECUTABLE_NAME = 'WGC.exe'

    def __init__(self):
        self._games = dict()
        self.ScanGames()
        pass
    
    def IsInstalled(self):
        return self.GetWgcDirectory() != None

    def GetWgcDirectory(self):
        #try to use path from wgc_path.data
        wgc_path_file = os.path.join(os.getenv('PROGRAMDATA'), self.WGC_PATH_FILE)
        if os.path.exists(wgc_path_file):
            wgc_path = None
            with open(wgc_path_file, 'r') as file_content:
                wgc_path = file_content.read()
            if os.path.exists(os.path.join(wgc_path,self.WGC_EXECUTABLE_NAME)):
                return wgc_path

        #fall back to program data
        wgc_programdata_dir = os.path.join(os.getenv('PROGRAMDATA'), self.WGC_PROGRAMDATA_DIR)
        if os.path.exists(os.path.join(wgc_programdata_dir,self.WGC_EXECUTABLE_NAME)):
            return wgc_programdata_dir

        return None

    def ScanGames(self):
        self._games.clear()

        if not self.IsInstalled():
            return None

        appslocation_dir = os.path.join(os.getenv('PROGRAMDATA'), self.WGC_APPSLOCATION_DIR)
        if not os.path.exists(appslocation_dir):
            return None

        app_files = [item.path for item in helper.scantree(appslocation_dir) if item.is_file() ]
        for app_file in app_files:
            app_path = None
            with open(app_file, 'r', encoding="utf-8") as file_content:
                app_path = file_content.read()

            app = WGCApplication(app_path)
            self._games[app.GetId()] = app

    def GetInstalledGames(self):
        return self._games.values()

    def GetGame(self, game_id):
        if game_id in self._games:
            return self._games[game_id]
  
        return None

    def UninstallGame(self):
        #TODO: <GAME_DIR>/wgc_api.exe --uninstall
        pass

