DEBUG = False

from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import json
import os
import random
import string
import sys
import pprint
import threading
from urllib.parse import parse_qs
from typing import Dict, List

from Crypto.Hash import keccak
import requests

from .wgc_application_owned import WGCOwnedApplication
from .wgc_constants import WGCAuthorizationResult, WGCRealms


class WGCAuthorizationServer(BaseHTTPRequestHandler):
    backend = None

    def do_HEAD(self):
        return

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:       
            post_data = parse_qs(post_data)
        except:
            pass

        if self.path == '/login':
            self.do_POST_login(post_data)
        elif self.path == '/2fa':
            self.do_POST_2fa(post_data)
        else:
            self.send_response(302)
            self.send_header('Location','/404')
            self.end_headers()

    def do_POST_login(self, data):

        data_valid = True
        if b'realm' not in data:
            data_valid = False
        if b'email' not in data:
            data_valid = False
        if b'password' not in data:
            data_valid = False

        auth_result = False

        if data_valid:
            try:
                auth_result = self.backend.do_auth_emailpass(
                    data[b'realm'][0].decode("utf-8"),
                    data[b'email'][0].decode("utf-8"),
                    data[b'password'][0].decode("utf-8"))
            except Exception:
                logging.exception("error on doing auth:")
 
        self.send_response(302)
        self.send_header('Content-type', "text/html")
        if auth_result == WGCAuthorizationResult.FINISHED:
            self.send_header('Location','/finished')
        elif auth_result == WGCAuthorizationResult.REQUIRES_2FA:
            self.send_header('Location','/2fa')
        else:
            self.send_header('Location','/login_failed')

        self.end_headers()


    def do_POST_2fa(self, data):
        data_valid = True

        if b'authcode' not in data:
            data_valid = False
        auth_result = False

        use_backup_code = False
        if b'use_backup' in data:
            use_backup_code = True

        if data_valid:
            try:
                auth_result = self.backend.do_auth_2fa(data[b'authcode'][0].decode("utf-8"), use_backup_code)
            except Exception:
                logging.exception("error on doing auth:")
 
        self.send_response(302)

        self.send_header('Content-type', "text/html")
        if auth_result == WGCAuthorizationResult.FINISHED:
            self.send_header('Location','/finished')
        elif auth_result == WGCAuthorizationResult.REQUIRES_2FA:
            self.send_header('Location','/2fa')
        elif auth_result == WGCAuthorizationResult.INCORRECT_2FA or auth_result == WGCAuthorizationResult.INCORRECT_2FA_BACKUP: 
            self.send_header('Location','/2fa_failed')
        else:
            self.send_header('Location','/login_failed')

        self.end_headers()


    def do_GET(self):
        status = 200
        content_type = "text/html"
        response_content = ""

        try:
            filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\%s.html' % self.path)
            if os.path.isfile(filepath):
                response_content = open(filepath).read()
            else:
                filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\404.html')
                if os.path.isfile(filepath):
                    response_content = open(filepath).read()
                else:
                    response_content = 'ERROR: FILE NOT FOUND'

            self.send_response(status)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(bytes(response_content, "UTF-8"))
        except Exception:
            logging.exception('WGCAuthorizationServer/do_GET: error on %s' % self.path)


