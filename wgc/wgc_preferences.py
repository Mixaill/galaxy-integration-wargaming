# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import os
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom

from .wgc_constants import FALLBACK_COUNTRY, FALLBACK_LANGUAGE
from .wgc_error import MetadataNotFoundError\
    

class WgcPreferences:
    '''
    WGC preferences.xml file
    '''

    FALLBACK_DEFAULT_INSTALL_PATH = 'C:/Games/'

    def __init__(self, filepath: str):
        self.__logger = logging.getLogger('wgc_preferences')

        self.__filepath = filepath
        self.__root = None

        if os.path.exists(filepath):
            self.__root = ElementTree.parse(filepath).getroot()
        else:
            self.__logger.warning('__init__: %s is not exists' % filepath)


    def register_app_dir(self, app_dir) -> bool:
        if not self.__root:
            self.__logger.error('register_app_dir: failed to register app because %s does not exists' % self.__filepath)
            return False

        games = self.__root.find('application/games_manager/games')
        if games is None:
            self.__logger.error('register_app_dir: failed to games section')
            return False

        game = ElementTree.SubElement(games, 'game')

        workdir = ElementTree.SubElement(game, 'working_dir')
        workdir.text = app_dir

        return True

    def get_wgc_language(self) -> str:
        if not self.__root:
            return FALLBACK_LANGUAGE

        result = self.__root.find('application/localization_manager/current_localization').text
        if result is None or result == '':
            result = FALLBACK_LANGUAGE

        return result

    def get_country_code(self) -> str:
        if not self.__root:
            return FALLBACK_COUNTRY

        result = self.__root.find('application/user_location_country_code').text
        if result is None or result == '':
            result = FALLBACK_COUNTRY

        return result

    def get_default_install_path(self) -> str:
        if not self.__root:
            return self.FALLBACK_DEFAULT_INSTALL_PATH

        result = self.__root.find('application/games_manager/default_install_path')
        
        #fallback to C:\Games\
        if result is None:
            return self.FALLBACK_DEFAULT_INSTALL_PATH
        
        return result.text

    def set_active_game(self, path: str) -> bool:
        if not self.__root:
            self.__logger.error('set_active_game: failed to set active game because %s does not exists' % self.__filepath)
            return False

        gm = self.__root.find('application/games_manager')
        if not gm:
            self.__logger.error('set_active_game: failed to find game manager')

        #protocol/application/games_manager/active_game
        active_game = gm.find('active_game')
        if not active_game:
            active_game = ElementTree.SubElement(gm, 'active_game')
        active_game.text = path

        return True


    def set_current_game(self, path: str) -> bool:
        if not self.__root:
            self.__logger.error('set_current_game: failed to set current game because %s does not exists' % self.__filepath)
            return False

        gm = self.__root.find('application/games_manager')
        if not gm:
            self.__logger.error('set_current_game: failed to find game manager')

        #protocol/application/games_manager/current_game
        current_game = gm.find('current_game')
        if not current_game:
            current_game = ElementTree.SubElement(gm, 'current_game')
        current_game.text = path

        return True


    def save(self) -> bool:
        if not self.__root:
            self.__logger.error('save: failed to save preferences.xml because root is None')
            return False

        text = ElementTree.tostring(self.__root, 'utf-8')
        with open(self.__filepath, "w") as f:
            f.write(minidom.parseString(text).toprettyxml(indent="  "))

        return True
