import logging
import os
import subprocess
import xml.etree.ElementTree as ElementTree
# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

from typing import Dict, List

from .wgc_constants import ADDITIONAL_EXECUTABLE_NAMES
from .wgc_error import MetadataNotFoundError
from .wgc_helper import DETACHED_PROCESS, is_mutex_exists, fixup_gamename

class WGCLocalApplication():
    
    INFO_FILE = 'game_info.xml'
    METADATA_FILE = 'game_metadata\\metadata.xml'
    WGCAPI_FILE = 'wgc_api.exe'

    def __init__(self, folder):
        self.__folder = folder
        self.__gameinfo = None
        self.__metadata = None

        gameinfo_file = os.path.join(self.__folder, self.INFO_FILE)
        metadata_file = os.path.join(self.__folder, self.METADATA_FILE)

        if not os.path.exists(gameinfo_file):
            raise MetadataNotFoundError("WGCLocalApplication/__init__: %s does not exists" % gameinfo_file)
        if not os.path.exists(metadata_file):
            raise MetadataNotFoundError("WGCLocalApplication/__init__: %s does not exists" % metadata_file)  

        self.__gameinfo = ElementTree.parse(gameinfo_file).getroot()
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


    def GetGameId(self) -> str:
        instance_id = self.GetId()
        if instance_id is None:
            return None

        return instance_id.split('.')[0]


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


    def GetMutexNames(self) -> List[str]:
        result = list()

        # metadata v5
        mtx_config = self.__metadata.find('mutex_name')
        
        #metadata v6
        if mtx_config is None:
            mtx_config = self.__metadata.find('predefined_section/mutex_name')

        if mtx_config is not None:
            result.append(mtx_config.text)

        #unknown version
        if not result:
            logging.warning('WGCLocalApplication/GetMutexName: no mutexes found for application %s' % self.GetId())

        return result


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

    def IsInstalled(self) -> bool:
        return self.__gameinfo.find('game/installed').text == 'true'

    def GetGameFolder(self) -> str:
        return self.__folder

    def GetExecutablePath(self, platform) -> str:
        return os.path.join(self.GetGameFolder(), self.GetExecutableNames()[platform])

    def GetExecutablePaths(self) -> List[str]:
        result = list()
        for _, executable_name in self.GetExecutableNames().items():
            result.append(os.path.join(self.GetGameFolder(), executable_name))

        if self.GetGameId() in ADDITIONAL_EXECUTABLE_NAMES:
            for exe_name in ADDITIONAL_EXECUTABLE_NAMES[self.GetGameId()]:
                result.append(os.path.join(self.GetGameFolder(), exe_name))

        return result

    def GetWgcapiPath(self) -> str:
        return os.path.join(self.GetGameFolder(), self.WGCAPI_FILE)

    def RunExecutable(self, platform) -> None:
        subprocess.Popen([self.GetExecutablePath(platform)], creationflags=DETACHED_PROCESS)

    def UninstallGame(self) -> None:
        subprocess.Popen([self.GetWgcapiPath(), '--uninstall'], creationflags=DETACHED_PROCESS, cwd = self.GetGameFolder())
