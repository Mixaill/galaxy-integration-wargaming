import asyncio
import time

from galaxy.api.types import LocalGame, LocalGameState

class LocalGames():
    LOCAL_GAMES_CACHE_VALID_PERIOD = 5

    def __init__(self, plugin):
        self._wgc_games = dict()
        self._games_local = dict()
        self._plugin = plugin
        self._local_games_update_in_progress = False
        self._local_games_last_update = 0

        self.__rescan_wgc()

    def GetWgcGames(self):
        return self._wgc_games.values()

    def GetWgcGame(self, game_id):
        if game_id in self._games_local:
            return self._wgc_games[game_id]

        return None

    def __rescan_wgc(self):
        self._games_local.clear()

        self._wgc_games = self._plugin._backend_wgc.GetGames()
        for id, game in self._wgc_games.items():
            local_game_state = LocalGameState.Running if game.IsRunning() else LocalGameState.Installed
            self._games_local[id] = LocalGame(id, local_game_state)

    def get_local_games(self):
        return list(self._games_local.values())

    def tick(self):
        async def notify_local_games_changed():
            notify_list = list()

            try:
                self._local_games_update_in_progress = True
                for id, game in self._wgc_games.items():
                    local_game_state = LocalGameState.Running if game.IsRunning() else LocalGameState.Installed
                    local_game = LocalGame(id, local_game_state)
                    
                    if id not in self._games_local:
                        notify_list.append(local_game)          
                    elif local_game_state != self._games_local[id].local_game_state:
                        notify_list.append(local_game)

                self._local_games_last_update = time.time()
            finally:
                self._local_games_update_in_progress = False

            for local_game in notify_list:
                self._games_local[id] = local_game
                self._plugin.update_local_game_status(local_game)

        # don't overlap update operations
        if self._local_games_update_in_progress:
            return

        if time.time() - self._local_games_last_update < self.LOCAL_GAMES_CACHE_VALID_PERIOD:
            return

        asyncio.create_task(notify_local_games_changed())
