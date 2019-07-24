import asyncio
import time

from galaxy.api.types import LocalGame, LocalGameState

class LocalGames():
    LOCAL_GAMES_CACHE_VALID_PERIOD = 5

    def __init__(self, plugin, wgc):
        self._wgc_games = dict()
        self._games_local = dict()
        self._plugin = plugin
        self._wgc = wgc
        self._local_games_update_in_progress = False
        self._local_games_last_update = 0
        self._task = None

        self.__rescan_wgc()


    def get_local_games(self):
        return list(self._games_local.values())


    def get_wgc_games(self):
        return self._wgc_games.values()

    def get_wgc_game(self, game_id):
        if game_id in self._games_local:
            return self._wgc_games[game_id]

        return None

    def tick(self):
        if time.time() - self._local_games_last_update < self.LOCAL_GAMES_CACHE_VALID_PERIOD:
            return

        if not self._task or self._task.done():
           self._task = self._plugin.create_task(self.__task_local_games_update(), 'wgc_localgames_update')


    def __rescan_wgc(self):
        self._games_local.clear()

        self._wgc_games = self._wgc.get_local_applications()

        for id, game in self._wgc_games.items():
            local_game_state = LocalGameState.Installed | LocalGameState.Running if game.IsRunning() else LocalGameState.Installed
            self._games_local[id] = LocalGame(id, local_game_state)


    async def __task_local_games_update(self):
        notify_list = list()

        try:
            self._local_games_update_in_progress = True
            for id, game in self._wgc_games.items():
                local_game_state = LocalGameState.Installed | LocalGameState.Running if game.IsRunning() else LocalGameState.Installed
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
