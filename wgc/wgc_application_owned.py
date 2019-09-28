import logging
import subprocess
from typing import Dict

from .wgc_helper import DETACHED_PROCESS, fixup_gamename
from .wgc_location import WGCLocation

class WGCOwnedApplicationInstance(object):
    def __init__(self, app_data, instance_data, is_purchased):
        self._name = app_data['game_name']
        self._data = instance_data
        self.__is_purchased = is_purchased

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

    def get_update_service_url(self):
        return self._data['update_service_url']

    def is_application_purchased(self) -> bool:
        return self.__is_purchased

    def install_application(self) -> bool:
        if not WGCLocation.is_wgc_installed():
            logging.warning('WGCOwnedApplicationInstance/install_application: failed to install %s because WGC is not installed' % self.get_application_id())
            return False

        subprocess.Popen([WGCLocation.get_wgc_exe_path(), '--install', '-g', self.get_application_install_url(), '--skipJobCheck'], creationflags=DETACHED_PROCESS)
        return True


class WGCOwnedApplication():

    def __init__(self, data, is_purchased):
        self.__data = data
        self.__is_purchased = is_purchased

        self._instances = dict()
        for instance_json in self.__data['instances']:
            instance_obj = WGCOwnedApplicationInstance(self.__data, instance_json, is_purchased)
            self._instances[instance_obj.get_application_id()] = instance_obj

    def is_application_purchased(self) -> bool:
        return self.__is_purchased

    def get_application_name(self) -> str:
        return fixup_gamename(self.__data['game_name'])

    def get_application_instances(self) -> Dict[str, WGCOwnedApplicationInstance]:
        return self._instances
