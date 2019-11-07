import asyncio
import json
import logging
import os
import platform
import sys
from typing import Any, List, Optional

#expand sys.path
thirdparty =  os.path.join(os.path.dirname(os.path.realpath(__file__)),'3rdparty\\')
if thirdparty not in sys.path:
    sys.path.insert(0, thirdparty)

#read manifest
menifest = None
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json")) as manifest:
    manifest = json.load(manifest)

#disable urllib3 logging
import urllib3
logging.getLogger("urllib3").propagate = False

#Start sentry
import sentry_sdk
sentry_sdk.init(
    "https://b9055b733b99493bb3f4dd4855e0e990@sentry.friends-of-friends-of-galaxy.org/2",
    release=("galaxy-integration-wargaming@%s" % manifest['version']))

from galaxy.api.consts import OSCompatibility, Platform
from galaxy.api.errors import BackendError, InvalidCredentials
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Authentication, Game, LicenseInfo, LicenseType, LocalGame, LocalGameState, NextStep, FriendInfo
import webbrowser

from wgc import WGC, PAPIWoT, WgcXMPP

class WargamingPlugin(Plugin):

    SLEEP_CHECK_INSTANCES = 30


    def __init__(self, reader, writer, token):
        super().__init__(Platform(manifest['platform']), manifest['version'], reader, writer, token)

        self._wgc = WGC()
        self._xmpp = dict()

        self.__task_check_for_instances = None
        self.__local_games_states = dict()
        self.__local_applications = dict()

        self.__platform = 'unknown'
        if platform.system() == 'Windows':
            self.__platform = 'windows'
        elif platform.system() == 'Darwin':
            self.__platform = 'macos'
        else:
            logging.error('plugin/__init__: unknown platform %s' % platform)


    async def authenticate(self, stored_credentials=None):
        if not stored_credentials:
            logging.info('No stored credentials')

            AUTH_PARAMS = {
                "window_title": "Login to Wargaming",
                "window_width": 640,
                "window_height": 460,
                "start_uri": self._wgc.auth_server_uri(),
                "end_uri_regex": '.*finished'
            }
            if not self._wgc.auth_server_start():
                raise BackendError()

            return NextStep("web_session", AUTH_PARAMS)

        else:
            auth_passed = self._wgc.login_info_set(stored_credentials)
            if not auth_passed:
                logging.warning('Stored credentials are invalid')
                raise InvalidCredentials()
            
            return Authentication(self._wgc.account_id(), '%s_%s' % (self._wgc.account_realm(), self._wgc.account_nickname()))

    async def pass_login_credentials(self, step, credentials, cookies):
        self._wgc.auth_server_stop()

        login_info = self._wgc.login_info_get()
        if not login_info:
            logging.error('Login info is None!')
            raise InvalidCredentials()

        self.store_credentials(login_info)
        return Authentication(self._wgc.account_id(), '%s_%s' % (self._wgc.account_realm(), self._wgc.account_nickname()))

    async def get_local_games(self)-> List[LocalGame]:
        self.__rescan_games(False)

        result = list()
        for id, state in self.__local_games_states.items():
            result.append(LocalGame(id,state)) 

        return result

    async def get_owned_games(self):       
        owned_applications = list()

        for instance in self._wgc.get_owned_applications(self._wgc.account_realm()).values():
            license_info = LicenseInfo(LicenseType.SinglePurchase if instance.is_application_purchased() else LicenseType.FreeToPlay, None)
            owned_applications.append(Game(instance.get_application_id(), instance.get_application_fullname(), None, license_info))

        return owned_applications


    async def launch_game(self, game_id):
        self.__local_applications[game_id].RunExecutable(self.__platform)
        self.update_local_game_status(LocalGame(game_id, LocalGameState.Installed | LocalGameState.Running))


    async def install_game(self, game_id):
        if not self._wgc.is_wgc_installed():
            webbrowser.open(self._wgc.get_wgc_install_url())
            return

        instances = self._wgc.get_owned_applications(self._wgc.account_realm())
        if game_id not in instances:
            logging.warning('plugin/install_games: failed to find the application with id %s' % game_id)
            raise BackendError()
        
        instances[game_id].install_application()


    async def uninstall_game(self, game_id):
        self.__local_applications[game_id].UninstallGame()


    async def launch_platform_client(self):
        self._wgc.launch_client(True)


    async def get_friends(self):
        friends = list()
        xmpp_client = self.__xmpp_get_client('WOT')

        while len(xmpp_client.client_roster) == 0:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

        for jid in xmpp_client.client_roster:
            userid = jid.split('@', 1)[0]
            if userid != str(self._wgc.account_id()):
                username = '%s_%s' % (self._wgc.account_realm(), xmpp_client.client_roster[jid]['name'])
                friends.append(FriendInfo(userid, username))

        return friends


    def tick(self):
        if not self.__task_check_for_instances or self.__task_check_for_instances.done():
            self.__task_check_for_game_instances = self.create_task(self.task_check_for_instances(), "task_check_for_instances")


    async def task_check_for_instances(self):
        self.__rescan_games(True)
        await asyncio.sleep(self.SLEEP_CHECK_INSTANCES)


    def __rescan_games(self, notify = False):
        self.__local_applications = self._wgc.get_local_applications()

        #delete uninstalled games
        for id in self.__local_games_states:
            if id not in self.__local_applications:
                self.__local_games_states.pop(id)
                self.update_local_game_status(LocalGame(id, LocalGameState.None_))

        #change status of installed games
        for id, game in self.__local_applications.items():
            status_changed = False
            new_state = LocalGameState.Installed | LocalGameState.Running if game.IsRunning() else LocalGameState.Installed

            if id not in self.__local_games_states:
                status_changed = True
            elif new_state != self.__local_games_states[id]:
                status_changed = True
            self.__local_games_states[id] = new_state

            if notify and status_changed:
                self.update_local_game_status(LocalGame(id, new_state))


    #
    # XMPP
    #
   
    def __xmpp_get_client(self, client_type: str) -> WgcXMPP:
        if client_type not in self._xmpp:
            self._xmpp[client_type] = self._wgc.get_xmpp_client(client_type)
            self._xmpp[client_type].connect()

        return self._xmpp[client_type]

    #
    # ImportOSCompatibility
    #

    async def get_os_compatibility(self, game_id: str, context: Any) -> Optional[OSCompatibility]:
        if game_id not in self.__local_applications:
            logging.warning('plugin/get_os_compatibility: unknown game_id %s' % game_id)
            return None

        result = 0
        for platform in self.__local_applications[game_id].GetOsCompatibility():
            if platform == 'windows':
                result |= OSCompatibility.Windows
            elif platform == 'macos':
                result |= OSCompatibility.MacOS
            elif platform == 'linux':
                result |= OSCompatibility.Linux
            else:
                logging.error('plugin/get_os_compatibility: unknown platform %s' % platform)

        return result

def main():
    create_and_run_plugin(WargamingPlugin, sys.argv)


if __name__ == "__main__":
    main()
