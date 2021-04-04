# (c) 2019-2021 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
from typing import Any

from mglx.mglx_http import MglxHttp

from .wgc_constants import WGCRealms

class WgcHttp(MglxHttp):
    #
    # Initialization
    #

    HTTP_USER_AGENT = 'wgc/20.01.00.9514'
    
    def __init__(self):
        super(WgcHttp, self).__init__(WgcHttp.HTTP_USER_AGENT, True)
        self.__logger = logging.getLogger('wgc_http')

    #
    # URL Formatting
    # 

    def get_url(self, ltype : str, realm: str, url: str) -> str:
        realm = realm.upper()
        
        try:
            return 'https://%s%s' % (WGCRealms[realm]['domain_%s' % ltype], url)
        except Exception:
            self.__logger.exception('get_url: failed to generate URL for ltype %s and realm %s' % (ltype, realm))
            return None

    #
    # Requests
    #

    async def request_get_simple(self, type: str, realm: str, url: str) -> Any:
        return await self.request('GET', self.get_url(type, realm, url))

    async def request_post_simple(self, type: str, realm: str, url: str, *, params: Any = None, data: Any = None, json: Any = None) -> Any:
        return await self.request('POST', self.get_url(type, realm, url), params = params, data = data, json = json)
