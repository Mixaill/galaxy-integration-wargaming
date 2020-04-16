# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
from typing import Dict

import slixmpp

from .wgc_constants import XMPPRealms, XMPPPresence

class WgcXMPP(slixmpp.ClientXMPP):
    def __init__(self, game, realm, account_id, token1):
        self._game = game.upper()
        self._realm = realm.upper()
        self._account_id = account_id
        self._token1 = token1

        super().__init__(self.get_xmpp_jid(), str(token1), sasl_mech='PLAIN')

        #enable plugins
        self.register_plugin('xep_0199') #XMPP Ping

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
        Returns game full name
        '''
        return XMPPRealms[self._game][self._realm]['title']

    def get_game_full_id(self) -> str:
        '''
        Returns full ID (WOT.RU.PRODUCTION)
        '''
        return '%s.%s.%s' % (self.get_game_id(), self.get_realm(), 'PRODUCTION')

    def get_realm(self) -> str:
        return self._realm

    def get_xmpp_jid(self) -> str:
        return '%s@%s/%s' % (self._account_id, self.get_xmpp_domain(), XMPPRealms[self._game][self._realm]['res'])

    def get_xmpp_host(self) -> str:
        return XMPPRealms[self._game][self._realm]['host']

    def get_xmpp_port(self) -> int:
        return XMPPRealms[self._game][self._realm]['port']

    def get_xmpp_domain(self) -> str:
        return XMPPRealms[self._game][self._realm]['domain']


    #Roster checks
    async def is_friend(self, account_id) -> bool:
        for jid in self.client_roster:
            friend_id = jid.split('@', 1)[0]
            if friend_id == str(account_id):
                return True
        
        return False

    @staticmethod
    def get_user_id_from_jid(jid: str) -> str:
        return jid.split('@', 1)[0]

    def get_user_name_from_jid(self, jid: str) -> str:
        name = self.client_roster[jid]['name']
        if not name:
            return None

        return '%s_%s' % (self._realm, self.client_roster[jid]['name'])

    async def get_friends(self) -> Dict[str,str]:
        result = dict()

        for jid in self.client_roster:
            user_id = WgcXMPP.get_user_id_from_jid(jid)
            if user_id == str(self._account_id):
                continue
            result[user_id] = self.get_user_name_from_jid(jid)
        return result

    def get_presence_userid(self, user_id: str) -> str:
        for jid in self.client_roster:
            if WgcXMPP.get_user_id_from_jid(jid) == str(user_id):
                for key,val in XMPPPresence[self.get_game_id()].items():
                    if val in self.client_roster[jid].resources:
                        return key

        return 'offline'

    def get_presence_jid(self, jid) -> str:
        for key,val in XMPPPresence[self.get_game_id()].items():
            if val == jid.resource:
                return key

        return 'offline'
