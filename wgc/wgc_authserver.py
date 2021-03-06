import asyncio
import os
import logging

import aiohttp
import aiohttp.web

from .wgc_constants import WGCAuthorizationResult

class WgcAuthorizationServer():
    LOCALSERVER_HOST = '127.0.0.1'
    LOCALSERVER_PORT = 13337

    def __init__(self, backend):
        self.__logger = logging.getLogger('wgc_authserver')

        self.__backend = backend
        self.__app = aiohttp.web.Application()

        self.__runner = None
        self.__site = None
        self.__task = None


        self.__app.add_routes([
            aiohttp.web.get ('/login'                , self.handle_login_get                    ),
            aiohttp.web.get ('/login_failed'         , self.handle_login_failed_get             ),
            aiohttp.web.get ('/2fa'                  , self.handle_2fa_get                      ),
            aiohttp.web.get ('/2fa_failed'           , self.handle_2fa_failed_get               ),
            aiohttp.web.get ('/finished'             , self.handle_finished_get                 ),
            aiohttp.web.get ('/unsupported_platform' , self.handle_unsupported_platform_get     ),
            aiohttp.web.get ('/banned'               , self.handle_banned_get                   ),

            aiohttp.web.post('/login'   , self.handle_login_post  ),   
            aiohttp.web.post('/2fa'     , self.handle_2fa_post    ),
        ])
    
    #
    # Info
    #

    def get_uri(self) -> str:
        return 'http://%s:%s/login' % (self.LOCALSERVER_HOST, self.LOCALSERVER_PORT)

    #
    # Start/Stop
    #

    async def start(self) -> bool:

        if self.__task is not None:
            self.__logger.warning('auth_server_start: auth server object is already exists')
            return False

        self.__task = asyncio.create_task(self.__worker(self.LOCALSERVER_HOST, self.LOCALSERVER_PORT))
        return True


    async def shutdown(self):    
        if self.__runner is not None:
            await self.__runner.cleanup()


    async def __worker(self, host, port):
        self.__runner = aiohttp.web.AppRunner(self.__app)
        await self.__runner.setup()
    
        self.__site = aiohttp.web.TCPSite(self.__runner, host, port)
        await self.__site.start()    

    #
    # Handlers
    #

    async def handle_login_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/login.html'))

    async def handle_unsupported_platform_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/unsupported_platform.html'))

    async def handle_login_failed_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/login_failed.html'))

    async def handle_2fa_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/2fa.html'))

    async def handle_2fa_failed_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/2fa_failed.html'))

    async def handle_finished_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/finished.html'))

    async def handle_banned_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html/banned.html'))

    async def handle_login_post(self, request):
        data = await request.post()
        auth_result = WGCAuthorizationResult.FAILED

        #check data
        data_valid = True
        if 'realm' not in data or not data['realm']:
            self.__logger.warning('handle_login_post: data is not valid, realm is missing')
            data_valid = False
        if 'email' not in data or not data['email']:
            self.__logger.warning('handle_login_post: data is not valid, email is missing')
            data_valid = False
        if 'password' not in data or not data['password']:
            self.__logger.warning('handle_login_post: data is not valid, password is missing')
            data_valid = False

        if data_valid:
            auth_result = await self.__backend.do_auth_emailpass(data['realm'], data['email'], data['password'])

        self.__process_auth_result(auth_result)

    async def handle_2fa_post(self, request):
        data = await request.post()

        auth_result = WGCAuthorizationResult.INCORRECT_2FA
        if 'authcode' in data and data['authcode']:
            use_backup_code = True if 'use_backup' in data else False
            auth_result = await self.__backend.do_auth_2fa(data['authcode'], use_backup_code)

        self.__process_auth_result(auth_result)

    def __process_auth_result(self, auth_result):
        if auth_result == WGCAuthorizationResult.FINISHED:
            raise aiohttp.web.HTTPFound('/finished')
        elif auth_result == WGCAuthorizationResult.REQUIRES_2FA:
            raise aiohttp.web.HTTPFound('/2fa')
        elif auth_result == WGCAuthorizationResult.INCORRECT_2FA or auth_result == WGCAuthorizationResult.INCORRECT_2FA_BACKUP: 
            raise aiohttp.web.HTTPFound('/2fa_failed')
        elif auth_result == WGCAuthorizationResult.BANNED: 
            raise aiohttp.web.HTTPFound('/banned')
        else:
            raise aiohttp.web.HTTPFound('/login_failed')