class WGCApi:
    HTTP_USER_AGENT = 'wgc/19.03.00.5220'

    OAUTH_GRANT_TYPE_BYPASSWORD = 'urn:wargaming:params:oauth:grant-type:basic'
    OAUTH_GRANT_TYPE_BYTOKEN = 'urn:wargaming:params:oauth:grant-type:access-token'
    OUATH_URL_CHALLENGE = '/id/api/v2/account/credentials/create/oauth/token/challenge/'
    OAUTH_URL_TOKEN = '/id/api/v2/account/credentials/create/oauth/token/'
    
    WGNI_URL_ACCOUNTINFO = '/id/api/v2/account/info/'

    WGCPS_FETCH_PRODUCT_INFO = '/platform/api/v1/fetchProductList'
    WGCPS_LOGINSESSION = '/auth/api/v1/loginSession'
    
    WGUSCS_SHOWROOM = '/api/v15/content/showroom/'

    LOCALSERVER_HOST = '127.0.0.1'
    LOCALSERVER_PORT = 13337

    def __init__(self, tracking_id : str = '', country_code : str = '', language_code : str = 'en'):
        self._tracking_id = tracking_id
        self._country_code = country_code
        self._language_code = language_code

        self._server_thread = None
        self._server_object = None

        self._login_info = None
        self._login_info_temp = None

        self._session = requests.Session()
        self._session.headers.update({'User-Agent': self.HTTP_USER_AGENT})
        if DEBUG:
            self._session.verify = False

    # 
    # Getters
    #

    def get_account_id(self) -> int:
        if self._login_info is None:
            logging.error('login info is none')
            return None

        if 'user' not in self._login_info:
            logging.error('login info does not contains user id')
            return None

        return int(self._login_info['user'])

    def get_account_email(self) -> str:
        if self._login_info is None:
            logging.error('login info is none')
            return None

        if 'email' not in self._login_info:
            logging.error('login info does not contains email')
            return None

        return self._login_info['email']

    def get_account_nickname(self) -> str:
        if self._login_info is None:
            logging.error('login info is none')
            return None

        if 'nickname' not in self._login_info:
            logging.error('login info does not contains nickname')
            return None

        return self._login_info['nickname']

        
    def get_account_realm(self) -> str:
        if self._login_info is None:
            logging.error('login info is none')
            return None

        if 'realm' not in self._login_info:
            logging.error('login info does not contains realm')
            return None

        return self._login_info['realm']

    #
    # Authorization server
    #

    def auth_server_uri(self) -> str:
        return 'http://%s:%s/login' % (self.LOCALSERVER_HOST, self.LOCALSERVER_PORT)

    def auth_server_start(self) -> bool:

        if self._server_thread is not None:
            logging.warning('Auth server thread is already running')
            return False

        if self._server_object is not None:
            logging.warning('Auth server object is exists')
            return False

        WGCAuthorizationServer.backend = self
        self._server_object = HTTPServer((self.LOCALSERVER_HOST, self.LOCALSERVER_PORT), WGCAuthorizationServer)
        self._server_thread = threading.Thread(target = self._server_object.serve_forever)
        self._server_thread.daemon = True
        self._server_thread.start()
        return True

    def auth_server_stop(self) -> bool:
        if self._server_object is not None:
            self._server_object.shutdown()
            self._server_object = None
        else:
            logging.warning('Auth server object is not exits')
            return False

        if self._server_thread is not None:
            self._server_thread.join()
            self._server_thread = None
        else:
            logging.warning('Auth server thread is not running')
            return False

    #
    # Login Info
    #

    def login_info_get(self) -> Dict[str,str]:
        return self._login_info

    def login_info_set(self, login_info: Dict[str,str]) -> bool:

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

        self._login_info = login_info
        self.__update_bearer()

        wgni_account_info = self.__wgni_get_account_info()

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

    def do_auth_emailpass(self, realm, email, password) -> WGCAuthorizationResult:
        '''
        Perform authorization using email and password
        '''

        self._session.cookies.clear()
        self._login_info_temp = {'realm': realm, 'email': email, 'password': password}

        challenge_data = self.__oauth_challenge_get(realm)
        if not challenge_data:
            logging.error('Failed to get challenge')
            return WGCAuthorizationResult.FAILED

        #calculate proof of work
        pow_number = self.__oauth_challenge_calculate(challenge_data)
        if not pow_number:
            logging.error('wgc_auth/do_auth_emailpass: failed to calculate challenge')
            return WGCAuthorizationResult.FAILED
        self._login_info_temp['pow_number'] = pow_number

        #try to get token
        token_data_bypassword = self.__oauth_token_get_bypassword(realm, email, password, pow_number)

        #process error
        if token_data_bypassword['status_code'] != 200:
            if 'error_description' in token_data_bypassword:
                if token_data_bypassword['error_description'] == 'twofactor_required':
                    self._login_info_temp['twofactor_token'] = token_data_bypassword['twofactor_token']
                    return WGCAuthorizationResult.REQUIRES_2FA
                elif token_data_bypassword['error_description'] == 'Invalid password parameter value.':
                    return WGCAuthorizationResult.INVALID_LOGINPASS
                elif token_data_bypassword['error_description'] == 'account_not_found':
                    return WGCAuthorizationResult.ACCOUNT_NOT_FOUND

            logging.error('wgc_auth/do_auth_emailpass: failed to request token by email and password: %s' % token_data_bypassword)
            return WGCAuthorizationResult.FAILED

        return self.do_auth_token(realm, email, token_data_bypassword)


    def do_auth_2fa(self, otp_code: str, use_backup_code: bool) -> WGCAuthorizationResult:
        '''
        Submits 2FA answer and continue authorization
        '''

        if 'realm' not in self._login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: realm not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'email' not in self._login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: email not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'password' not in self._login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: password not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'pow_number' not in self._login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: pow number not in stored data')
            return WGCAuthorizationResult.FAILED

        if 'twofactor_token' not in self._login_info_temp:
            logging.error('wgc_auth/do_auth_2fa: twofactor token not in stored data')
            return WGCAuthorizationResult.FAILED

        token_data_byotp = self.__oauth_token_get_bypassword(
            self._login_info_temp['realm'],
            self._login_info_temp['email'],
            self._login_info_temp['password'],
            self._login_info_temp['pow_number'],
            self._login_info_temp['twofactor_token'],
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

        return self.do_auth_token(self._login_info_temp['realm'], self._login_info_temp['email'], token_data_byotp)


    def do_auth_token(self, realm, email, token_data_input) -> WGCAuthorizationResult:
        '''
        Second step of authorization in case if you already logged in via emailpass or 2FA
        '''

        token_data_bytoken = self.__oauth_token_get_bytoken(realm, token_data_input)
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
        self._login_info = login_info

        #update bearer
        self.__update_bearer()

        #get additinal info from WGNI
        wgni_account_info = self.__wgni_get_account_info()
        logging.info(wgni_account_info)
        self._login_info['nickname'] = wgni_account_info['nickname']

        return WGCAuthorizationResult.FINISHED


    def __update_bearer(self):
        if self._login_info is None:
            logging.error('wgc_auth/update_bearer: login info is none')
            return None

        if 'access_token' not in self._login_info:
            logging.error('wgc_auth/update_bearer: login info does not contain access token')
            return None

        if 'exchange_code' not in self._login_info:
            logging.error('wgc_auth/update_bearer: login info does not contain exchange code')
            return None

        self._session.headers.update({'Authorization':'Bearer %s:%s' % (self._login_info['access_token'], self._login_info['exchange_code'])})

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

    def __oauth_challenge_get(self, realm):
        r = self._session.get(self.__get_url('wgnet', realm, self.OUATH_URL_CHALLENGE))
        if r.status_code != 200:
            logging.error('wgc_auth/oauth_challenge_get: error %s, content: %s' % (r.status_code, r.text))
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
            keccak_hash = keccak.new(digest_bits=512)
            keccak_hash.update(hashcash_str+str(pow_number).encode('utf-8'))
            digest = keccak_hash.hexdigest()

            if digest.startswith(prefix):
                return pow_number

            pow_number = pow_number + 1

    def __oauth_token_get_bypassword(self, realm, email, password, pow_number, twofactor_token : str = None, otp_code : str = None, use_backup_code : bool = False):
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

        response = self._session.post(self.__get_url('wgnet', realm, self.OAUTH_URL_TOKEN), data = body)
        while response.status_code == 202:
            response = self._session.get(response.headers['Location'])
        
        text = None
        try:
            text = json.loads(response.text)
        except Exception:
            logging.exception('wgc_api/__oauth_token_get_bypassword: failed to parse response')
            return None

        text['status_code'] = response.status_code
        return text

    def __oauth_token_get_bytoken(self, realm, token_data):
        body = dict()
        body['access_token'] = token_data['access_token']
        body['grant_type'] = self.OAUTH_GRANT_TYPE_BYTOKEN
        body['client_id'] = self.__oauth_get_clientid(realm)
        body['exchange_code'] = ''.join(random.choices(string.digits+'ABCDEF', k=32))
        body['tid'] = self._tracking_id

        r = self._session.post(self.__get_url('wgnet', realm, self.OAUTH_URL_TOKEN), data = body)
        if r.status_code != 202:
            return None

        r2 = self._session.get(r.headers['Location'])
        if r2.status_code != 200:
            return None

        result = json.loads(r2.text)
        result['exchange_code'] = body['exchange_code']

        return result

    #
    # Account info
    #

    def __wgni_get_account_info(self):
        if self._login_info is None:
            logging.error('wgc_auth/wgni_get_account_info: login info is none')
            return None

        if 'realm' not in self._login_info:
            logging.error('wgc_auth/wgni_get_account_info: login info does not contain realm')
            return None

        response = self._session.post(
            self.__get_url('wgnet', self._login_info['realm'], self.WGNI_URL_ACCOUNTINFO), 
            data = { 'fields' : 'nickname' })
      
        while response.status_code == 202:
            response = self._session.get(response.headers['Location'])
        
        if response.status_code != 200:
            logging.error('wgc_auth/wgni_get_account_info: error on retrieving account info: %s' % response.text)
            return None

        return json.loads(response.text)

    #
    # Fetch product list
    #

    def fetch_product_list(self) -> List[WGCOwnedApplication]:
        product_list = list()

        additional_gameurls = list()
        for game_data in self.__wgcps_fetch_product_list()['data']['product_content']:
            wgc_data = game_data['metadata']['wgc']
            additional_gameurls.append('%s@%s' % (wgc_data['application_id']['data'], wgc_data['update_url']['data']))

        showroom_data = self.__wguscs_get_showroom(additional_gameurls)
        if showroom_data is None:
            logging.error('wgc_api/fetch_product_list: error on retrieving showroom data')
            return product_list

        for product in showroom_data['showcase']:
            product_list.append(WGCOwnedApplication(product))

        return product_list


    def __wgcps_fetch_product_list(self):
        if self._login_info is None:
            logging.error('wgc_auth/__wgcps_fetch_product_list: login info is none')
            return None

        if 'realm' not in self._login_info:
            logging.error('wgc_auth/__wgcps_fetch_product_list: login info does not contain realm')
            return None

        response = self._session.post(
            self.__get_url('wgcps', self._login_info['realm'], self.WGCPS_FETCH_PRODUCT_INFO), 
            json = { 'account_id' : self.get_account_id(), 'country' : self._country_code, 'storefront' : 'wgc_showcase' })
      
        while response.status_code == 202:
            response = self._session.get(response.headers['Location'])
        
        if response.status_code != 200:
            logging.error('wgc_auth/__wgcps_fetch_product_list: error on retrieving account info: %s' % response.text)
            return None

        response_content = json.loads(response.text)

        #load additional adata
        response_content['data']['product_content'] = list()
        for product_uri in response_content['data']['product_uris']:
            product_response = self._session.get(product_uri)
            if response.status_code != 200:
                logging.error('wgc_auth/__wgcps_fetch_product_list: error on retrieving product info: %s' % product_uri)
                continue

            response_content['data']['product_content'].append(json.loads(product_response.text))

        return response_content


    def __wguscs_get_showroom(self, additional_urls : List[str] = None):
        if self._login_info is None:
            logging.error('wgc_auth/__wguscs_get_showroom: login info is none')
            return None

        if 'realm' not in self._login_info:
            logging.error('wgc_auth/__wguscs_get_showroom: login info does not contain realm')
            return None

        additionals = ''
        if additional_urls:     
            additionals = '&showcase_products=' + str.join('&showcase_products=', additional_urls)

        url = self.__get_url('wguscs', self._login_info['realm'], self.WGUSCS_SHOWROOM)
        url = url + '?lang=%s' % self._language_code.upper()
        url = url + '&gameid=WGC.RU.PRODUCTION&format=json'
        url = url + '&country_code=%s' % self._country_code
        url = url + additionals

        showroom_response = self._session.get(url)
        
        if showroom_response.status_code != 200:
            logging.error('wgc_auth/__wguscs_get_showroom: error on retrieving showroom data: %s' % response.text)
            return None

        return json.loads(showroom_response.text)
