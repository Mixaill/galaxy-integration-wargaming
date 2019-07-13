import asyncio
import logging

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

        self.add_event_handler('session_start', self.on_session_start)

    def connect(self):
        return super().connect((self.get_xmpp_host(), self.get_xmpp_port()))

    #Callbacks
    def on_session_start(self, event):
        self.send_presence()
        self.get_roster(callback=self.on_roster_received)

    def on_roster_received(self, event):
        pass


    #Info

    def get_xmpp_jid(self) -> str:
        return '%s@%s' % (self._account_id, self.get_xmpp_domain())

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
