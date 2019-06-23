import sys

from galaxy.api.consts import Platform
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Authentication, Game, LicenseInfo, LicenseType, LocalGame, LocalGameState

from localgames import LocalGames
from version import __version__
from wgc import WGC

class WargamingPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(Platform.Wargaming, __version__, reader, writer, token)
        self._backend_wgc = WGC()
        self._backend_localgames = LocalGames(self)

    async def authenticate(self, stored_credentials=None):
        return Authentication(1,"TestUser")

    async def pass_login_credentials(self, step, credentials, cookies):
        return Authentication(1,"TestUser")

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
        pass

    def tick(self):
        self._backend_localgames.tick()

def main():
    create_and_run_plugin(WargamingPlugin, sys.argv)


if __name__ == "__main__":
    main()
