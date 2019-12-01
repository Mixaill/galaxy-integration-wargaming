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

from galaxy.api.consts import OSCompatibility, Platform, PresenceState
from galaxy.api.errors import BackendError, InvalidCredentials
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Authentication, Game, LicenseInfo, LicenseType, LocalGame, LocalGameState, NextStep, UserInfo, UserPresence
import webbrowser

from wgc import WGC, PAPIWoT, WgcXMPP

class WargamingPlugin(Plugin):
    """
    Wargaming Plugin for GOG Galaxy

    Implemented features:
      * ImportOwnedGames
      * ImportInstalledGames
      * LaunchGame
      * InstallGame
      * UninstallGame
      * LaunchPlatformClient
      * ImportFriends
      * ImportOSCompatibility
      * ImportUserPresence

    Missing features:
      * ImportAchievements
      * ShutdownPlatformClient
      * ImportGameTime
      * ImportGameLibrarySettings

    """

    SLEEP_CHECK_INSTANCES = 30


    def __init__(self, reader, writer, token):
        super().__init__(Platform(manifest['platform']), manifest['version'], reader, writer, token)

        self._wgc = WGC()
        self._xmpp = dict()

        self.__task_check_for_instances_obj = None
        self.__local_games_states = dict()
        self.__local_applications = dict()

        self.__platform = 'unknown'
        if platform.system() == 'Windows':
            self.__platform = 'windows'
        elif platform.system() == 'Darwin':
            self.__platform = 'macos'
        else:
            logging.error('plugin/__init__: unknown platform %s' % platform)

    #
    # Authentication
    #

    async def authenticate(self, stored_credentials=None):
        if not stored_credentials:
            logging.info('plugin/authenticate: no stored credentials')

            AUTH_PARAMS = {
                "window_title": "Login to Wargaming",
                "window_width": 640,
                "window_height": 460,
                "start_uri": self._wgc.auth_server_uri(),
                "end_uri_regex": '.*finished'
            }
            if not await self._wgc.auth_server_start():
                raise BackendError()

            return NextStep("web_session", AUTH_PARAMS)

        else:
            auth_passed = await self._wgc.login_info_set(stored_credentials)
            if not auth_passed:
                logging.warning('plugin/authenticate: stored credentials are invalid')
                raise InvalidCredentials()
            
            return Authentication(self._wgc.account_id(), '%s_%s' % (self._wgc.account_realm(), self._wgc.account_nickname()))

    async def pass_login_credentials(self, step, credentials, cookies):
        await self._wgc.auth_server_stop()

        login_info = self._wgc.login_info_get()
        if not login_info:
            logging.error('plugin/authenticate: login info is None!')
            raise InvalidCredentials()

        self.store_credentials(login_info)
        return Authentication(self._wgc.account_id(), '%s_%s' % (self._wgc.account_realm(), self._wgc.account_nickname()))

    #
    # ImportOwnedGames
    #

    async def get_owned_games(self) -> List[Game]:     
        owned_applications = list()

        for instance in (await self._wgc.get_owned_applications(self._wgc.account_realm())).values():
            license_info = LicenseInfo(LicenseType.SinglePurchase if instance.is_application_purchased() else LicenseType.FreeToPlay, None)
            owned_applications.append(Game(instance.get_application_id(), instance.get_application_fullname(), None, license_info))

        return owned_applications

    #
    # ImportInstalledGames
    #

    async def get_local_games(self) -> List[LocalGame]:
        self.__rescan_games(False)

        result = list()
        for id, state in self.__local_games_states.items():
            result.append(LocalGame(id,state)) 

        return result

    #
    # LaunchGame
    #

    async def launch_game(self, game_id: str) -> None:
        self.__local_applications[game_id].RunExecutable(self.__platform)
        self.__change_game_status(game_id, LocalGameState.Installed | LocalGameState.Running)

    #
    # InstallGame
    #

    async def install_game(self, game_id: str) -> None:
        if not self._wgc.is_wgc_installed():
            webbrowser.open(self._wgc.get_wgc_install_url())
            return

        instances = self._wgc.get_owned_applications(self._wgc.account_realm())
        if game_id not in instances:
            logging.warning('plugin/install_games: failed to find the application with id %s' % game_id)
            raise BackendError()
        
        instances[game_id].install_application()

    #
    # UninstallGame
    #

    async def uninstall_game(self, game_id: str) -> None:
        self.__local_applications[game_id].UninstallGame()

    #
    # LaunchPlatformClient
    #

    async def launch_platform_client(self) -> None:
        self._wgc.launch_client(True)

    #
    # ImportFriends
    #

    async def get_friends(self) -> List[UserInfo]:
        xmpp_client = await self.__xmpp_get_client('WOT')

        friends = list()
        for user_id, user_name in (await xmpp_client.get_friends()).items():
            #TODO: avatar
            #TODO: profile URL
            friends.append(UserInfo(user_id, user_name, None, None))

        return friends

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

    #
    # ImportUserPresence
    #

    async def get_user_presence(self, user_id: str, context: Any) -> UserPresence:
        xmpp_client = await self.__xmpp_get_client('WOT')
        xmpp_state = await xmpp_client.get_presence(user_id)

        presence_state = PresenceState.Unknown
        if xmpp_state == 'online':
            presence_state = PresenceState.Online
        elif xmpp_state == 'offline':
            presence_state = PresenceState.Offline
        elif xmpp_state == 'unknown':
            presence_state = PresenceState.Unknown
        else:
            logging.error('plugin/get_user_presence: unknown presence state %s' % xmpp_state)

        #TODO: game id
        #TODO: game title
        #TODO: in_game_status
        #TODO: full status
        return UserPresence(presence_state, None, None, None, None)

    #
    # Other
    #

    def tick(self):
        if not self.__task_check_for_instances_obj or self.__task_check_for_instances_obj.done():
            self.__task_check_for_instances_obj = self.create_task(self.__task_check_for_instances(), "task_check_for_instances")

    async def shutdown(self) -> None:
        await self._wgc.shutdown()

    #
    # Internals
    #

    async def __task_check_for_instances(self):
        self.__rescan_games(True)
        await asyncio.sleep(self.SLEEP_CHECK_INSTANCES)

    def __rescan_games(self, notify = False):
        self.__local_applications = self._wgc.get_local_applications()

        #delete uninstalled games
        for game_id in self.__local_games_states:
            if game_id not in self.__local_applications:
                self.__change_game_status(game_id, LocalGameState.None_)

        #change status of installed games
        for game_id, game in self.__local_applications.items():    
            new_state = LocalGameState.Installed | LocalGameState.Running if game.IsRunning() else LocalGameState.Installed
            
            status_changed = True
            if game_id in self.__local_games_states and new_state == self.__local_games_states[game_id]:
                status_changed = False

            if notify and status_changed:
                self.__change_game_status(game_id, new_state)


    def __change_game_status(self, game_id: str, new_state: LocalGameState) -> None:
        self.__local_games_states[game_id] = new_state
        self.update_local_game_status(LocalGame(game_id, new_state))


    async def __xmpp_get_client(self, client_type: str) -> WgcXMPP:
        if client_type not in self._xmpp:
            self._xmpp[client_type] = await self._wgc.get_xmpp_client(client_type)
            self._xmpp[client_type].connect()

        return self._xmpp[client_type]


def main():
    create_and_run_plugin(WargamingPlugin, sys.argv)


if __name__ == "__main__":
    main()
