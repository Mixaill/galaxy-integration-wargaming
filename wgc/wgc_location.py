# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import os
from pathlib import Path
from typing import List


from .wgc_helper import scantree

class WGCLocation():
    
    WGC_PROGRAMDATA_DIR = 'Wargaming.net/GameCenter/'

    WGC_APPSLOCATION_DIR = 'apps/'
    WGC_PATH_FILE = 'data/wgc_path.dat'
    WGC_TRACKING_FILE = 'data/wgc_tracking_id.dat'

    WGC_PREFERENCES_FILE = 'preferences.xml'  
    WGC_EXECUTABLE_NAME = 'wgc.exe'
    WGC_GAMES_RESTRICTIONS = 'games_restrictions.xml'

    WGC_MACOS_PROGRAMDATA_DIR = os.path.join(Path.home(), 'Library/Application Support/Wargaming.net Game Center/Bottles/wargaminggamecenter64/drive_c/ProgramData/Wargaming.net/GameCenter/')
    WGC_MACOS_WGC_DIR         = os.path.join(Path.home(), 'Library/Application Support/Wargaming.net Game Center/Bottles/wargaminggamecenter64/drive_c/Program Files (x86)/Wargaming.net/GameCenter/')


    @staticmethod
    def get_wgc_programdata_dir() -> str:
        #Windows
        if os.getenv('PROGRAMDATA'):
            return os.path.join(os.getenv('PROGRAMDATA'), WGCLocation.WGC_PROGRAMDATA_DIR)

        #macOS
        if os.path.exists(WGCLocation.WGC_MACOS_PROGRAMDATA_DIR):
            return WGCLocation.WGC_MACOS_PROGRAMDATA_DIR

        logging.getLogger('WGC/Location').warn('get_wgc_programdata_dir: WGC ProgramData directory was not found')
        return ''

    @staticmethod
    def get_wgc_wgcpath_file() -> str:
        return os.path.join(WGCLocation.get_wgc_programdata_dir(), WGCLocation.WGC_PATH_FILE)

    @staticmethod
    def get_wgc_trackingid_file() -> str:
        return os.path.join(WGCLocation.get_wgc_programdata_dir(), WGCLocation.WGC_TRACKING_FILE)

    @staticmethod
    def get_wgc_apps_dir() -> str:
        return os.path.join(WGCLocation.get_wgc_programdata_dir(), WGCLocation.WGC_APPSLOCATION_DIR)

    @staticmethod
    def get_wgc_dir() -> str: 
        #try to use path from wgc_path.data
        wgc_path_file = WGCLocation.get_wgc_wgcpath_file()
        if os.path.exists(wgc_path_file):
            wgc_path = None
            with open(wgc_path_file, 'r') as file_content:
                wgc_path = file_content.read()
            if os.path.exists(os.path.join(wgc_path, WGCLocation.WGC_EXECUTABLE_NAME)):
                return wgc_path

        #fall back to program data
        wgc_programdata_dir = WGCLocation.get_wgc_programdata_dir()
        if os.path.exists(os.path.join(wgc_programdata_dir, WGCLocation.WGC_EXECUTABLE_NAME)):
            return wgc_programdata_dir

        #fall back to macos path
        if os.path.exists(WGCLocation.WGC_MACOS_WGC_DIR):
            return WGCLocation.WGC_MACOS_WGC_DIR

        return None       

    @staticmethod
    def get_wgc_exe_path() -> str:
        '''
        returns path to the wgc.exe file
        '''
        wgc_dir = WGCLocation.get_wgc_dir()
        if wgc_dir is None:
            return None

        return os.path.join(wgc_dir, WGCLocation.WGC_EXECUTABLE_NAME)
    
    @staticmethod
    def get_wgc_preferences_file() -> str:
        '''
        returns path to the preferences.xml file
        '''
        wgc_dir = WGCLocation.get_wgc_dir()
        if wgc_dir is None:
            return None

        preferences_path = os.path.join(wgc_dir, WGCLocation.WGC_PREFERENCES_FILE)
        if not os.path.exists(preferences_path):
            return None
        
        return preferences_path

    @staticmethod
    def get_wgc_gamerestrictions_file() -> str:
        '''
        returns path to the games_restrictions.xml file
        '''
        wgc_dir = WGCLocation.get_wgc_dir();
        if not wgc_dir:
            return ''

        gamerestrictions_path = os.path.join(wgc_dir, WGCLocation.WGC_GAMES_RESTRICTIONS)
        if not os.path.exists(gamerestrictions_path):
            return ''

        return gamerestrictions_path

    @staticmethod
    def get_apps_dirs() -> List[str]:
        apps = list()

        apploc_dir = WGCLocation.get_wgc_apps_dir()
        if not os.path.exists(apploc_dir):
            return apps

        app_files = [item.path for item in scantree(apploc_dir) if item.is_file() ]
        for app_file in app_files:
            app_path = None
            with open(app_file, 'r', encoding="utf-8") as file_content:
                app_path = file_content.read()
                apps.append(app_path)

        return apps

    @staticmethod
    def is_wgc_installed() -> bool:
        return WGCLocation.get_wgc_dir() != None
