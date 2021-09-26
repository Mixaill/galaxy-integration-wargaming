# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import os
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
from typing import List

from .wgc_apptype import WgcAppType
from .wgc_error import MetadataNotFoundError, MetadataParseError
from .wgc_metadata import WgcMetadata

class WgcGameInfo:
    '''
    Game game_info.xml file
    '''

    @staticmethod 
    def create_file(filepath: str, app_instance, metadata: WgcMetadata, apptype: WgcAppType, localization: str):
        '''
        creates a new game_info.xml file
        '''
        
        protocol = ElementTree.Element('protocol', {'version': '2.9', 'wgc_publisher_id': 'wargaming', 'name': 'game_info'})
        protocol_game = ElementTree.SubElement(protocol, 'game')
        
        #protocol/game/id
        protocol_game_id = ElementTree.SubElement(protocol_game, 'id')
        protocol_game_id.text = metadata.get_app_id()
        
        #protocol/game/index
        protocol_game_idx = ElementTree.SubElement(protocol_game, 'index')
        protocol_game_idx.text = '0'
        
        #protocol/game/installed
        protocol_game_installed = ElementTree.SubElement(protocol_game, 'installed')
        protocol_game_installed.text = 'false'

        #protocol/game/all_parts_installed
        protocol_game_allpartsinstalled = ElementTree.SubElement(protocol_game, 'all_parts_installed')
        protocol_game_allpartsinstalled.text = 'false'

        #protocol/game/localization
        protocol_game_localization = ElementTree.SubElement(protocol_game, 'localization')
        protocol_game_localization.text = localization

        #protocol/game/content_localization
        protocol_game_contentlocalization = ElementTree.SubElement(protocol_game, 'content_localization')
        protocol_game_contentlocalization.text = localization

        #protocol/game/client_type
        protocol_game_clienttype = ElementTree.SubElement(protocol_game, 'client_type')
        protocol_game_clienttype.text = apptype.get_apptype()

        #protocol/game/show_guide
        protocol_game_showguide = ElementTree.SubElement(protocol_game, 'show_guide')
        protocol_game_showguide.text = 'true'

        #protocol/game/update_urls
        protocol_game_updateurls = ElementTree.SubElement(protocol_game, 'update_urls')
        protocol_game_updateurls_val = ElementTree.SubElement(protocol_game_updateurls, 'value')
        protocol_game_updateurls_val.text = app_instance.get_update_service_url()

        #protocol/game/corrupt_parts
        ElementTree.SubElement(protocol_game, 'corrupt_parts')

        #protocol/game/parts_versions
        protocol_game_partsversions = ElementTree.SubElement(protocol_game, 'part_versions')
        for part_id in metadata.get_parts_ids(apptype.get_apptype()):
            ElementTree.SubElement(protocol_game_partsversions, 'version', {'name': part_id, 'available': '', 'installed': '0'})

        #protocol/game/parameters
        protocol_game_parameters = ElementTree.SubElement(protocol_game, 'parameters')
        protocol_game_parameters_desktop = ElementTree.SubElement(protocol_game_parameters, 'value', {'name': 'create_desktop_shortcut'})
        protocol_game_parameters_desktop.text = 'true'
        protocol_game_parameters_menu = ElementTree.SubElement(protocol_game_parameters, 'value', {'name': 'create_start_menu_shortcut'})
        protocol_game_parameters_menu.text = 'true'
    
        #protocol/game/dlc
        ElementTree.SubElement(protocol_game, 'dlc')

        text = ElementTree.tostring(protocol, 'utf-8')
        with open(filepath, "w") as f:
            f.write(minidom.parseString(text).toprettyxml(indent="  "))


    def __init__(self, filepath: str):
        self.__filepath = filepath

        if not os.path.exists(self.__filepath):
            raise MetadataNotFoundError("WgcGameInfo/__init__: %s does not exists" % self.__filepath)

        self.__root = None
        try:
            self.__root = ElementTree.parse(self.__filepath).getroot()
        except ElementTree.ParseError:
            raise MetadataParseError("WgcGameInfo/__init__: %s failed to parse" % self.__filepath)        


    def is_installed(self) -> bool:
        '''
        checks if game is installed according to game_info.xml
        '''
        return self.__root.find('game/installed').text == 'true'

