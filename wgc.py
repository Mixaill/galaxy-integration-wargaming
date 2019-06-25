import os
import subprocess
import xml.etree.ElementTree as ET

import helper
from wgc_auth import WGCAuthorization

class WGCApplication():
    DETACHED_PROCESS = 0x00000008
    INFO_FILE = 'game_info.xml'
    METADATA_FILE = 'game_metadata\\metadata.xml'
    WGCAPI_FILE = 'wgc_api.exe'

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

    def GetMutexName(self):
        return self._metadata.find('mutex_name').text

    def IsInstalled(self):
        return bool(self._gameinfo.find('game/installed').text)

    def GetGameFolder(self):
        return self._folder

    def IsRunning(self):
        return helper.is_mutex_exists(self.GetMutexName())

    def GetExecutableName(self):
        return self._metadata.find('executable_name').text

    def GetExecutablePath(self):
        return os.path.join(self.GetGameFolder(), self.GetExecutableName())

    def GetWgcapiPath(self):
        return os.path.join(self.GetGameFolder(), self.WGCAPI_FILE)

    def RunExecutable(self):
        subprocess.Popen([self.GetExecutablePath()], creationflags=self.DETACHED_PROCESS)

    def UninstallGame(self):
        subprocess.Popen([self.GetWgcapiPath(), '--uninstall'], creationflags=self.DETACHED_PROCESS, cwd = self.GetGameFolder())


class WGC():
    WGC_PROGRAMDATA_DIR = 'Wargaming.net\\GameCenter\\'
    WGC_PATH_FILE = 'Wargaming.net\\GameCenter\\data\\wgc_path.dat'
    WGC_TRACKING_FILE = 'Wargaming.net\\GameCenter\\data\\wgc_tracking_id.dat'
    WGC_APPSLOCATION_DIR = 'Wargaming.net\\GameCenter\\apps\\'
    WGC_EXECUTABLE_NAME = 'WGC.exe'

    def __init__(self):
        self._backend_authorization = WGCAuthorization(self.GetTrackingId())
        pass

    def IsInstalled(self):
        return self.GetWgcDirectory() != None

    def GetAuthorizationBackend(self):
        return self._backend_authorization

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

    def GetTrackingId(self):
        tracking_id = ''

        wgc_tracking_file = os.path.join(os.getenv('PROGRAMDATA'), self.WGC_TRACKING_FILE)
        if os.path.exists(wgc_tracking_file):
            with open(wgc_tracking_file, 'r') as file_content:
                tracking_id = file_content.read()

        return tracking_id

    def GetGames(self):
        games = dict()

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
            games[app.GetId()] = app

        return games

