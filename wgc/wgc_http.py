import collections
import ssl
from typing import Any, Dict

import aiohttp
import certifi

class WgcHttp:
    HTTP_USER_AGENT = 'wgc/20.01.00.9514'
    
    def __init__(self):
        self.__sslcontext = ssl.create_default_context(cafile=certifi.where())
        self.__connector = aiohttp.TCPConnector(ssl_context=self.__sslcontext)
        self.__session_headers = {'User-Agent': self.HTTP_USER_AGENT}
        self.__session = aiohttp.ClientSession(connector=self.__connector, headers = self.__session_headers)


    async def shutdown(self):
        await self.__session.close()


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


    async def request_post(self, url: str, *, params: Any = None, data: Any = None, json: Any = None) -> Any:
        return await self.request('POST', url, params = params, data = data, json = json)

