import os
import subprocess
from typing import Dict
import xml.etree.ElementTree as ElementTree

from .wgc_api import WGCApi
from .wgc_application import WGCApplication
from .wgc_location import WGCLocation

class WGC():
    def __init__(self):
        self._api = WGCApi(self.get_tracking_id(), self.get_country_code())
        pass

    #General
    def is_installed(self) -> bool:
        return WGCLocation.get_wgc_dir() != None


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

    # Tracking

    def get_country_code(self) -> str:
        wgc_preferences_file = WGCLocation.get_wgc_preferences_file()
        if os.path.exists(wgc_preferences_file):
            xml_file = ElementTree.parse(wgc_preferences_file).getroot()
            return xml_file.find('application/user_location_country_code').text

        return ''

    def get_tracking_id(self) -> str:
        tracking_id = ''

        wgc_tracking_file = WGCLocation.get_wgc_trackingid_file()
        if os.path.exists(wgc_tracking_file):
            with open(wgc_tracking_file, 'r') as file_content:
                tracking_id = file_content.read()

        return tracking_id

    def get_local_applications(self) -> Dict[str, WGCApplication]:
        apps = dict()
        for app_dir in WGCLocation.get_apps_dirs():
            app = WGCApplication(app_dir)
            apps[app.GetId()] = app

        return apps

    def get_owned_applications(self) -> Dict[str, WGCApplication]:
        #TODO: implement fetching owned application from WGCPS
        return self.get_local_applications()
