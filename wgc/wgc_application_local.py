# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import asyncio
import logging
import os
import subprocess
import xml.etree.ElementTree as ElementTree
from typing import Dict, List

import psutil

from .wgc_constants import ADDITIONAL_EXECUTABLE_NAMES
from .wgc_error import MetadataNotFoundError
from .wgc_gameinfo import WgcGameInfo
from .wgc_helper import DETACHED_PROCESS, file_copy
from .wgc_launcher import WgcLauncher
from .wgc_location import WGCLocation
from .wgc_metadata import WgcMetadata

class WGCLocalApplication():
    
    INFO_FILE = 'game_info.xml'
    METADATA_FILE = 'game_metadata/metadata.xml'
    WGCAPI_FILE = 'wgc_api.exe'

    def __init__(self, folder):
        self.__logger = logging.getLogger('wgc_application_local')
        self.__folder = folder

        self.__gameinfo = WgcGameInfo(os.path.join(self.__folder, self.INFO_FILE))
        self.__metadata = WgcMetadata(os.path.join(self.__folder, self.METADATA_FILE))

    def get_app_id(self) -> str:
        return self.__metadata.get_app_id()

    async def get_app_size(self) -> int:
        total_size = 0
        try:
            for dirpath, _, filenames in os.walk(self.__folder):
                for f in filenames:
                    await asyncio.sleep(0)
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except Exception:
            self.__logger.exception('get_app_size:')

        return total_size

    def GetGameId(self) -> str:
        instance_id = self.get_app_id()
        if instance_id is None:
            return None

        return instance_id.split('.')[0]


    def GetOsCompatibility(self) -> List[str]:
        executables = self.__metadata.get_executable_names()
        if executables is None:
            self.__logger.warning('GetOsCompatibility: None object')

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

    def get_application_wgcapi_path(self) -> str:
        '''
        returns path to the application's instance of wgc_api.exe
        '''
        return os.path.join(self.GetGameFolder(), self.WGCAPI_FILE)

    def is_running(self) -> bool:
        '''
        check if current local application is running
        '''
        app_pathes = list()
        proc_pathes = list()
        cmdline_pathes = list()

        #populate app pathes
        for app_path in self.GetExecutablePaths():
            if app_path is None or app_path == '':
                continue
            app_pathes.append(app_path.lower().replace('\\','/'))

        #populate proc pathes
        for proc in psutil.process_iter(['exe', 'cmdline']):
            proc_exe = proc.info['exe']
            proc_cmdline = proc.info['cmdline']

            #process exe
            if not proc_exe:
                continue
            proc_pathes.append(proc_exe.lower().replace('\\','/'))

            #process cmdline
            if proc_cmdline and len(proc_cmdline) > 1 and proc_cmdline[0] == 'winewrapper.exe':
                cmdline_pathes.extend([i.lower().replace('\\','/') for i in proc_cmdline])

        #check pathes
        for app_path in app_pathes:
            if app_path in proc_pathes:
                return True
            if app_path in cmdline_pathes:
                return True

        return False

    def run_application(self, platform) -> bool:
        return WgcLauncher.launch_app(self.GetExecutablePath(platform))

    def uninstall_application(self) -> bool:
        #update wgcapi
        file_copy(WGCLocation.get_wgc_wgcapi_path(), self.get_application_wgcapi_path())

        return WgcLauncher.launch_app(self.get_application_wgcapi_path(), ['--uninstall'])
