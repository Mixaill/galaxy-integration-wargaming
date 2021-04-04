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

#platform helper
def get_platform() -> str:
    system = platform.system()
    if system == 'Windows':
        return 'windows'

    if system == 'Darwin':
        return 'macos'

    logging.error('plugin/get_platform: unknown platform %s' % system)
    return 'unknown'


#expand sys.path
thirdparty =  os.path.join(os.path.dirname(os.path.realpath(__file__)),'3rdparty_%s/' % get_platform())
if thirdparty not in sys.path and os.path.exists(thirdparty):
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
    "https://35009a54bd184d25b227e2f26ae96dd7@sentry.friends-of-friends-of-galaxy.org/2",
    release=("galaxy-integration-wargaming@%s" % manifest['version']))

from galaxy.api.consts import OSCompatibility, Platform, PresenceState
from galaxy.api.errors import BackendError, InvalidCredentials, UnknownError
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Authentication, Game, GameTime, LicenseInfo, LicenseType, LocalGame, LocalGameState, NextStep, UserInfo, UserPresence

import webbrowser

from galaxyutils.time_tracker import TimeTracker, GameNotTrackedException, GamesStillBeingTrackedException

from wgc import WGC, WgcLauncher, WGCLocalApplication, PAPIWoT, WgcXMPP, get_profile_url

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
      * ImportLocalSize

    Missing features:
      * ImportAchievements
      * ShutdownPlatformClient
      * ImportGameLibrarySettings
      * ImportSubscriptions
      * ImportSubscriptionGames
    """

    SLEEP_CHECK_INSTANCES = 30


    def __init__(self, reader, writer, token):
        super().__init__(Platform(manifest['platform']), manifest['version'], reader, writer, token)

        self._logger = logging.getLogger('wgc_plugin')
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

        self.__platform = get_platform()

    #
    # Authentication
    #

    async def authenticate(self, stored_credentials = None):
        authserver = self._wgc.get_auth_server()
        wgni = self._wgc.get_wgni_client()

        if not stored_credentials:
            self._logger.info('plugin/authenticate: no stored credentials')

            AUTH_PARAMS = {
                "window_title": "Login to Wargaming",
                "window_width": 640,
                "window_height": 460,
                "start_uri": authserver.get_uri(),
                "end_uri_regex": '.*finished'
            }
            if not await authserver.start():
                raise BackendError()

            return NextStep("web_session", AUTH_PARAMS)

        else:
            auth_passed = await wgni.login_info_set(stored_credentials)
            if not auth_passed:
                self._logger.warning('plugin/authenticate: stored credentials are invalid')
                raise InvalidCredentials()
            
            return Authentication(wgni.get_account_id(), '%s_%s' % (wgni.get_account_realm(), wgni.get_account_nickname()))


    async def pass_login_credentials(self, step, credentials, cookies):
        authserver = self._wgc.get_auth_server()
        wgni = self._wgc.get_wgni_client()

        await authserver.shutdown()

        login_info = wgni.login_info_get()
        if not login_info:
            self._logger.error('plugin/authenticate: login info is None!')
            raise InvalidCredentials()

        self.store_credentials(login_info)
        return Authentication(wgni.get_account_id(), '%s_%s' % (wgni.get_account_realm(), wgni.get_account_nickname()))

    #
    # ImportOwnedGames
    #

    async def get_owned_games(self) -> List[Game]:     
        owned_applications = list()

        wgni = self._wgc.get_wgni_client()
        
        login_info = wgni.login_info_get()
        if login_info is None:
            self._logger.error('plugin/get_owned_games: login info is None', exc_info=True)
            return owned_applications

        realm = wgni.get_account_realm()
        if realm is None:
            self._logger.error('plugin/get_owned_games: realm is None', exc_info=True)
            return owned_applications

        for instance in (await self._wgc.get_owned_applications(realm)).values():
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
        if game_id not in self.__local_applications:
            self._logger.warning('plugin/launch_game: failed to run game with id %s' % game_id)
            return

        self.__local_applications[game_id].run_application(self.__platform)
        self.__change_game_status(game_id, LocalGameState.Installed | LocalGameState.Running, True)

    #
    # InstallGame
    #

    async def install_game(self, game_id: str) -> None:
        if not self._wgc.is_wgc_installed():
            webbrowser.open(self._wgc.get_wgc_install_url())
            return

        wgni = self._wgc.get_wgni_client()
        instances = await self._wgc.get_owned_applications(wgni.get_account_realm())
        if game_id not in instances:
            self._logger.warning('plugin/install_games: failed to find the application with id %s' % game_id)
            raise BackendError()
        
        await instances[game_id].install_application()

    #
    # UninstallGame
    #

    async def uninstall_game(self, game_id: str) -> None:
        self.__local_applications[game_id].uninstall_application()

    #
    # LaunchPlatformClient
    #

    async def launch_platform_client(self) -> None:
        WgcLauncher.launch_wgc(True)

    #
    # ImportFriends
    #

    async def get_friends(self) -> List[UserInfo]:
        xmpp_client = await self.__xmpp_get_client('WOT')

        friends = list()
        for user_id, user_name in (await xmpp_client.get_friends()).items():
            avatar_url = 'https://ru.wargaming.net/clans/media/clans/emblems/cl_307/163307/emblem_195x195.png'
            profile_url = get_profile_url(xmpp_client.get_game_id(), xmpp_client.get_realm(), user_id)
            friends.append(UserInfo(user_id, user_name, avatar_url, profile_url))

        self._logger.info('plugin/get_friends: %s' % friends)
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

    async def prepare_os_compatibility_context(self, game_ids: List[str]) -> Any:     
        result = dict()

        game_restrictions = self._wgc.get_game_restrictions()
        current_platform = get_platform()

        for game_id in game_ids:
            #populate from local app
            if game_id in self.__local_applications:
                result[game_id] = self.__local_applications[game_id].GetOsCompatibility()
                continue

            #windows is supported in any way
            result[game_id] = ['windows']

            #populate from game restriction for non-windows platform
            if current_platform != 'windows' and game_restrictions:
                if game_id in game_restrictions.get_allowed_ids():
                    result[game_id].append(current_platform)

        return result

    async def get_os_compatibility(self, game_id: str, context: Any) -> Optional[OSCompatibility]:      
        game = context[game_id]

        result = None
        for platform in game:
            if platform == 'windows':
                result = OSCompatibility.Windows if result is None else result | OSCompatibility.Windows
            elif platform == 'macos':
                result = OSCompatibility.MacOS if result is None else result | OSCompatibility.MacOS
            elif platform == 'linux':
                result = OSCompatibility.Linux if result is None else result | OSCompatibility.Linux
            else:
                self._logger.error('plugin/get_os_compatibility: unknown platform %s' % platform)

        return result

    #
    # ImportUserPresence
    #

    async def prepare_user_presence_context(self, user_id_list: List[str]) -> Any:
        result = dict()

        xmpp_client = await self.__xmpp_get_client('WOT')
        for user_id in user_id_list:
            result[user_id] = await self.__xmpp_get_gog_presence(xmpp_client.get_presence_userid(user_id))

        return result

    async def get_user_presence(self, user_id: str, context: Any) -> UserPresence:
        if user_id not in context:
            raise UnknownError('plugin/get_user_presence: failed to get info for user %s' % user_id)

        return context[user_id]

    #
    # ImportLocalSize
    #

    async def prepare_local_size_context(self, game_ids: List[str]) -> Any:
        ctx = dict()

        for game_id in game_ids:
            if game_id in self.__local_applications:
                ctx[game_id] = await self.__local_applications[game_id].get_app_size()

        return ctx


    async def get_local_size(self, game_id: str, context: Any) -> Optional[int]:   
        if game_id in context:
            return context[game_id]

        return None

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

    def __rescan_games(self, notify = False):
        self.__local_applications = self._wgc.get_local_applications()

        #delete uninstalled games
        for game_id in self.__local_games_states:
            if game_id not in self.__local_applications:
                self.__change_game_status(game_id, LocalGameState.None_, notify)

        #change status of installed games
        for game_id, game in self.__local_applications.items():
            new_state = LocalGameState.None_
            if game.is_running():
                new_state = LocalGameState.Installed | LocalGameState.Running
            elif game.IsInstalled():
                new_state = LocalGameState.Installed

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

    #
    # Internals/XMPP
    #

    async def __xmpp_get_client(self, client_type: str) -> WgcXMPP:
        if client_type not in self._xmpp:
            self._xmpp[client_type] = await self._wgc.get_xmpp_client(client_type)
            self._xmpp[client_type].add_event_handler('got_online', self.__xmpp_on_got_online)
            self._xmpp[client_type].add_event_handler('got_offline', self.__xmpp_on_got_offline)
            self._xmpp[client_type].connect()

        return self._xmpp[client_type]

    async def __xmpp_on_got_online(self, presence) -> None:
        xmpp_client = await self.__xmpp_get_client('WOT')
        
        user_id = xmpp_client.get_user_name_from_jid(presence['from'])
        if not user_id:
            return

        xmpp_presence = xmpp_client.get_presence_jid(presence['from'])
        user_presence = await self.__xmpp_get_gog_presence(xmpp_presence)
        self.update_user_presence(user_id, user_presence)


    async def __xmpp_on_got_offline(self, presence) -> None:
        xmpp_client = await self.__xmpp_get_client('WOT')

        user_id = xmpp_client.get_user_name_from_jid(presence['from'])
        if not user_id:
            return

        self.update_user_presence(user_id, UserPresence(presence_state = PresenceState.Offline))


    async def __xmpp_get_gog_presence(self, xmpp_presence: str) -> UserPresence:
        xmpp_client = await self.__xmpp_get_client('WOT')

        presence_state = PresenceState.Unknown
        game_id = None
        game_title = None
        status = None

        if xmpp_presence == 'online':
            presence_state = PresenceState.Online
            game_id = xmpp_client.get_game_full_id()
            game_title = xmpp_client.get_game_title()
        elif xmpp_presence == 'mobile':
            presence_state = PresenceState.Online
        elif xmpp_presence == 'offline':
            presence_state = PresenceState.Offline
        else:
            self._logger.error('plugin/__xmpp_get_gog_presence: unknown presence state %s' % xmpp_presence)

        return UserPresence(
            presence_state = presence_state,
            game_id = game_id,
            game_title = game_title,
            in_game_status = status)

    #
    # Internals/Gametime
    #

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
            #it is possible situation in case when we shutdown plugin before finishing handshake
            pass

        if gametime_cache:
            self.persistent_cache["gametime_cache"] = gametime_cache
            self.push_cache()


def main():
    create_and_run_plugin(WargamingPlugin, sys.argv)


if __name__ == "__main__":
    main()
