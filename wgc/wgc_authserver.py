# (c) 2019-2021 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import os.path

import aiohttp

from mglx.mglx_webserver import MglxWebserver

from .wgc_constants import WGCAuthorizationResult


class WgcAuthServer(MglxWebserver):
    def __init__(self, backend = None):
        self.__logger = logging.getLogger('wgc_authserver')

        super(WgcAuthServer, self).__init__()

        self.__backend = backend

        self.add_route('GET', '/'                     , self.handle_login_get                    )
        self.add_route('GET', '/login'                , self.handle_login_get                    )
        self.add_route('GET', '/login_failed'         , self.handle_login_failed_get             )
        self.add_route('GET', '/2fa'                  , self.handle_2fa_get                      )
        self.add_route('GET', '/2fa_failed'           , self.handle_2fa_failed_get               )
        self.add_route('GET', '/finished'             , self.handle_finished_get                 )
        self.add_route('GET', '/unsupported_platform' , self.handle_unsupported_platform_get     )
        self.add_route('GET', '/banned'               , self.handle_banned_get                   )


        self.add_route('POST', '/'     , self.handle_login_post)
        self.add_route('POST', '/login', self.handle_login_post)
        self.add_route('POST', '/2fa'  , self.handle_2fa_post)

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
