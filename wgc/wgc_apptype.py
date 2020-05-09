# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import os
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom

from .wgc_error import MetadataNotFoundError

class WgcAppType():
    '''
    Game app_type.xml file
    '''

    @staticmethod 
    def create_file(filepath: str, app_type: str, switch_to_type: str):
        '''
        creates a new app_type.xml file
        '''

        protocol = ElementTree.Element('protocol', {'version': '3.0', 'name': 'app_type'})
        
        protocol_apptype = ElementTree.SubElement(protocol, 'app_type')
        protocol_apptype.text = app_type

        protocol_switchtype = ElementTree.SubElement(protocol, 'switch_to_type')
        protocol_switchtype.text = switch_to_type

        text = ElementTree.tostring(protocol, 'utf-8')
        with open(filepath, "w") as f:
            f.write(minidom.parseString(text).toprettyxml(indent="  "))


    def __init__(self, filepath: str):
        
        if not os.path.exists(filepath):
            raise MetadataNotFoundError("WgcAppType/__init__: %s does not exists" % filepath)
        
        self.__root = ElementTree.parse(filepath).getroot()


    def get_apptype(self) -> str:
        '''
        returns app_type.xml/protocol/app_type
        '''
        return self.__root.find('app_type').text


    def get_switchtype(self) -> str:
        '''
        returns app_type.xml/protocol/switch_to_type
        '''
        return self.__root.find('switch_to_type').text

