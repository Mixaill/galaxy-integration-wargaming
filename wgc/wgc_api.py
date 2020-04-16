# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import asyncio
from collections import namedtuple
import json
import logging
import os
import platform
import pprint
import random
import string
import sys
import threading
from typing import Any, Dict, List
from urllib.parse import parse_qs


import aiohttp
import aiohttp.web
import sha3

from .wgc_application_owned import WGCOwnedApplication
from .wgc_constants import WGCAuthorizationResult, WGCRealms, GAMES_F2P

class WGCAuthorizationServer():

    def __init__(self, backend):
        self.__backend = backend
        self.__app = aiohttp.web.Application()

        self.__runner = None
        self.__site = None

        self.__app.add_routes([
            aiohttp.web.get ('/login'                , self.handle_login_get                    ),
            aiohttp.web.get ('/login_failed'         , self.handle_login_failed_get             ),
            aiohttp.web.get ('/2fa'                  , self.handle_2fa_get                      ),
            aiohttp.web.get ('/2fa_failed'           , self.handle_2fa_failed_get               ),
            aiohttp.web.get ('/finished'             , self.handle_finished_get                 ),
            aiohttp.web.get ('/unsupported_platform' , self.handle_unsupported_platform_get     ),
            
            aiohttp.web.post('/login'   , self.handle_login_post  ),   
            aiohttp.web.post('/2fa'     , self.handle_2fa_post    ),
        ])
    
    async def start(self, host, port):
        self.__runner = aiohttp.web.AppRunner(self.__app)
        await self.__runner.setup()
    
        self.__site = aiohttp.web.TCPSite(self.__runner, host, port)
        await self.__site.start()    

    async def shutdown(self):    
        await self.__runner.cleanup()

    async def handle_login_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\login.html'))

    async def handle_unsupported_platform_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\unsupported_platform.html'))

    async def handle_login_failed_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\login_failed.html'))

    async def handle_2fa_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\2fa.html'))

    async def handle_2fa_failed_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\2fa_failed.html'))

    async def handle_finished_get(self, request):
        return aiohttp.web.FileResponse(os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\finished.html'))

    async def handle_login_post(self, request):
        data = await request.post()
        auth_result = WGCAuthorizationResult.FAILED

        #check data
        data_valid = True
        if 'realm' not in data or not data['realm']:
            logging.warning('wgc_auth_server/handle_login_post: data is not valid, realm is missing')
            data_valid = False
        if 'email' not in data or not data['email']:
            logging.warning('wgc_auth_server/handle_login_post: data is not valid, email is missing')
            data_valid = False
        if 'password' not in data or not data['password']:
            logging.warning('wgc_auth_server/handle_login_post: data is not valid, password is missing')
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
        else:
            raise aiohttp.web.HTTPFound('/login_failed')

class WGCApi:
    HTTP_USER_AGENT = 'wgc/20.01.00.9514'

    OAUTH_GRANT_TYPE_BYPASSWORD = 'urn:wargaming:params:oauth:grant-type:basic'
    OAUTH_GRANT_TYPE_BYTOKEN = 'urn:wargaming:params:oauth:grant-type:access-token'
    OUATH_URL_CHALLENGE = '/id/api/v2/account/credentials/create/oauth/token/challenge/'
    OAUTH_URL_TOKEN = '/id/api/v2/account/credentials/create/oauth/token/'
    
    WGNI_URL_TOKEN1 = '/id/api/v2/account/credentials/create/token1/'
    WGNI_URL_ACCOUNTINFO = '/id/api/v2/account/info/'

    WGCPS_FETCH_PRODUCT_INFO = '/platform/api/v1/fetchProductList'
    WGCPS_LOGINSESSION = '/auth/api/v1/loginSession'
    
    WGUSCS_SHOWROOM = '/api/v16/content/showroom/'

    LOCALSERVER_HOST = '127.0.0.1'
    LOCALSERVER_PORT = 13337

    def __init__(self, tracking_id : str = '', country_code : str = '', language_code : str = 'en'):
        self._tracking_id = tracking_id
        self._country_code = country_code
        self._language_code = language_code

        self.__server = None

        self.__login_info = None
        self.__login_info_temp = None

        self.__session_headers = {'User-Agent': self.HTTP_USER_AGENT}
        self.__session = aiohttp.ClientSession(headers = {'User-Agent': self.HTTP_USER_AGENT})

    async def shutdown(self):
        if self.__server is not None:
            await self.auth_server_stop()
        
        await self.__session.close()

    #
    # Requests
    #

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

        return namedtuple('WgcResponse', ['status', 'text'])(response_status, response_text)

    async def request_get(self, url: str) -> Any:
        return await self.request('GET', url)

    async def request_post(self, url: str, *, params: Any = None, data: Any = None, json: Any = None) -> Any:
        return await self.request('POST', url, params = params, data = data, json = json)

    # 
    # Getters
    #

    def get_account_id(self) -> int:
        if self.__login_info is None:
            logging.error('login info is none')
            return None

        if 'user' not in self.__login_info:
            logging.error('login info does not contains user id')
            return None

        return int(self.__login_info['user'])

    def get_account_email(self) -> str:
        if self.__login_info is None:
            logging.error('login info is none')
            return None

        if 'email' not in self.__login_info:
            logging.error('login info does not contains email')
            return None

        return self.__login_info['email']

    def get_account_nickname(self) -> str:
        if self.__login_info is None:
            logging.error('login info is none')
            return None

        if 'nickname' not in self.__login_info:
            logging.error('login info does not contains nickname')
            return None

        return self.__login_info['nickname']
        
    def get_account_realm(self) -> str:
        if self.__login_info is None:
            logging.error('login info is none')
            return None

        if 'realm' not in self.__login_info:
            logging.error('login info does not contains realm')
            return None

        return self.__login_info['realm']

    #
    # Authorization server
    #

    def auth_server_uri(self) -> str:
        if platform.system() == 'Windows':
            return 'http://%s:%s/login' % (self.LOCALSERVER_HOST, self.LOCALSERVER_PORT)
        
        return 'http://%s:%s/unsupported_platform' % (self.LOCALSERVER_HOST, self.LOCALSERVER_PORT)

    async def auth_server_start(self) -> bool:

        if self.__server is not None:
            logging.warning('wgc_api/auth_server_start: auth server object is already exists')
            return False

        self.__server = WGCAuthorizationServer(self)
        self.__server_task = asyncio.create_task(self.__server.start(self.LOCALSERVER_HOST, self.LOCALSERVER_PORT))

        return True

    async def auth_server_stop(self) -> bool:
        if self.__server is not None:
            await self.__server.shutdown()
            self.__server = None
            return True
        else:
            logging.warning('wgc_ap/auth_server_stop: auth server object is not exits')
            return False

    #
    # Login Info
    #

    def login_info_get(self) -> Dict[str,str]:
        return self.__login_info

    async def login_info_set(self, login_info: Dict[str,str]) -> bool:

        if login_info is None:
            logging.error('wgc_auth/login_info_set: login info is none')
            return False

        if 'realm' not in login_info:
            logging.error('wgc_auth/login_info_set: realm is missing')
            return False

        if 'access_token' not in login_info:
            logging.error('wgc_auth/login_info_set: access token is missing')
            return False

        if 'exchange_code' not in login_info:
            logging.error('wgc_auth/login_info_set: exchange code is missing')
            return False

        if 'email' not in login_info:
            logging.error('wgc_auth/login_info_set: email')
            return False

        if 'user' not in login_info:
            logging.error('wgc_auth/login_info_set: user is missing')
            return False

        self.__login_info = login_info
        self.__update_bearer()

        wgni_account_info = await self.__wgni_get_account_info()

        if wgni_account_info is None:
            logging.error('wgc_auth/login_info_set: failed to get account info')
            return False

        if wgni_account_info['sub'] != login_info['user']:
            logging.error('wgc_auth/login_info_set: SPA ID missmatch')
            return False
        
        return True

    #
    # Authorization routine
    # 

    async def do_auth_emailpass(self, realm, email, password) -> WGCAuthorizationResult:
        '''
        Perform authorization using email and password
        '''

        self.__login_info_temp = {'realm': realm, 'email': email, 'password': password}

        challenge_data = await self.__oauth_challenge_get(realm)
        if not challenge_data:
            logging.error('do_auth_emailpass/ failed to get challenge')
            return WGCAuthorizationResult.FAILED

        #calculate proof of work
        pow_number = self.__oauth_challenge_calculate(challenge_data)
        if not pow_number:
            logging.error('wgc_auth/do_auth_emailpass: failed to calculate challenge')
            return WGCAuthorizationResult.FAILED
        self.__login_info_temp['pow_number'] = pow_number

        #try to get token
        token_data_bypassword = await self.__oauth_token_get_bypassword(realm, email, password, pow_number)

        #process error
        if token_data_bypassword['status_code'] != 200:
            if 'error_description' in token_data_bypassword:
                if token_data_bypassword['error_description'] == 'twofactor_required':
                    self.__login_info_temp['twofactor_token'] = token_data_bypassword['twofactor_token']
                    return WGCAuthorizationResult.REQUIRES_2FA
                elif token_data_bypassword['error_description'] == 'Invalid password parameter value.':
                    return WGCAuthorizationResult.INVALID_LOGINPASS
                elif token_data_bypassword['error_description'] == 'Request is missing password parameter.':
                    return WGCAuthorizationResult.INVALID_LOGINPASS
                elif token_data_bypassword['error_description'] == 'account_not_found':
                    return WGCAuthorizationResult.ACCOUNT_NOT_FOUND

            logging.error('wgc_auth/do_auth_emailpass: failed to request token by email and password: %s' % token_data_bypassword)
            return WGCAuthorizationResult.FAILED

        return await self.do_auth_token(realm, email, token_data_bypassword)

    async def do_auth_2fa(self, otp_code: str, use_backup_code: bool) -> WGCAuthorizationResult:
        '''
        Submits 2FA answer and continue authorization
        '''

        if 'realm' not in self.__login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: realm not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'email' not in self.__login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: email not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'password' not in self.__login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: password not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'pow_number' not in self.__login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: pow number not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'twofactor_token' not in self.__login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: twofactor token not in stored data')
            return WGCAuthorizationResult.FAILED

        token_data_byotp = await self.__oauth_token_get_bypassword(
            self.__login_info_temp['realm'],
            self.__login_info_temp['email'],
            self.__login_info_temp['password'],
            self.__login_info_temp['pow_number'],
            self.__login_info_temp['twofactor_token'],
            otp_code,
            use_backup_code)

        # process error
        if token_data_byotp['status_code'] != 200:
            if 'error_description' in token_data_byotp:
                error_desc = token_data_byotp['error_description'] 
                if error_desc == 'twofactor_invalid' or error_desc == 'Invalid otp_code parameter value.':
                    return WGCAuthorizationResult.INCORRECT_2FA
                if error_desc == 'Invalid backup_code parameter value.':
                    return WGCAuthorizationResult.INCORRECT_2FA_BACKUP
            
            logging.error('wgc_auth/do_auth_2fa: failed to request token by email, password and OTP: %s' % token_data_byotp)
            return WGCAuthorizationResult.FAILED

        return await self.do_auth_token(self.__login_info_temp['realm'], self.__login_info_temp['email'], token_data_byotp)

    async def do_auth_token(self, realm, email, token_data_input) -> WGCAuthorizationResult:
        '''
        Second step of authorization in case if you already logged in via emailpass or 2FA
        '''

        token_data_bytoken = await self.__oauth_token_get_bytoken(realm, token_data_input)
        if not token_data_bytoken:
            logging.error('wgc_auth/do_auth_token: failed to request token by token')
            return WGCAuthorizationResult.FAILED
        
        #generate login info
        login_info = dict()
        login_info['realm'] = realm
        login_info['email'] = email
        login_info['user'] = token_data_bytoken['user']
        login_info['access_token'] = token_data_bytoken['access_token']
        login_info['exchange_code'] = token_data_bytoken['exchange_code']
        self.__login_info = login_info

        #update bearer
        self.__update_bearer()

        #get additinal info from WGNI
        wgni_account_info = await self.__wgni_get_account_info()
        logging.info(wgni_account_info)
        self.__login_info['nickname'] = wgni_account_info['nickname']

        return WGCAuthorizationResult.FINISHED

    def __update_bearer(self):
        if self.__login_info is None:
            logging.error('wgc_auth/update_bearer: login info is none')
            return None

        if 'access_token' not in self.__login_info:
            logging.error('wgc_auth/update_bearer: login info does not contain access token')
            return None

        if 'exchange_code' not in self.__login_info:
            logging.error('wgc_auth/update_bearer: login info does not contain exchange code')
            return None

        self.__session_headers.update({'Authorization':'Bearer %s:%s' % (self.__login_info['access_token'], self.__login_info['exchange_code'])})

    #
    # URL formatting
    #

    def __get_url(self, ltype : str, realm: str, url: str) -> str:
        realm = realm.upper()
        
        try:
            return 'https://%s%s' % (WGCRealms[realm]['domain_%s' % ltype ], url)
        except Exception:
            logging.exception('wgc_api/__get_url: failed to generate URL for ltype %s and realm %s' % (ltype, realm))
            return None

    #
    # OAuth
    #

    def __oauth_get_clientid(self, realm):
        realm = realm.upper()

        try:
            return WGCRealms[realm]['client_id']
        except Exception:
            logging.exception('wgc_api/__get_oauth_clientid: failed to get client Id for realm %s' % realm)
            return None

    async def __oauth_challenge_get(self, realm):
        r = await self.request_get(self.__get_url('wgnet', realm, self.OUATH_URL_CHALLENGE))
        if r.status != 200:
            logging.error('wgc_auth/oauth_challenge_get: error %s, content: %s' % (r.status, r.text))
            return None

        return json.loads(r.text)['pow']
        
    def __oauth_challenge_calculate(self, challenge_data):
        if challenge_data['algorithm']['name'] != 'hashcash' :
            logging.error('unknown proof-of-work algorithm')
            return None

        prefix = '0' * challenge_data['complexity']
        hashcash_str = '%s:%s:%s:%s:%s:%s:' % (
            challenge_data['algorithm']['version'], 
            challenge_data['complexity'], 
            challenge_data['timestamp'], 
            challenge_data['algorithm']['resourse'], 
            challenge_data['algorithm']['extension'], 
            challenge_data['random_string'])
        hashcash_str = hashcash_str.encode('utf-8')

        pow_number = 0
        while True:
            keccak_hash = sha3.keccak_512()
            keccak_hash.update(hashcash_str+str(pow_number).encode('utf-8'))

            if keccak_hash.hexdigest().startswith(prefix):
                return pow_number

            pow_number = pow_number + 1

    async def __oauth_token_get_bypassword(self, realm, email, password, pow_number, twofactor_token : str = None, otp_code : str = None, use_backup_code : bool = False):
        body = dict()
        body['username'] = email
        body['password'] = password
        body['grant_type'] = self.OAUTH_GRANT_TYPE_BYPASSWORD
        body['client_id'] = self.__oauth_get_clientid(realm)
        body['tid'] = self._tracking_id
        body['pow'] = pow_number
        if twofactor_token is not None:
            body['twofactor_token'] = twofactor_token
        if otp_code is not None:
            if use_backup_code:
                body['backup_code'] = otp_code
            else:
                body['otp_code'] = otp_code

        response = await self.request_post(self.__get_url('wgnet', realm, self.OAUTH_URL_TOKEN), data = body)
        
        result = None
        try:
            result = json.loads(response.text)
        except Exception:
            logging.exception('wgc_api/__oauth_token_get_bypassword: failed to parse response %s' % response.text)
            return result

        result['status_code'] = response.status
        return result

    async def __oauth_token_get_bytoken(self, realm, token_data):
        body = dict()
        body['access_token'] = token_data['access_token']
        body['grant_type'] = self.OAUTH_GRANT_TYPE_BYTOKEN
        body['client_id'] = self.__oauth_get_clientid(realm)
        body['exchange_code'] = ''.join(random.choices(string.digits+'ABCDEF', k=32))
        body['tid'] = self._tracking_id

        response = await self.request_post(self.__get_url('wgnet', realm, self.OAUTH_URL_TOKEN), data = body)

        if response.status != 200:
            logging.error('wgc_auth/__oauth_token_get_bytoken: error on receiving token by token: %s because status is %s' % (response.text, response.status))
            return None

        result = json.loads(response.text)
        result['exchange_code'] = body['exchange_code']

        return result

    #
    # Token1
    #

    async def create_token1(self, requested_for : str) -> str:
        resp = await self.__wgni_create_token_1(requested_for)

        if resp is None:
            logging.error('wgc_api/create_token1: failed to create token1 for %s' % requested_for)
            return None

        if 'token' not in resp:
            logging.error('wgc_api/create_token1: server response for %s does not contains token: %s' % (requested_for, resp))
            return None

        return resp['token']

    async def __wgni_create_token_1(self, requested_for : str):
        if self.__login_info is None:
            logging.error('wgc_api/__wgni_create_token_1: login info is none')
            return None

        if 'realm' not in self.__login_info:
            logging.error('wgc_api/__wgni_create_token_1: login info does not contain realm')
            return None

        if 'access_token' not in self.__login_info:
            logging.error('wgc_api/__wgni_create_token_1: login info does not contain access_token')
            return None

        response = await self.request_post(
            self.__get_url('wgnet', self.__login_info['realm'], self.WGNI_URL_TOKEN1), 
            data = { 'requested_for' : requested_for, 'access_token' : self.__login_info['access_token'] })

        if response.status != 200:
            logging.error('wgc_api/__wgni_create_token_1: error on creating token1: %s' % response.text)
            return None

        return json.loads(response.text)

    #
    # Account info
    #

    async def __wgni_get_account_info(self):
        if self.__login_info is None:
            logging.error('wgc_auth/wgni_get_account_info: login info is none')
            return None

        if 'realm' not in self.__login_info:
            logging.error('wgc_auth/wgni_get_account_info: login info does not contain realm')
            return None

        response = await self.request_post(
            self.__get_url('wgnet', self.__login_info['realm'], self.WGNI_URL_ACCOUNTINFO), 
            data = { 'fields' : 'nickname' })
        
        if response.status != 200:
            logging.error('wgc_auth/wgni_get_account_info: error on retrieving account info: %s' % response.text)
            return None

        return json.loads(response.text)

    #
    # Fetch product list
    #

    async def fetch_product_list(self) -> List[WGCOwnedApplication]:
        product_list = list()

        additional_gameurls = list()
        purchased_gameids = list()
        wgcps_product_list = await self.__wgcps_fetch_product_list()
        if wgcps_product_list is not None:
            for game_data in wgcps_product_list['data']['product_content']:
                wgc_data = game_data['metadata']['wgc']
                additional_gameurls.append('%s@%s' % (wgc_data['application_id']['data'], wgc_data['update_url']['data']))
                purchased_gameids.append(wgc_data['application_id']['data'].split('.')[0])

        showroom_data = await self.__wguscs_get_showroom(additional_gameurls)
        if showroom_data is None:
            logging.error('wgc_api/fetch_product_list: error on retrieving showroom data')
            return product_list

        for product in showroom_data['data']['showcase']:
            #check that instances are exists
            if not product['instances']:
                logging.warn('wgc_api/fetch_product_list: product has no instances %s' % product)
                continue

            #prase game id
            app_gameid = None
            try:
                app_gameid = product['instances'][0]['application_id'].split('.')[0]
            except:
                logging.exception('wgc_api/fetch_product_list: failed to get app_id')

            if app_gameid in GAMES_F2P or app_gameid in purchased_gameids:
                is_purchased = app_gameid in purchased_gameids and app_gameid not in GAMES_F2P
                product_list.append(WGCOwnedApplication(product, is_purchased))
            else:
                logging.warning('wgc_api/fetch_product_list: unknown ID %s' % app_gameid)

        return product_list


    async def __wgcps_fetch_product_list(self):
        if self.__login_info is None:
            logging.error('wgc_auth/__wgcps_fetch_product_list: login info is none')
            return None

        if 'realm' not in self.__login_info:
            logging.error('wgc_auth/__wgcps_fetch_product_list: login info does not contain realm')
            return None

        response = await self.request_post(
            self.__get_url('wgcps', self.__login_info['realm'], self.WGCPS_FETCH_PRODUCT_INFO), 
            json = { 'account_id' : self.get_account_id(), 'country' : self._country_code, 'storefront' : 'wgc_showcase' })

        if response.status == 504:
            logging.warning('wgc_auth/__wgcps_fetch_product_list: failed to get data: gateway timeout')
            return None

        response_content = None
        try:
            response_content = json.loads(response.text)
        except Exception:
            logging.exception('wgc_auth/__wgcps_fetch_product_list: failed for parse json: %s' % response.text)
            return None

        if response.status != 200:
            #{"status": "error", "errors": [{"code": "platform_error", "context": {"result_code": "EXCEPTION"}}, {"code": "retry", "context": {"interval": 30}}]}
            if 'errors' in response_content and response_content['errors'][0]['code'] == 'platform_error':
                logging.warning('wgc_auth/__wgcps_fetch_product_list: platform error: %s' % response.text)
            else:
                logging.error('wgc_auth/__wgcps_fetch_product_list: error on retrieving account info: %s' % response.text)
            return None

        #load additional adata
        response_content['data']['product_content'] = list()
        for product_uri in response_content['data']['product_uris']:
            product_response = await self.request_get(product_uri)
            if product_response.status != 200:
                logging.error('wgc_auth/__wgcps_fetch_product_list: error on retrieving product info: %s' % product_uri)
                continue

            response_content['data']['product_content'].append(json.loads(product_response.text))

        return response_content

    async def __wguscs_get_showroom(self, additional_urls : List[str] = None):
        if self.__login_info is None:
            logging.error('wgc_auth/__wguscs_get_showroom: login info is none')
            return None

        if 'realm' not in self.__login_info:
            logging.error('wgc_auth/__wguscs_get_showroom: login info does not contain realm')
            return None

        additionals = ''
        if additional_urls:     
            additionals = '&showcase_products=' + str.join('&showcase_products=', additional_urls)

        url = self.__get_url('wguscs', self.__login_info['realm'], self.WGUSCS_SHOWROOM)
        url = url + '?lang=%s' % self._language_code.upper()
        url = url + '&gameid=WGC.RU.PRODUCTION&format=json'
        url = url + '&country_code=%s' % self._country_code
        url = url + additionals

        showroom_response = await self.request_get(url)
        
        if showroom_response.status != 200:
            logging.error('wgc_auth/__wguscs_get_showroom: error on retrieving showroom data: %s' % showroom_response.text)
            return None

        return json.loads(showroom_response.text)
