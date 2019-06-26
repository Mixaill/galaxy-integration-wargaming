from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import json
import os
import sys
import pprint
import threading
from urllib.parse import parse_qs

#expand sys.path
thirdparty = os.path.join(os.path.dirname(os.path.realpath(__file__)),'3rdparty\\')
if thirdparty not in sys.path:
    sys.path.insert(0, thirdparty)

#import 3rdparty    
from Crypto.Hash import keccak
import requests

class WGCAuthorizationServer(BaseHTTPRequestHandler):
    backend = None

    def do_HEAD(self):
        return

    def do_POST(self):
        #get post data
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
            
        data = parse_qs(post_data)
        data_valid = True

        if b'realm' not in data:
            data_valid = False

        if b'email' not in data:
            data_valid = False

        if b'password' not in data:
            data_valid = False

        auth_result = False

        if data_valid:
            auth_result = self.backend.do_auth(
                data[b'realm'][0].decode("utf-8"),
                data[b'email'][0].decode("utf-8"),
                data[b'password'][0].decode("utf-8"))
 
        self.send_response(302)
        self.send_header('Content-type', "text/html")
        if auth_result:
            self.send_header('Location','/finished')
        else:
            self.send_header('Location','/login_failed')

        self.end_headers()

    def do_GET(self):
        status = 200
        content_type = "text/html"
        response_content = ""

        filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\%s.html' % self.path)
        if os.path.isfile(filepath):
            response_content = open(filepath).read()
        else:
            filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)),'html\\404.html')
            response_content = open(filepath).read()

        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.end_headers()
        self.wfile.write(bytes(response_content, "UTF-8"))


class WGCAuthorization:
    HTTP_USER_AGENT = 'wgc/19.03.00.5220'

    OAUTH_CLIENT_ID = '77cxLwtEJ9uvlcm2sYe4O8viIIWn1FEWlooMTTqF'
    OAUTH_EXCHANGE_CODE = 'E6F15EBD8EC89D29DB79534D0F15EE4C'
    OAUTH_GRANT_TYPE_BYPASSWORD = 'urn:wargaming:params:oauth:grant-type:basic'
    OAUTH_GRANT_TYPE_BYTOKEN = 'urn:wargaming:params:oauth:grant-type:access-token'
    OUATH_URL_CHALLENGE = '/id/api/v2/account/credentials/create/oauth/token/challenge/'
    OAUTH_URL_TOKEN = '/id/api/v2/account/credentials/create/oauth/token/'

    WGCPS_LOGINSESSION = '/auth/api/v1/loginSession'

    LOCALSERVER_HOST = '127.0.0.1'
    LOCALSERVER_PORT = 13337

    def __init__(self, tracking_id = ''):
        self._tracking_id = tracking_id
        self._server_thread = None
        self._server_object = None

        self._login_info = None

        self._session = requests.Session()
        self._session.headers.update({'User-Agent': self.HTTP_USER_AGENT})

    # 
    # Getters
    #

    def get_account_id(self):
        if self._login_info is None:
            logging.error('login info is none')
            return None

        if 'user' not in self._login_info:
            logging.error('login info does not contains user id')
            return None

        return self._login_info['user']

    def get_account_email(self):
        if self._login_info is None:
            logging.error('login info is none')
            return None

        if 'email' not in self._login_info:
            logging.error('login info does not contains email')
            return None

        return self._login_info['email']

    #
    # Authorization server
    #

    def auth_server_start(self):

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

    def auth_server_stop(self):
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

    def login_info_get(self):
        return self._login_info

    def login_info_set(self, login_info):
        if 'realm' not in login_info:
            return False

        if 'access_token' not in login_info:
            return False

        if 'email' not in login_info:
            return False

        if 'user' not in login_info:
            return False

        r = self._session.get(self.__get_url('wgcps', login_info['realm'], self.WGCPS_LOGINSESSION), headers = {'Authorization':'Bearer %s' % login_info['access_token']})
        if r.status_code != 200:
            return False

        rj = json.loads(r.text)
        if rj['status'] == 'ok':
            self._login_info = login_info
            return True

        return False

    #
    # Authorization routine
    # 

    def do_auth(self, realm, email, password):

        challenge_data = self.__oauth_challenge_get(realm)
        if not challenge_data:
            logging.error('Failed to get challenge')
            return False

        pow_number = self.__oauth_challenge_calculate(challenge_data)
        if not pow_number:
            logging.error('Failed to calculate challenge')
            return False

        token_data_bypassword = self.__oauth_token_get_bypassword(realm, email, password, pow_number)
        if not token_data_bypassword:
            logging.error('Failed to request token by email and password')
            return False

        token_data_bytoken = self.__oauth_token_get_bytoken(realm, token_data_bypassword)
        if not token_data_bytoken:
            logging.error('Failed to request token by token')
            return False

        #generate login info
        login_info = dict()
        login_info['realm'] = realm
        login_info['email'] = email
        login_info['user'] = token_data_bytoken['user']
        login_info['access_token'] = token_data_bytoken['access_token']
        self._login_info = login_info

        return True

    #
    # URL formatting
    #

    def __get_url(self, ltype, realm, url):
        realm = realm.upper()

        if ltype == 'wgnet':
            if realm == 'RU':
                return 'https://ru.wargaming.net' + url
            if realm == 'EU':
                return 'https://eu.wargaming.net' + url
            if realm == 'NA':
                return 'https://na.wargaming.net' + url
            if realm == 'ASIA':
                return 'https://asia.wargaming.net' + url

        if ltype == 'wgcps':
            if realm == 'RU':
                return 'https://wgcps-ru.wargaming.net' + url
            if realm == 'EU':
                return 'https://wgcps-eu.wargaming.net' + url
            if realm == 'NA':
                return 'https://wgcps-na.wargaming.net' + url
            if realm == 'ASIA':
                return 'https://wgcps-asia.wargaming.net' + url

        logging.error('Failed to specify link')
        return None

    #
    # OAuth
    #

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

    def __oauth_token_get_bypassword(self, realm, email, password, pow_number):
        body = dict()
        body['username'] = email
        body['password'] = password
        body['grant_type'] = self.OAUTH_GRANT_TYPE_BYPASSWORD
        body['client_id'] = self.OAUTH_CLIENT_ID
        body['tid'] = self._tracking_id
        body['pow'] = pow_number

        r = self._session.post(self.__get_url('wgnet', realm, self.OAUTH_URL_TOKEN), data = body)
        if r.status_code != 202:
            logging.error('wgc_auth/oauth_token_get_bypassword: error 1-%s, content: %s' % (r.status_code, r.text))
            return None

        r2 = self._session.get(r.headers['Location'])
        if r2.status_code != 200:
            logging.error('wgc_auth/oauth_token_get_bypassword: error 2-%s, content: %s' % (r2.status_code, r2.text))
            return None

        return json.loads(r2.text)

    def __oauth_token_get_bytoken(self, realm, token_data):
        body = dict()
        body['access_token'] = token_data['access_token']
        body['grant_type'] = self.OAUTH_GRANT_TYPE_BYTOKEN
        body['client_id'] = self.OAUTH_CLIENT_ID
        body['exchange_code'] = self.OAUTH_EXCHANGE_CODE
        body['tid'] = self._tracking_id

        r = self._session.post(self.__get_url('wgnet', realm, self.OAUTH_URL_TOKEN), data = body)
        if r.status_code != 202:
            return None

        r2 = self._session.get(r.headers['Location'])
        if r2.status_code != 200:
            return None

        return json.loads(r2.text)

