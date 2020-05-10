# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import os
import subprocess
import xml.etree.ElementTree as ElementTree

from typing import Dict, List

from .wgc_constants import ADDITIONAL_EXECUTABLE_NAMES
from .wgc_error import MetadataNotFoundError
from .wgc_gameinfo import WgcGameInfo
from .wgc_helper import DETACHED_PROCESS, is_mutex_exists
from .wgc_metadata import WgcMetadata

class WGCLocalApplication():
    
    INFO_FILE = 'game_info.xml'
    METADATA_FILE = 'game_metadata/metadata.xml'
    WGCAPI_FILE = 'wgc_api.exe'

    def __init__(self, folder):
        self.__folder = folder

        self.__gameinfo = WgcGameInfo(os.path.join(self.__folder, self.INFO_FILE))
        self.__metadata = WgcMetadata(os.path.join(self.__folder, self.METADATA_FILE))

    def get_app_id(self) -> str:
        return self.__metadata.get_app_id()

    def GetGameId(self) -> str:
        instance_id = self.get_app_id()
        if instance_id is None:
            return None

        return instance_id.split('.')[0]


    def GetOsCompatibility(self) -> List[str]:
        executables = self.__metadata.get_executable_names()
        if executables is None:
            logging.warning('WGCLocalApplication/GetOsCompatibility: None object')

        return executables.keys()

    def IsInstalled(self) -> bool:
        return self.__gameinfo.is_installed()

    def GetGameFolder(self) -> str:
        return self.__folder

    def GetExecutablePath(self, platform) -> str:
        return os.path.join(self.GetGameFolder(), self.__metadata.get_executable_names()[platform])

    def GetExecutablePaths(self) -> List[str]:
        result = list()
        for _, executable_name in self.__metadata.get_executable_names().items():
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
