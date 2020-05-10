# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import os
from pathlib import Path
from typing import List

from .wgc_helper import scantree, get_platform

class WGCLocation():    
    MACOS_EXECUTABLE     = '/Applications/Wargaming.net Game Center.app/Contents/MacOS/Wargaming.net Game Center'
    WINE_DRIVE_C         = os.path.join(Path.home(), 'Library/Application Support/Wargaming.net Game Center/Bottles/wargaminggamecenter64/drive_c/')
    
    FALLBACK_DIR_PROGRAMDATA = 'C:/ProgramData/'
    FALLBACK_DIR_WGC         = 'C:/Program Files (x86)/Wargaming.net/GameCenter/'

    WGC_PROGRAMDATA = 'Wargaming.net/GameCenter/'
    WGC_PROGRAMDATA_APPS = 'apps/'
    WGC_PROGRAMDATA_WGCPATH = 'data/wgc_path.dat'
    WGC_PROGRAMDATA_WGCTRACKING = 'data/wgc_tracking_id.dat'

    WGC_WGCDIR_EXECUTABLE = 'wgc.exe'
    WGC_WGCDIR_GAMESRESTRICTIONS = 'games_restrictions.xml'
    WGC_WGCDIR_PREFERENCES = 'preferences.xml'  

    @staticmethod 
    def fixup_path(fspath: str) -> str:
        '''
        converts Wine path to macOS path
        '''
        if get_platform() == "macos":
            return fspath.replace('\\','/').replace('C:/', WGCLocation.WINE_DRIVE_C)

        return fspath

    @staticmethod 
    def fixdown_path(fspath: str) -> str:
        '''
        converts macOS path to Wine path
        '''
        if get_platform() == "macos":
            return fspath.replace('\\','/').replace(WGCLocation.WINE_DRIVE_C,'C:/')

        return fspath

    @staticmethod
    def get_wgc_programdata_dir() -> str:
        #get from env
        programdata = os.getenv('PROGRAMDATA')

        #fallback
        if not programdata:
            programdata = WGCLocation.fixup_path(WGCLocation.FALLBACK_DIR_PROGRAMDATA)

        #check %PROGRAMDATA%
        if not os.path.exists(programdata):
            logging.getLogger('wgc_location').error('get_wgc_programdata_dir: failed to find programdata (%s)' % programdata)
            return ''

        #check WGC directory
        programdata_wgc = os.path.join(programdata, WGCLocation.WGC_PROGRAMDATA)
        if not os.path.exists(programdata_wgc):
            logging.getLogger('wgc_location').warning('get_wgc_programdata_dir: failed to find wgc programdata directory (%s)' % programdata_wgc)
            return ''

        return programdata_wgc

    @staticmethod
    def get_wgc_wgcpath_file() -> str:
        return os.path.join(WGCLocation.get_wgc_programdata_dir(), WGCLocation.WGC_PROGRAMDATA_WGCPATH)

    @staticmethod
    def get_wgc_trackingid_file() -> str:
        return os.path.join(WGCLocation.get_wgc_programdata_dir(), WGCLocation.WGC_PROGRAMDATA_WGCTRACKING)

    @staticmethod
    def get_wgc_apps_dir() -> str:
        return os.path.join(WGCLocation.get_wgc_programdata_dir(), WGCLocation.WGC_PROGRAMDATA_APPS)

    @staticmethod
    def get_wgc_dir() -> str:
        wgc_dir = ''

        #try to use path from wgc_path.data
        WGC_PROGRAMDATA_WGCPATH = WGCLocation.get_wgc_wgcpath_file()
        if os.path.exists(WGC_PROGRAMDATA_WGCPATH):
            with open(WGC_PROGRAMDATA_WGCPATH, 'r') as file_content:
                wgc_dir = WGCLocation.fixup_path(file_content.read())

            if os.path.exists(os.path.join(wgc_dir, WGCLocation.WGC_WGCDIR_EXECUTABLE)):
                return wgc_dir

        #fall back to program data
        wgc_dir = WGCLocation.fixup_path(WGCLocation.get_wgc_programdata_dir())
        if os.path.exists(os.path.join(wgc_dir, WGCLocation.WGC_WGCDIR_EXECUTABLE)):
            return wgc_dir

        #fall back to program files
        wgc_dir = WGCLocation.fixup_path(WGCLocation.FALLBACK_DIR_WGC)
        if os.path.exists(os.path.join(wgc_dir, WGCLocation.WGC_WGCDIR_EXECUTABLE)):
            return wgc_dir

        logging.getLogger('wgc_location').warning('get_wgc_dir: failed to find wgc directory')
        return wgc_dir       

    @staticmethod
    def get_wgc_exe_path() -> str:
        '''
        returns path to the wgc executable
        '''
        result = os.path.join(WGCLocation.get_wgc_dir(), WGCLocation.WGC_WGCDIR_EXECUTABLE) 
        if not os.path.exists(result):
            logging.getLogger('wgc_location').warning('get_wgc_exe_path: failed to find wgc executable')
            return ''

        return result

    @staticmethod
    def get_wgc_exe_macos_path() -> str:
        '''
        returns path to the wgc macos launcher binary
        '''
        if get_platform() != 'macos':
            logging.getLogger('wgc_location').error('get_wgc_exe_macos_path: requires macOS')
            return ''
    
        return WGCLocation.MACOS_EXECUTABLE

    @staticmethod
    def get_wgc_preferences_file() -> str:
        '''
        returns path to the preferences.xml file
        '''
        
        result = os.path.join(WGCLocation.get_wgc_dir(), WGCLocation.WGC_WGCDIR_PREFERENCES)
        if not os.path.exists(result):
            logging.getLogger('wgc_location').warning('get_wgc_preferences_file: failed to find wgc preferences.xml')
            return ''
        
        return result

    @staticmethod
    def get_wgc_gamerestrictions_file() -> str:
        '''
        returns path to the games_restrictions.xml file
        '''

        result = os.path.join(WGCLocation.get_wgc_dir(), WGCLocation.WGC_WGCDIR_GAMESRESTRICTIONS)
        if not os.path.exists(result):
            logging.getLogger('wgc_location').info('get_wgc_gamerestrictions_file: failed to find wgc game_restrictions.xml')
            return ''

        return result

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
                apps.append(WGCLocation.fixup_path(app_path))

        return apps

    @staticmethod
    def is_wgc_installed() -> bool:
        return WGCLocation.get_wgc_dir()
