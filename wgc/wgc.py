import logging
import os
import subprocess
from typing import Dict
import xml.etree.ElementTree as ElementTree

from .wgc_api import WGCApi
from .wgc_application_local import WGCLocalApplication
from .wgc_application_owned import WGCOwnedApplication, WGCOwnedApplicationInstance
from .wgc_location import WGCLocation
from .wgc_xmpp import WgcXMPP

class WGC():
    def __init__(self):
        self._api = WGCApi(self.get_tracking_id(), self.get_country_code(), self.get_wgc_language())
        pass


    #Auth Server
    def auth_server_uri(self) -> str:
        return self._api.auth_server_uri()

    def auth_server_start(self) -> bool:
        return self._api.auth_server_start()

    def auth_server_stop(self) -> bool:
        return self._api.auth_server_stop()


    #Login info
    def login_info_get(self) -> Dict[str,str]:
        return self._api.login_info_get()

    def login_info_set(self, login_info: Dict[str,str]) -> bool:
        return self._api.login_info_set(login_info)


    #Account details
    def account_id(self) -> int:
        return self._api.get_account_id()

    def account_email(self) -> str:
        return self._api.get_account_email()

    def account_nickname(self) -> str:
        return self._api.get_account_nickname()

    def account_realm(self) -> str:
        return self._api.get_account_realm()

    # Settings

    def __get_preferences_value(self, node_name: str) -> str:
        wgc_preferences_file = WGCLocation.get_wgc_preferences_file()
        if wgc_preferences_file is not None:
            xml_file = ElementTree.parse(wgc_preferences_file).getroot()
            return xml_file.find(node_name).text

        return ''

    def get_wgc_language(self) -> str:
        return self.__get_preferences_value('application/localization_manager/current_localization')

    def get_country_code(self) -> str:
        return self.__get_preferences_value('application/user_location_country_code')


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
            app = WGCLocalApplication(app_dir)
            apps[app.GetId()] = app

        return apps

    def get_owned_applications(self) -> Dict[str, WGCOwnedApplicationInstance]:
        applications_instances = dict()
        for application in self._api.fetch_product_list():
            applications_instances.update(application.get_application_instances())

        return applications_instances

    # XMPP
    
    def get_xmpp_client(self, game) -> WgcXMPP :

        realm = self._api.get_account_realm()
        if realm is None:
            logging.error('wgc/get_xmpp_wot: failed to get realm')
            return None

        account_id = self._api.get_account_id()
        if account_id is None:
            logging.error('wgc/get_xmpp_wot: failed to get account_id')
            return None

        token1 = self._api.create_token1('xmppcs')
        if token1 is None:
            logging.error('wgc/get_xmpp_wot: failed to get token1')

        return WgcXMPP(game, realm, account_id, token1)

