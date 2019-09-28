import asyncio
import logging
import os
import sys
from typing import List

#expand sys.path
thirdparty =  os.path.join(os.path.dirname(os.path.realpath(__file__)),'3rdparty\\')
if thirdparty not in sys.path:
    sys.path.insert(0, thirdparty)

from version import __version__

#Start sentry
import sentry_sdk
sentry_sdk.init(
    "https://965fd62de6974b1c8301b794a426238d@sentry.openwg.net/2",
    release=("galaxy-integration-wargaming@%s" % __version__))

from galaxy.api.consts import Platform
from galaxy.api.errors import BackendError, InvalidCredentials
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Authentication, Game, LicenseInfo, LicenseType, LocalGame, LocalGameState, NextStep, FriendInfo

from localgames import LocalGames

from wgc import WGC, PAPIWoT, WgcXMPP

class WargamingPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(Platform.Wargaming, __version__, reader, writer, token)

        self._wgc = WGC()
        self._xmpp = dict()

        self._localgames = LocalGames(self, self._wgc)

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

    async def get_local_games(self):
        return self._localgames.get_local_games()

    async def get_owned_games(self):       
        owned_applications = list()

        for instance in self._wgc.get_owned_applications().values():
            owned_applications.append(Game(instance.get_application_id(), instance.get_application_fullname(), None, LicenseInfo(LicenseType.FreeToPlay, None)))

        return owned_applications

    async def launch_game(self, game_id):
        game = self._localgames.get_wgc_game(game_id)
        if game is not None:
            game.RunExecutable()
        
    async def install_game(self, game_id):
        instances = self._wgc.get_owned_applications()

        if game_id not in instances:
            logging.warning('plugin/install_games: failed to find the application with id %s' % game_id)
            raise BackendError()
        
        instances[game_id].install_application()

    async def uninstall_game(self, game_id):
        game = self._localgames.get_wgc_game(game_id)
        if game is not None:
            game.UninstallGame()

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
        self._localgames.tick()


    def __xmpp_get_client(self, client_type: str) -> WgcXMPP:
        if client_type not in self._xmpp:
            self._xmpp[client_type] = self._wgc.get_xmpp_client(client_type)
            self._xmpp[client_type].connect()

        return self._xmpp[client_type]

def main():
    create_and_run_plugin(WargamingPlugin, sys.argv)


if __name__ == "__main__":
    main()
