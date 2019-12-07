import asyncio
import logging
from typing import Dict

import slixmpp

from .wgc_constants import XMPPRealms

class WgcXMPP(slixmpp.ClientXMPP):
    def __init__(self, game, realm, account_id, token1):
        self._game = game.upper()
        self._realm = realm.upper()
        self._account_id = account_id
        self._token1 = token1

        super().__init__(self.get_xmpp_jid(), str(token1), sasl_mech='PLAIN')
       
        #enable authentication via unencrypted PLAIN
        self['feature_mechanisms'].unencrypted_plain = True

        #disable aiodns
        self.use_aiodns = False

        self.add_event_handler('session_start', self.on_session_start)

    def connect(self):
        return super().connect((self.get_xmpp_host(), self.get_xmpp_port()))

    #Callbacks
    def on_session_start(self, event):
        self.send_presence(pfrom=self.get_xmpp_jid(), ppriority=0)
        self.get_roster(callback=self.on_roster_received)

    def on_roster_received(self, event):
        pass


    #Info

    def get_game_id(self) -> str:
        '''
        Returns first part of ID (WOT)
        '''
        return self._game

    def get_game_title(self) -> str:
        '''
        Returns game full name (World of Tanks (RU))
        '''
        if self.get_game_id() == 'WOT':
            return 'World of Tanks (%s)' % self.get_realm()
        else:
            logging.error('WgcXMPP/get_game_title: unknown game id %s' % self.get_game_id())
            return None

    def get_game_full_id(self) -> str:
        '''
        Returns full ID (WOT.RU.PRODUCTION)
        '''
        return '%s.%s.%s' % (self.get_game_id(), self.get_realm(), 'PRODUCTION')

    def get_realm(self) -> str:
        return self._realm

    def get_xmpp_jid(self) -> str:
        return '%s@%s/%s' % (self._account_id, self.get_xmpp_domain(), self._game.lower())

    def get_xmpp_host(self) -> str:
        return XMPPRealms[self._game][self._realm]['host']

    def get_xmpp_port(self) -> int:
        return XMPPRealms[self._game][self._realm]['port']

    def get_xmpp_domain(self) -> str:
        return XMPPRealms[self._game][self._realm]['domain']


    #Roster checks
    async def is_friend(self, account_id) -> bool:
        while len(self.client_roster) == 0:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

        for jid in self.client_roster:
            friend_id = jid.split('@', 1)[0]
            if friend_id == str(account_id):
                return True
        
        return False


    async def get_friends(self) -> Dict[str,str]:
        result = dict()

        while len(self.client_roster) == 0:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

        for jid in self.client_roster:
            user_id = jid.split('@', 1)[0]
            if user_id == str(self._account_id):
                continue
            result[user_id] =  '%s_%s' % (self._realm, self.client_roster[jid]['name'])

        return result


    async def get_presence(self, user_id: str) -> str:
        while len(self.client_roster) == 0:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

        for jid in self.client_roster:
            if jid.split('@', 1)[0] == str(user_id):
                return 'online' if self._game.lower() in self.client_roster[jid].resources else 'offline'

        return 'unknown'
