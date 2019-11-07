import logging
import os
import subprocess
import xml.etree.ElementTree as ElementTree
from typing import Dict, List

from .wgc_helper import DETACHED_PROCESS, is_mutex_exists, fixup_gamename

class WGCLocalApplication():
    
    INFO_FILE = 'game_info.xml'
    METADATA_FILE = 'game_metadata\\metadata.xml'
    WGCAPI_FILE = 'wgc_api.exe'

    def __init__(self, folder):
        self.__folder = folder
        self.__gameinfo = None
        self.__metadata = None

        #game_info.xml
        gameinfo_file = os.path.join(self.__folder, self.INFO_FILE)
        if not os.path.exists(gameinfo_file):
            logging.error("WGCLocalApplication/__init__: %s does not exists" % gameinfo_file)
            raise AttributeError("WGCLocalApplication/__init__: %s does not exists" % gameinfo_file)
        self.__gameinfo = ElementTree.parse(gameinfo_file).getroot()

        #metadata.xml
        metadata_file = os.path.join(self.__folder, self.METADATA_FILE)
        if not os.path.exists(metadata_file):
            logging.error("WGCLocalApplication/__init__: %s does not exists" % metadata_file)
            raise AttributeError("WGCLocalApplication/__init__: %s does not exists" % metadata_file)    
        self.__metadata = ElementTree.parse(metadata_file).getroot()


    def GetId(self) -> str:
        # metadata v5
        result = self.__metadata.find('app_id')
        
        #metadata v6
        if result is None:
            result = self.__metadata.find('predefined_section/app_id')

        #unknown version
        if result is None:
            logging.error('WGCLocalApplication/GetId: None object')
            return None

        return result.text


    def GetName(self) -> str:
        # metadata v5
        result = self.__metadata.find('shortcut_name')
        
        #metadata v6
        if result is None:
            result = self.__metadata.find('predefined_section/shortcut_name')

        #unknown version
        if result is None:
            logging.error('WGCLocalApplication/GetName: None object')
            return None

        return fixup_gamename(result.text)


    def GetMutexName(self) -> str:
        # metadata v5
        result = self.__metadata.find('mutex_name')
        
        #metadata v6
        if result is None:
            result = self.__metadata.find('predefined_section/mutex_name')

        #unknown version
        if result is None:
            logging.error('WGCLocalApplication/GetMutexName: None object')
            return None

        return result.text


    def GetExecutableNames(self) -> Dict[str,str]:
        result = dict()

        # metadata v5
        node = self.__metadata.find('executable_name')
        if node is not None:
            result['windows'] = node.text
        
        #metadata v6
        node = self.__metadata.find('predefined_section/executables')
        if node is not None:
            for executable in node:
                platform = 'windows'
                if 'emul' in executable.attrib:
                    if executable.attrib['emul'] == 'wgc_mac':
                        platform = 'macos'

                result[platform] = executable.text

        #unknown version
        if not result:
            logging.error('WGCLocalApplication/GetExecutableName: failed to find executables')
            return None

        return result

    def GetOsCompatibility(self) -> List[str]:
        executables = self.GetExecutableNames()
        if executables is None:
            logging.warning('WGCLocalApplication/GetOsCompatibility: None object')

        return executables.keys()

    def IsInstalled(self) -> str:
        return bool(self.__gameinfo.find('game/installed').text)

    def GetGameFolder(self) -> str:
        return self.__folder

    def IsRunning(self) -> bool:
        return is_mutex_exists(self.GetMutexName())

    def GetExecutablePath(self, platform) -> str:
        return os.path.join(self.GetGameFolder(), self.GetExecutableNames()[platform])

    def GetWgcapiPath(self) -> str:
        return os.path.join(self.GetGameFolder(), self.WGCAPI_FILE)

    def RunExecutable(self, platform) -> None:
        subprocess.Popen([self.GetExecutablePath(platform)], creationflags=DETACHED_PROCESS)

    def UninstallGame(self) -> None:
        subprocess.Popen([self.GetWgcapiPath(), '--uninstall'], creationflags=DETACHED_PROCESS, cwd = self.GetGameFolder())
