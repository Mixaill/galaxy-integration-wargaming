# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import asyncio
import json
import logging
import os
import pickle
import platform
import sys
from typing import Any, Dict, List, Optional

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
from galaxy.api.errors import BackendError, InvalidCredentials, UnknownError
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Authentication, Game, GameTime, LicenseInfo, LicenseType, LocalGame, LocalGameState, NextStep, UserInfo, UserPresence
import galaxy.proc_tools as proc_tools

import webbrowser

from galaxyutils.time_tracker import TimeTracker, GameNotTrackedException, GamesStillBeingTrackedException

from wgc import WGC, WGCLocalApplication, PAPIWoT, WgcXMPP, get_profile_url

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
      * ImportGameTime
      * ImportOSCompatibility
      * ImportUserPresence

    Missing features:
      * ImportAchievements
      * ShutdownPlatformClient
      * ImportGameLibrarySettings

    """

    SLEEP_CHECK_INSTANCES = 30


    def __init__(self, reader, writer, token):
        super().__init__(Platform(manifest['platform']), manifest['version'], reader, writer, token)

        self._wgc = WGC()
        self._xmpp = dict()

        #intialized flag
        self.__handshake_completed = False
        self.__localgames_imported = False

        #time tracker
        self.__gametime_tracker = None

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

    async def authenticate(self, stored_credentials = None):
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

        self.__localgames_imported = True
        return result

    #
    # LaunchGame
    #

    async def launch_game(self, game_id: str) -> None:
        self.__local_applications[game_id].RunExecutable(self.__platform)
        self.__change_game_status(game_id, LocalGameState.Installed | LocalGameState.Running, True)

    #
    # InstallGame
    #

    async def install_game(self, game_id: str) -> None:
        if not self._wgc.is_wgc_installed():
            webbrowser.open(self._wgc.get_wgc_install_url())
            return

        instances = await self._wgc.get_owned_applications(self._wgc.account_realm())
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
            avatar_url = None
            profile_url = get_profile_url(xmpp_client.get_game_id(), xmpp_client.get_realm(), user_id)
            friends.append(UserInfo(user_id, user_name, avatar_url, profile_url))

        logging.info('plugin/get_friends: %s' % friends)
        return friends

    #
    # ImportGameTime
    #

    async def get_game_time(self, game_id: str, context: Any) -> GameTime:
        try:
            return self.__gametime_tracker.get_tracked_time(game_id)
        except GameNotTrackedException:
            return GameTime(game_id, 0, 0)

    #
    # ImportOSCompatibility
    #

    async def get_os_compatibility(self, game_id: str, context: Any) -> Optional[OSCompatibility]:
        if game_id not in self.__local_applications:
            #TODO: find a way to get OS compat from owned application, not local
            #logging.warning('plugin/get_os_compatibility: unknown game_id %s' % game_id)
            return OSCompatibility.Windows

        result = None
        for platform in self.__local_applications[game_id].GetOsCompatibility():
            if platform == 'windows':
                result = OSCompatibility.Windows if result is None else result | OSCompatibility.Windows
            elif platform == 'macos':
                result = OSCompatibility.MacOS if result is None else result | OSCompatibility.MacOS
            elif platform == 'linux':
                result = OSCompatibility.Linux if result is None else result | OSCompatibility.Linux
            else:
                logging.error('plugin/get_os_compatibility: unknown platform %s' % platform)

        return result

    #
    # ImportUserPresence
    #

    async def prepare_user_presence_context(self, user_id_list: List[str]) -> Any:
        result = dict()

        xmpp_client = await self.__xmpp_get_client('WOT')

        for user_id in user_id_list:
            xmpp_state = await xmpp_client.get_presence(user_id)

            presence_state = PresenceState.Unknown
            game_id = None
            game_title = None
            status = None #TODO: support WoT Assistant

            if xmpp_state == 'online':
                presence_state = PresenceState.Online
                game_id = xmpp_client.get_game_full_id()
                game_title = xmpp_client.get_game_title()
            elif xmpp_state == 'offline':
                presence_state = PresenceState.Offline
            elif xmpp_state == 'unknown':
                presence_state = PresenceState.Unknown
            else:
                logging.error('plugin/prepare_user_presence_context: unknown presence state %s' % xmpp_state)

            result[user_id] = UserPresence(
                presence_state = presence_state,
                game_id = game_id,
                game_title = game_title,
                in_game_status = status)

        return result


    async def get_user_presence(self, user_id: str, context: Any) -> UserPresence:
        if user_id not in context:
            raise UnknownError('plugin/get_user_presence: failed to get info for user %s' % user_id)

        return context[user_id]

    #
    # Other
    #

    def handshake_complete(self) -> None:
        #time tracker initialization
        gametime_cache = self.__gametime_load_cache()
        self.__gametime_tracker = TimeTracker(game_time_cache=gametime_cache) if gametime_cache is not None else TimeTracker()

        self.__handshake_completed = True

    def tick(self):
        if self.__handshake_completed and self.__localgames_imported:
            if not self.__task_check_for_instances_obj or self.__task_check_for_instances_obj.done():
                self.__task_check_for_instances_obj = self.create_task(self.__task_check_for_instances(), "task_check_for_instances")

    async def shutdown(self) -> None:
        await self._wgc.shutdown()

        #xmpp
        for xmpp_client in self._xmpp.values():
            xmpp_client.disconnect()

        #time tracker
        self.__gametime_save_cache()

    #
    # Internals
    #

    async def __task_check_for_instances(self):
        self.__rescan_games(True)
        await asyncio.sleep(self.SLEEP_CHECK_INSTANCES)


    def __is_game_running(self, app: WGCLocalApplication) -> bool:
        for game_path in app.GetExecutablePaths():
            for pid in proc_tools.pids():
                proc_path = proc_tools.get_process_info(pid).binary_path
                if proc_path is None or proc_path == '':
                    continue
                if proc_path.lower().replace('\\','/') == game_path.lower().replace('\\','/'):
                    return True

        return False


    def __rescan_games(self, notify = False):
        self.__local_applications = self._wgc.get_local_applications()

        #delete uninstalled games
        for game_id in self.__local_games_states:
            if game_id not in self.__local_applications:
                self.__change_game_status(game_id, LocalGameState.None_, notify)

        #change status of installed games
        for game_id, game in self.__local_applications.items():    
            new_state = LocalGameState.Installed | LocalGameState.Running if self.__is_game_running(game) else LocalGameState.Installed

            status_changed = False
            if game_id not in self.__local_games_states or new_state != self.__local_games_states[game_id]:
                status_changed = True

            if status_changed:
                self.__change_game_status(game_id, new_state, notify)


    def __change_game_status(self, game_id: str, new_state: LocalGameState, notify: bool) -> None:
        self.__local_games_states[game_id] = new_state

        if notify:
            #notify gametime tracker
            if new_state == LocalGameState.Installed | LocalGameState.Running:
                self.__gametime_tracker.start_tracking_game(game_id)
            else:
                try:
                    self.__gametime_tracker.stop_tracking_game(game_id)
                except GameNotTrackedException:
                    pass

            #notify GLX client
            self.update_local_game_status(LocalGame(game_id, new_state))


    async def __xmpp_get_client(self, client_type: str) -> WgcXMPP:
        if client_type not in self._xmpp:
            self._xmpp[client_type] = await self._wgc.get_xmpp_client(client_type)
            self._xmpp[client_type].connect()

        return self._xmpp[client_type]


    def __gametime_load_cache(self) -> Any:
        gametime_cache = None
        if "gametime_cache" in self.persistent_cache:
            gametime_cache = pickle.loads(bytes.fromhex(self.persistent_cache["gametime_cache"]))

        return gametime_cache

    def __gametime_save_cache(self) -> None:
        gametime_cache = None
        if self.__gametime_tracker:     
            try:
                gametime_cache = self.__gametime_tracker.get_time_cache_hex()
            except GamesStillBeingTrackedException:
                pass
        else:
            logging.error('plugin/__gametime_save_cache: gametime tracker is not initialized')

        if gametime_cache:
            self.persistent_cache["gametime_cache"] = gametime_cache
            self.push_cache()


def main():
    create_and_run_plugin(WargamingPlugin, sys.argv)


if __name__ == "__main__":
    main()
