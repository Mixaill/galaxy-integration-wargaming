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

    def __init__(self, filepath: str):
        self.__logger = logging.getLogger('wgc_preferences')

        if not os.path.exists(filepath):
            raise MetadataNotFoundError("WgcPreferences/__init__: %s does not exists" % filepath)
        
        self.__filepath = filepath
        self.__root = ElementTree.parse(filepath).getroot()


    def register_app_dir(self, app_dir) -> bool:
        games = self.__root.find('application/games_manager/games')
        if games is None:
            return False

        game = ElementTree.SubElement(games, 'game')

        workdir = ElementTree.SubElement(game, 'working_dir')
        workdir.text = app_dir

        self.save()
        return True

    def get_wgc_language(self) -> str:
        result = self.__root.find('application/localization_manager/current_localization').text
        if result is None or result == '':
            result = FALLBACK_LANGUAGE

        return result

    def get_country_code(self) -> str:
        result = self.__root.find('application/user_location_country_code').text
        if result is None or result == '':
            result = FALLBACK_COUNTRY

        return result


    def get_default_install_path(self) -> str:
        return self.__root.find('application/games_manager/default_install_path').text


    def save(self) -> str:
        text = ElementTree.tostring(self.__root, 'utf-8')
        with open(self.__filepath, "w") as f:
            f.write(minidom.parseString(text).toprettyxml(indent="  "))
