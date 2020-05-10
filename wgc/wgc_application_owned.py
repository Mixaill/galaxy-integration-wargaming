# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import codecs
import logging
import os
import random
import string
import subprocess
from typing import Dict


from .wgc_apptype import WgcAppType
from .wgc_gameinfo import WgcGameInfo
from .wgc_helper import DETACHED_PROCESS, fixup_gamename, get_platform
from .wgc_launcher import WgcLauncher
from .wgc_location import WGCLocation
from .wgc_metadata import WgcMetadata
from .wgc_preferences import WgcPreferences

class WGCOwnedApplicationInstance():
    def __init__(self, app_data, instance_data, is_purchased, api):
        self.__logger = logging.getLogger('wgc_application_owned_instance')

        self._name = app_data['game_name']
        self._data = instance_data
        self.__is_purchased = is_purchased
        self.__api = api

    def get_application_id(self):
        return self._data['application_id']

    def get_application_gameid(self):
        return self.get_application_id().split('.')[0]

    def get_application_realm(self):
        return self.get_application_id().split('.')[1]

    def get_application_name(self):
        return fixup_gamename(self._name)

    def get_application_fullname(self):
        if self.get_application_realm() == 'WW':
            return self.get_application_name()
        else:
            return '%s (%s)' % (self.get_application_name(), self.get_application_realm())

    def get_application_install_url(self):
        return '%s@%s' % (self.get_application_id(), self.get_update_service_url())

    async def get_metadata(self) -> str:
        '''
        downloads metadata
        '''
        return await self.__api.fetch_app_metadata(self.get_update_service_url(), self.get_application_id())

    def get_update_service_url(self):
        return self._data['update_service_url']

    def is_application_purchased(self) -> bool:
        return self.__is_purchased

    async def install_application(self) -> bool:
        if not WGCLocation.is_wgc_installed():
            self.__logger.warning('install_application: failed to install %s because WGC is not installed' % self.get_application_id())
            return False

        if get_platform() == 'macos':
            return await self.install_application_macos()
        elif get_platform() == 'windows':
            return WgcLauncher.launch_wgc_gameinstall(self.get_application_install_url())
        else:
            self.__logger.error('install_application: unsupported platform %s' % get_platform())
            return False

    async def install_application_macos(self) -> bool:
        preferences = WgcPreferences(WGCLocation.get_wgc_preferences_file())
        
        #create dirs
        dir_game = WGCLocation.fixup_path(os.path.join(preferences.get_default_install_path(), self.get_application_fullname().replace(' ', '_').replace('(','').replace(')','')))
        if os.path.exists(dir_game):
            dir_game = '%s_%s' % (dir_game.rstrip('\\/'), ''.join(random.choices(string.digits+'ABCDEF', k=8)))

        file_apptype = os.path.join(dir_game ,'app_type.xml')
        file_gameinfo = os.path.join(dir_game ,'game_info.xml')

        dir_metadata = os.path.join(dir_game, 'game_metadata/')
        file_metadata = os.path.join(dir_metadata,'metadata.xml')
        os.makedirs(dir_metadata, exist_ok=True)

        #game_metadata/metadata.xml
        with codecs.open(file_metadata, 'w', 'utf-8') as f:
            f.write(await self.get_metadata())
        metadata = WgcMetadata(file_metadata)
    
        #root/app_type.xml
        WgcAppType.create_file(file_apptype, metadata.get_default_client_type(), metadata.get_default_client_type())
        apptype = WgcAppType(file_apptype)

        #root/game_metadata.xml
        language_to_install = metadata.get_default_language()
        if preferences.get_wgc_language().upper in metadata.get_languages():
            language_to_install = preferences.get_wgc_language().upper()
        
        WgcGameInfo.create_file(file_gameinfo, self, metadata, apptype, language_to_install)

        #register game directory
        preferences.register_app_dir(WGCLocation.fixdown_path(dir_game))
        preferences.set_active_game(WGCLocation.fixdown_path(dir_game))
        preferences.set_current_game(WGCLocation.fixdown_path(dir_game))
        preferences.save()

        #run WGC
        WgcLauncher.launch_wgc()


class WGCOwnedApplication():

    def __init__(self, data, is_purchased, api):
        self.__data = data
        self.__is_purchased = is_purchased
        self.__api = api

        self._instances = dict()
        for instance_json in self.__data['instances']:
            instance_obj = WGCOwnedApplicationInstance(self.__data, instance_json, is_purchased, self.__api)
            self._instances[instance_obj.get_application_id()] = instance_obj

    def is_application_purchased(self) -> bool:
        return self.__is_purchased

    def get_application_name(self) -> str:
        return fixup_gamename(self.__data['game_name'])

    def get_application_instances(self) -> Dict[str, WGCOwnedApplicationInstance]:
        return self._instances
