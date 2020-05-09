# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import asyncio
import json
import logging
import random
import string
from typing import Dict

from .wgc_constants import WGCAuthorizationResult, WGCRealms
from .wgc_http import WgcHttp
from .wgc_keccak import Keccak512

class WgcWgni:
    '''
    Wargaming Network Identity
    '''
    
    OAUTH_GRANT_TYPE_BYPASSWORD = 'urn:wargaming:params:oauth:grant-type:basic'
    OAUTH_GRANT_TYPE_BYTOKEN = 'urn:wargaming:params:oauth:grant-type:access-token'
    OUATH_URL_CHALLENGE = '/id/api/v2/account/credentials/create/oauth/token/challenge/'
    OAUTH_URL_TOKEN = '/id/api/v2/account/credentials/create/oauth/token/'

    WGNI_URL_TOKEN1 = '/id/api/v2/account/credentials/create/token1/'
    WGNI_URL_ACCOUNTINFO = '/id/api/v2/account/info/'

    def __init__(self, http : WgcHttp, tracking_id : str = ''):
        self.__logger = logging.getLogger('wgc_auth')

        self.__http = http

        self.__tracking_id = tracking_id

        self.__login_info = None
        self.__login_info_temp = None
 
    async def shutdown(self):
        pass

    #
    # Account Info Storage
    #

    def get_account_id(self) -> int:
        if self.__login_info is None:
            self.__logger.error('get_account_id: login info is none')
            return None

        if 'user' not in self.__login_info:
            self.__logger.error('get_account_id: login info does not contains user id')
            return None

        return int(self.__login_info['user'])

    def get_account_email(self) -> str:
        if self.__login_info is None:
            self.__logger.error('get_account_email: login info is none')
            return None

        if 'email' not in self.__login_info:
            self.__logger.error('get_account_email: login info does not contains email')
            return None

        return self.__login_info['email']

    def get_account_nickname(self) -> str:
        if self.__login_info is None:
            self.__logger.error('get_account_nickname: login info is none')
            return None

        if 'nickname' not in self.__login_info:
            self.__logger.error('get_account_nickname: login info does not contains nickname')
            return None

        return self.__login_info['nickname']
        
    def get_account_realm(self) -> str:
        if self.__login_info is None:
            self.__logger.error('get_account_realm: login info is none')
            return None

        if 'realm' not in self.__login_info:
            self.__logger.error('get_account_realm: login info does not contains realm')
            return None

        return self.__login_info['realm']


    def login_info_get(self) -> Dict[str,str]:
        return self.__login_info

    async def login_info_set(self, login_info: Dict[str,str]) -> bool:

        if login_info is None:
            self.__logger.error('login_info_set: login info is none')
            return False

        if 'realm' not in login_info:
            self.__logger.error('login_info_set: realm is missing')
            return False

        if 'access_token' not in login_info:
            self.__logger.error('login_info_set: access token is missing')
            return False

        if 'exchange_code' not in login_info:
            self.__logger.error('login_info_set: exchange code is missing')
            return False

        if 'email' not in login_info:
            self.__logger.error('login_info_set: email')
            return False

        if 'user' not in login_info:
            self.__logger.error('login_info_set: user is missing')
            return False

        self.__login_info = login_info
        self.__update_bearer()

        wgni_account_info = await self.__request_account_info()

        if wgni_account_info is None:
            self.__logger.error('login_info_set: failed to get account info')
            return False

        if wgni_account_info['sub'] != login_info['user']:
            self.__logger.error('login_info_set: SPA ID missmatch')
            return False
        
        return True

    #
    # Account info
    #

    async def __request_account_info(self):
        if self.__login_info is None:
            self.__logger.error('__request_account_info: login info is none')
            return None

        if 'realm' not in self.__login_info:
            self.__logger.error('__request_account_info: login info does not contain realm')
            return None

        response = await self.__http.request_post_simple(
            'wgnet', self.__login_info['realm'], self.WGNI_URL_ACCOUNTINFO, 
            data = { 'fields' : 'nickname' })
        
        if response.status != 200:
            self.__logger.error('__request_account_info: error on retrieving account info: %s' % response.text)
            return None

        return json.loads(response.text)


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
            self.__logger.error('do_auth_emailpass: failed to get challenge')
            return WGCAuthorizationResult.FAILED

        #calculate proof of work
        pow_number = self.__oauth_challenge_calculate(challenge_data)
        if not pow_number:
            self.__logger.error('do_auth_emailpass: failed to calculate challenge')
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
                elif token_data_bypassword['error_description'] == 'Invalid username parameter value.':
                    return WGCAuthorizationResult.INVALID_LOGINPASS
                elif token_data_bypassword['error_description'] == 'Invalid password parameter value.':
                    return WGCAuthorizationResult.INVALID_LOGINPASS
                elif token_data_bypassword['error_description'] == 'Request is missing password parameter.':
                    return WGCAuthorizationResult.INVALID_LOGINPASS
                elif token_data_bypassword['error_description'] == 'account_not_found':
                    return WGCAuthorizationResult.ACCOUNT_NOT_FOUND

            self.__logger.error('do_auth_emailpass: failed to request token by email and password: %s' % token_data_bypassword)
            return WGCAuthorizationResult.FAILED

        return await self.do_auth_token(realm, email, token_data_bypassword)


    async def do_auth_2fa(self, otp_code: str, use_backup_code: bool) -> WGCAuthorizationResult:
        '''
        Submits 2FA answer and continue authorization
        '''

        if 'realm' not in self.__login_info_temp:
            self.__logger.error('do_auth_2fa: realm not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'email' not in self.__login_info_temp:
            self.__logger.error('do_auth_2fa: email not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'password' not in self.__login_info_temp:
            self.__logger.error('do_auth_2fa: password not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'pow_number' not in self.__login_info_temp:
            self.__logger.error('do_auth_2fa: pow number not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'twofactor_token' not in self.__login_info_temp:
            self.__logger.error('do_auth_2fa: twofactor token not in stored data')
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
                if error_desc == 'twofactor_invalid':
                    return WGCAuthorizationResult.INCORRECT_2FA
                elif error_desc == 'Invalid otp_code parameter value.':
                    return WGCAuthorizationResult.INCORRECT_2FA
                elif error_desc == 'Invalid twofactor token.':
                    return WGCAuthorizationResult.INCORRECT_2FA
                if error_desc == 'Invalid backup_code parameter value.':
                    return WGCAuthorizationResult.INCORRECT_2FA_BACKUP
            
            self.__logger.error('do_auth_2fa: failed to request token by email, password and OTP: %s' % token_data_byotp)
            return WGCAuthorizationResult.FAILED

        return await self.do_auth_token(self.__login_info_temp['realm'], self.__login_info_temp['email'], token_data_byotp)


    async def do_auth_token(self, realm, email, token_data_input) -> WGCAuthorizationResult:
        '''
        Second step of authorization in case if you already logged in via emailpass or 2FA
        '''

        token_data_bytoken = await self.__oauth_token_get_bytoken(realm, token_data_input)
        if not token_data_bytoken:
            self.__logger.error('do_auth_token: failed to request token by token')
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
        wgni_account_info = await self.__request_account_info()
        self.__login_info['nickname'] = wgni_account_info['nickname']

        return WGCAuthorizationResult.FINISHED


    #
    # OAuth
    #

    def __oauth_get_clientid(self, realm):
        '''
        get OAuth client ID
        '''
        realm = realm.upper()

        try:
            return WGCRealms[realm]['client_id']
        except Exception:
            self.__logger.exception('__get_oauth_clientid: failed to get client Id for realm %s' % realm)
            return None


    async def __oauth_challenge_get(self, realm):
        '''
        request authentication challenge and return proof-of-work
        '''
        r = await self.__http.request_get_simple('wgnet', realm, self.OUATH_URL_CHALLENGE)
        if r.status != 200:
            self.__logger.error('__oauth_challenge_get: error %s, content: %s' % (r.status, r.text))
            return None

        return json.loads(r.text)['pow']


    def __oauth_challenge_calculate(self, challenge_data):
        '''
        calculates solution for proof-of-work challenge
        '''

        if challenge_data['algorithm']['name'] != 'hashcash' :
            self.__logger.error('__oauth_challenge_calculate: unknown proof-of-work algorithm')
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
            keccak_hash = Keccak512()
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
        body['tid'] = self.__tracking_id
        body['pow'] = pow_number
        if twofactor_token is not None:
            body['twofactor_token'] = twofactor_token
        if otp_code is not None:
            if use_backup_code:
                body['backup_code'] = otp_code
            else:
                body['otp_code'] = otp_code

        response = await self.__http.request_post_simple('wgnet', realm, self.OAUTH_URL_TOKEN, data = body)
        
        result = None
        try:
            result = json.loads(response.text)
        except Exception:
            self.__logger.exception('__oauth_token_get_bypassword: failed to parse response %s' % response.text)
            return result

        result['status_code'] = response.status
        return result


    async def __oauth_token_get_bytoken(self, realm, token_data):
        body = dict()
        body['access_token'] = token_data['access_token']
        body['grant_type'] = self.OAUTH_GRANT_TYPE_BYTOKEN
        body['client_id'] = self.__oauth_get_clientid(realm)
        body['exchange_code'] = ''.join(random.choices(string.digits+'ABCDEF', k=32))
        body['tid'] = self.__tracking_id

        response = await self.__http.request_post_simple('wgnet', realm, self.OAUTH_URL_TOKEN, data = body)

        if response.status != 200:
            self.__logger.error('__oauth_token_get_bytoken: error on receiving token by token: %s because status is %s' % (response.text, response.status))
            return None

        result = json.loads(response.text)
        result['exchange_code'] = body['exchange_code']

        return result


    #
    # Token1
    #

    async def create_token1(self, requested_for : str) -> str:
        #validate login info
        if self.__login_info is None:
            self.__logger.error('create_token1: login info is none')
            return None

        if 'realm' not in self.__login_info:
            self.__logger.error('create_token1: login info does not contain realm')
            return None

        if 'access_token' not in self.__login_info:
            self.__logger.error('create_token1: login info does not contain access_token')
            return None

        #send request
        response = await self.__http.request_post_simple(
            'wgnet', self.__login_info['realm'], self.WGNI_URL_TOKEN1, 
            data = { 'requested_for' : requested_for, 'access_token' : self.__login_info['access_token'] })

        #parse data
        if response.status != 200:
            self.__logger.error('create_token1: error on retrieving token1: %s, %s' % (response.status, response.text))
            return None

        content = json.loads(response.text)
        if content is None:
            self.__logger.error('create_token1: failed parse token1 response (%s, %s)' % (requested_for, response.text))
            return None

        if 'token' not in content:
            self.__logger.error('create_token1: server response for %s does not contains token: %s' % (requested_for, content))
            return None

        return content['token']


    #
    # Other
    #

    def __update_bearer(self):
        if self.__login_info is None:
            self.__logger.error('__update_bearer: login info is none')
            return None

        if 'access_token' not in self.__login_info:
            self.__logger.error('__update_bearer: login info does not contain access token')
            return None

        if 'exchange_code' not in self.__login_info:
            self.__logger.error('__update_bearer: login info does not contain exchange code')
            return None

        self.__http.update_headers({'Authorization':'Bearer %s:%s' % (self.__login_info['access_token'], self.__login_info['exchange_code'])})

