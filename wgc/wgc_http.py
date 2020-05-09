# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import collections
import logging
import ssl
from typing import Any, Dict

import aiohttp
import certifi

from .wgc_constants import WGCRealms

class WgcHttp:
    HTTP_USER_AGENT = 'wgc/20.01.00.9514'
    
    def __init__(self):
        self.__logger = logging.getLogger('wgc_http')

        self.__sslcontext = ssl.create_default_context(cafile=certifi.where())
        self.__connector = aiohttp.TCPConnector(ssl_context=self.__sslcontext)
        self.__session_headers = {'User-Agent': self.HTTP_USER_AGENT}
        self.__session = aiohttp.ClientSession(connector=self.__connector, headers = self.__session_headers)


    async def shutdown(self):
        await self.__session.close()


    #
    # URL Formatting
    # 
    def get_url(self, ltype : str, realm: str, url: str) -> str:
        realm = realm.upper()
        
        try:
            return 'https://%s%s' % (WGCRealms[realm]['domain_%s' % ltype ], url)
        except Exception:
            self.__logger.exception('get_url: failed to generate URL for ltype %s and realm %s' % (ltype, realm))
            return None


    def update_headers(self, headers: Dict):
        '''
        update HTTP headers
        '''
        self.__session_headers.update(headers)


    async def request(self, method: str, url: str, *, params: Any = None, data: Any = None, json: Any = None):
        response_status = 202
        response_text = None

        if 'Referer' in self.__session_headers:
            self.__session_headers.pop('Referer')
    
        while True:
            async with self.__session.request(method, url, headers = self.__session_headers, params = params, data = data, json = json) as response:
                response_text = await response.text()
                response_status = response.status
                if response_status == 202 and 'Location' in response.headers:
                    url = response.headers['Location']
                    self.__session_headers.update({'Referer': str(response.url)})
                    method = 'GET'
                else:
                    break

        return collections.namedtuple('WgcHttpResponse', ['status', 'text'])(response_status, response_text)


    async def request_get(self, url: str) -> Any:
        return await self.request('GET', url)


    async def request_get_simple(self, type: str, realm: str, url: str) -> Any:
        return await self.request('GET', self.get_url(type, realm, url))


    async def request_post(self, url: str, *, params: Any = None, data: Any = None, json: Any = None) -> Any:
        return await self.request('POST', url, params = params, data = data, json = json)


    async def request_post_simple(self, type: str, realm: str, url: str, *, params: Any = None, data: Any = None, json: Any = None) -> Any:
        return await self.request('POST', self.get_url(type, realm, url), params = params, data = data, json = json)

