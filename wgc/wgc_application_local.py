import os
import subprocess
import xml.etree.ElementTree as ElementTree

from .wgc_helper import DETACHED_PROCESS, is_mutex_exists, fixup_gamename

class WGCLocalApplication():
    
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

        self._gameinfo = ElementTree.parse(gameinfo_file).getroot()
        self._metadata = ElementTree.parse(metadata_file).getroot()

    def GetId(self) -> str:
        return self._metadata.find('app_id').text
    
    def GetName(self) -> str:
        return fixup_gamename(self._metadata.find('shortcut_name').text)

    def GetMutexName(self) -> str:
        return self._metadata.find('mutex_name').text

    def IsInstalled(self) -> str:
        return bool(self._gameinfo.find('game/installed').text)

    def GetGameFolder(self) -> str:
        return self._folder

    def IsRunning(self) -> bool:
        return is_mutex_exists(self.GetMutexName())

    def GetExecutableName(self) -> str:
        return self._metadata.find('executable_name').text

    def GetExecutablePath(self) -> str:
        return os.path.join(self.GetGameFolder(), self.GetExecutableName())

    def GetWgcapiPath(self) -> str:
        return os.path.join(self.GetGameFolder(), self.WGCAPI_FILE)

    def RunExecutable(self) -> None:
        subprocess.Popen([self.GetExecutablePath()], creationflags=DETACHED_PROCESS)

    def UninstallGame(self) -> None:
        subprocess.Popen([self.GetWgcapiPath(), '--uninstall'], creationflags=DETACHED_PROCESS, cwd = self.GetGameFolder())
