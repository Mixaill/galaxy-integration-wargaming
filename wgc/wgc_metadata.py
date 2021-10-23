# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import os
import xml.etree.ElementTree as ElementTree
from typing import Dict, List

from .wgc_error import MetadataNotFoundError, MetadataParseError
from .wgc_helper import fixup_gamename

class WgcMetadata:
    '''
    Game metadata.xml file
    '''

    def __init__(self, filepath: str):
        self.__logger = logging.getLogger('wgc_metadata')
        self.__filepath = filepath

        if not os.path.exists(self.__filepath):
            raise MetadataNotFoundError("WgcMetadata/__init__: %s does not exists" % self.__filepath)

        self.__root = None
        try:
            self.__root = ElementTree.parse(self.__filepath).getroot()
        except ElementTree.ParseError:
            raise MetadataParseError("WgcMetadata/__init__: %s failed to parse" % self.__filepath)        

    def get_app_id(self) -> str:
        '''
        returns app id from metadata
        '''

        # metadata v5
        result = self.__root.find('app_id')
        
        # metadata v6
        if result is None:
            result = self.__root.find('predefined_section/app_id')

        #unknown version
        if result is None:
            self.__logger.error('get_app_id: None object')
            return None

        return result.text

    def get_name(self) -> str:
        '''
        returns game name from metadata
        '''

        # metadata v5
        result = self.__root.find('shortcut_name')
        
        # metadata v6
        if result is None:
            result = self.__root.find('predefined_section/shortcut_name')

        #unknown version
        if result is None:
            self.__logger.error('get_name: None object')
            return None

        return fixup_gamename(result.text)

    def get_executable_names(self) -> Dict[str,str]:
        result = dict()

        # metadata v5
        node = self.__root.find('executable_name')
        if node is not None:
            result['windows'] = node.text
        
        #metadata v6
        node = self.__root.find('predefined_section/executables')
        if node is not None:
            for executable in node:
                platform = 'windows'
                if 'emul' in executable.attrib:
                    if executable.attrib['emul'] == 'wgc_mac':
                        platform = 'macos'

                result[platform] = executable.text

        #unknown version
        if not result:
            self.__logger.error('get_executable_names: failed to find executables')
            return None

        return result

    def get_mutex_names(self) -> List[str]:
        result = list()

        # metadata v5
        mtx_config = self.__root.find('mutex_name')
        
        # metadata v6
        if mtx_config is None:
            mtx_config = self.__root.find('predefined_section/mutex_name')

        if mtx_config is not None:
            result.append(mtx_config.text)

        #unknown version
        if not result:
            self.__logger.warning('get_mutex_names: no mutexes found for application %s' % self.get_app_id())

        return result

    def get_client_types(self) -> List[str]:
        # metadata v6
        client_types = self.__root.find('predefined_section/client_types')
        if client_types is not None:
            result = list()

            for client_type in client_types:
                result.append(client_type.attrib['id'])

            return result

        # metadata v5
        client_types = self.__root.find('metadata/client_type')
        if client_types is not None:
            result = list()
            result.append(client_types.attrib['id'])
            return result

        return None


    def get_default_client_type(self) -> str:
        # metadata v6
        client_types = self.__root.find('predefined_section/client_types')
        if client_types is not None:
            return client_types.attrib['default']

        # metadata v5
        client_types = self.__root.find('metadata/default_client_type')
        if client_types is not None:
            return client_types.text

        return None

    def get_parts_ids(self, client_type_id: str) -> List[str]:

        # metadata v6
        client_types = self.__root.find('predefined_section/client_types')
        if client_types is not None:
            result = list()

            for client_type in client_types:
                if client_type.attrib['id'] != client_type_id:
                    continue
                
                client_parts = client_type.find('client_parts')
                for client_part in client_parts:
                    result.append(client_part.attrib['id'])

            return result

        # metadata v5
        client_types = self.__root.find('metadata/client_type')
        if client_types is not None:
            result = list()

            if client_types.attrib['id'] != client_type_id:
                return None
            
            client_parts = client_types.find('client_parts')
            for client_part in client_parts:
                result.append(client_part.attrib['id'])

            return result

        return None


    def get_languages(self) -> List[str]:
        # metadata v6
        languages = self.__root.find('predefined_section/supported_languages')
        if languages is not None:
            return languages.text.split(',')

        # metadata v5
        languages = self.__root.find('supported_languages')
        if languages is not None:
            return languages.text.split(',')

        return None


    def get_default_language(self) -> str:
        # metadata v6
        language =  self.__root.find('predefined_section/default_language')
        if language is not None:
            return language.text

        # metadata v5
        language =  self.__root.find('default_language')
        if language is not None:
            return language.text

        return None
