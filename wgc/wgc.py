# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import os
import subprocess
from typing import Dict
import xml.etree.ElementTree as ElementTree

from .wgc_api import WgcApi
from .wgc_authserver import WgcAuthServer
from .wgc_application_local import WGCLocalApplication
from .wgc_application_owned import WGCOwnedApplication, WGCOwnedApplicationInstance
from .wgc_constants import FALLBACK_COUNTRY, FALLBACK_LANGUAGE, WGCInstallDocs
from .wgc_error import MetadataNotFoundError
from .wgc_gamerestrictions import WGCGameRestrictions
from .wgc_helper import DETACHED_PROCESS
from .wgc_http import WgcHttp
from .wgc_location import WGCLocation
from .wgc_preferences import WgcPreferences
from .wgc_wgni import WgcWgni
from .wgc_xmpp import WgcXMPP

class WGC():
    def __init__(self, config : Dict):
        self.__logger = logging.getLogger('wgc')    

        #parse config
        ssl_verify = True
        if 'ssl_verify' in config:
            ssl_verify = config['ssl_verify']

        self.__http = WgcHttp(ssl_verify)
        self.__wgni = WgcWgni(self.__http, self.get_tracking_id())
        self.__authserver = WgcAuthServer(self.__wgni)

        preferences = WgcPreferences(WGCLocation.get_wgc_preferences_file())
        self.__api = WgcApi(self.__http, self.__wgni, preferences.get_country_code(), preferences.get_wgc_language())


    async def shutdown(self):
        await self.__api.shutdown()
        await self.__authserver.shutdown()
        await self.__wgni.shutdown()
        await self.__http.shutdown()


    #HTTP Client
    def get_http_client(self) -> WgcHttp:
        return self.__http


    #WGNI Client
    def get_wgni_client(self) -> WgcWgni:
        return self.__wgni


    #Auth Server
    def get_auth_server(self) -> WgcAuthServer:
        return self.__authserver


    #API Client
    def get_api_client(self) -> WgcApi:
        return self.__api


    # Tracking
    def get_tracking_id(self) -> str:
        tracking_id = ''

        wgc_tracking_file = WGCLocation.get_wgc_trackingid_file()
        if os.path.exists(wgc_tracking_file):
            with open(wgc_tracking_file, 'r') as file_content:
                tracking_id = file_content.read()

        return tracking_id


    # Applications

    def get_local_applications(self) -> Dict[str, WGCLocalApplication]:
        apps = dict()

        for app_dir in WGCLocation.get_apps_dirs():
            #skip missing directories
            if not os.path.exists(app_dir):
                continue
            
            try:
                app = WGCLocalApplication(app_dir)
                apps[app.get_app_id()] = app
            except MetadataNotFoundError:
                self.__logger.warning('WGC/get_local_applications: Failed to found game metadata from folder %s. ' % app_dir)
            except PermissionError:
                self.__logger.warning('WGC/get_local_applications: Failed to get accces to the folder %s. ' % app_dir)
            except Exception:
                self.__logger.exception('WGC/get_local_applications: Failed to load game metadata from folder %s. ' % app_dir)

        return apps

    async def get_owned_applications(self, target_realm: str = None) -> Dict[str, WGCOwnedApplicationInstance]:
        applications_instances = dict()
        for application in await self.get_api_client().fetch_product_list():
            for key, application_instance in application.get_application_instances().items():

                #skip if realm is not match our target
                realm = application_instance.get_application_realm()
                if target_realm is not None:
                    if realm != 'WW' and realm != 'CT' and realm != target_realm:
                        continue
                
                applications_instances[key] = application_instance

        return applications_instances

    # WGC Client

    def is_wgc_installed(self) -> bool:
        return WGCLocation.is_wgc_installed()

    def get_wgc_install_url(self) -> str:
        return WGCInstallDocs[self.get_wgni_client().get_account_realm()]
 
    # Game Restrictions

    def get_game_restrictions(self) -> WGCGameRestrictions:
        game_restrictions_file = WGCLocation.get_wgc_gamerestrictions_file()

        if not game_restrictions_file:
            return None

        return WGCGameRestrictions(game_restrictions_file)

    # XMPP
    
    async def get_xmpp_client(self, game) -> WgcXMPP :

        realm = self.get_wgni_client().get_account_realm()
        if realm is None:
            self.__logger.error('wgc/get_xmpp_wot: failed to get realm')
            return None

        account_id = self.get_wgni_client().get_account_id()
        if account_id is None:
            self.__logger.error('wgc/get_xmpp_wot: failed to get account_id')
            return None

        token1 = await self.get_wgni_client().create_token1('xmppcs')
        if token1 is None:
            self.__logger.error('wgc/get_xmpp_wot: failed to get token1')
            return None

        return WgcXMPP(game, realm, account_id, token1)

