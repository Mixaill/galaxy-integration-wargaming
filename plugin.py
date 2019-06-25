import logging
import os
import sys

#expand sys.path
thirdparty =  os.path.join(os.path.dirname(os.path.realpath(__file__)),'3rdparty\\')
if thirdparty not in sys.path:
    sys.path.insert(0, thirdparty)

from galaxy.api.consts import Platform
from galaxy.api.errors import InvalidCredentials
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Authentication, Game, LicenseInfo, LicenseType, LocalGame, LocalGameState, NextStep

from localgames import LocalGames
from version import __version__
from wgc import WGC

class WargamingPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(Platform.Wargaming, __version__, reader, writer, token)

        self._backend_wgc = WGC()
        self._backend_localgames = LocalGames(self)

    async def authenticate(self, stored_credentials=None):
        backend_auth = self._backend_wgc.GetAuthorizationBackend()

        if not stored_credentials:
            logging.info('No stored credentials')

            AUTH_PARAMS = {
                "window_title": "Login to Wargaming",
                "window_width": 640,
                "window_height": 460,
                "start_uri": 'http://%s:%s/login' % (backend_auth.LOCALSERVER_HOST, backend_auth.LOCALSERVER_PORT),
                "end_uri_regex": '.*finished'
            }
            backend_auth.auth_server_start()
            return NextStep("web_session", AUTH_PARAMS)

        else:
            auth_passed = backend_auth.login_info_set(stored_credentials)
            if not auth_passed:
                logging.warning('Stored credentials are invalid')
                raise InvalidCredentials()
            
            return Authentication(backend_auth.get_account_id(), backend_auth.get_account_email())

    async def pass_login_credentials(self, step, credentials, cookies):
        backend_auth = self._backend_wgc.GetAuthorizationBackend()
        backend_auth.auth_server_stop()

        login_info = backend_auth.login_info_get()
        if not login_info:
            logging.error('Login info is None!')

        self.store_credentials(login_info)
        return Authentication(backend_auth.get_account_id(), backend_auth.get_account_email())

    async def get_local_games(self):
        return self._backend_localgames.get_local_games()

    async def get_owned_games(self):
        owned_games = []

        for game in self._backend_localgames.GetWgcGames():
            owned_games.append(Game(game.GetId(), game.GetName(), [], LicenseInfo(LicenseType.FreeToPlay, None)))

        return owned_games

    async def launch_game(self, game_id):
        game = self._backend_localgames.GetWgcGame(game_id)
        if game is not None:
            game.RunExecutable()
        
    async def install_game(self, game_id):
        pass

    async def uninstall_game(self, game_id):
        game = self._backend_localgames.GetWgcGame(game_id)
        if game is not None:
            game.UninstallGame()

    def tick(self):
        self._backend_localgames.tick()

def main():
    create_and_run_plugin(WargamingPlugin, sys.argv)

if __name__ == "__main__":
    main()
