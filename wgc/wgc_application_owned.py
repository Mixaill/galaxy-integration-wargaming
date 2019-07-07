import logging
import subprocess
from typing import Dict

from .wgc_helper import DETACHED_PROCESS
from .wgc_location import WGCLocation

class WGCOwnedApplicationInstance(object):
    def __init__(self, app_data, instance_data):
        self._name = app_data['game_name']
        self._data = instance_data

    def get_application_id(self):
        return self._data['application_id']

    def get_application_fullname(self):
        return '%s (%s)' % (self._name, self._data['realm_id'])

    def get_application_install_url(self):
        return '%s@%s' % (self.get_application_id(), self.get_update_service_url())

    def get_update_service_url(self):
        return self._data['update_service_url']

    def install_application(self) -> bool:
        if not WGCLocation.is_wgc_installed():
            logging.warning('WGCOwnedApplicationInstance/install_application: failed to install %s because WGC is not installed' % self.get_application_id())
            return False

        subprocess.Popen([WGCLocation.get_wgc_exe_path(), '--install', '-g', self.get_application_install_url(), '--skipJobCheck'], creationflags=DETACHED_PROCESS)
        return True


class WGCOwnedApplication():

    def __init__(self, data):
        self._data = data

        self._instances = dict()
        for instance_json in self._data['instances']:
            instance_obj = WGCOwnedApplicationInstance(self._data, instance_json)
            self._instances[instance_obj.get_application_id()] = instance_obj

    def get_application_name(self) -> str:
        return self._data['game_name']

    def get_application_instances(self) -> Dict[str, WGCOwnedApplicationInstance]:
        return self._instances