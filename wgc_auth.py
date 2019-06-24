import hashlib
import logging
import json
import os
import sys
import pprint

#expand sys.path
thirdparty =  os.path.join(os.path.dirname(os.path.realpath(__file__)),'3rdparty\\')
if thirdparty not in sys.path:
    sys.path.insert(0, thirdparty)

#import 3rdparty    
from Crypto.Hash import keccak
import requests

class WGCAuthorization:
    HTTP_USER_AGENT = 'wgc/19.03.00.5220'

    OAUTH_CLIENT_ID = '77cxLwtEJ9uvlcm2sYe4O8viIIWn1FEWlooMTTqF'
    OAUTH_EXCHANGE_CODE = 'E6F15EBD8EC89D29DB79534D0F15EE4C'
    OAUTH_GRANT_TYPE_BYPASSWORD = 'urn:wargaming:params:oauth:grant-type:basic'
    OAUTH_GRANT_TYPE_BYTOKEN = 'urn:wargaming:params:oauth:grant-type:access-token'
    OUATH_URL_CHALLENGE = '/id/api/v2/account/credentials/create/oauth/token/challenge/'
    OAUTH_URL_TOKEN = '/id/api/v2/account/credentials/create/oauth/token/'

    def __init__(self, realm, tracking_id = ''):
        self._tracking_id = tracking_id

        self._realm = realm.upper()
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': self.HTTP_USER_AGENT})

    def do_auth(self, email, password):
        challenge_data = self.__oauth_challenge_get()
        if not challenge_data:
            logging.error('Failed to get challenge')
            return False

        pow_number = self.__oauth_challenge_calculate(challenge_data)
        if not pow_number:
            logging.error('Failed to calculate challenge')
            return False

        token_data_bypassword = self.__oauth_token_get_bypassword(email, password, pow_number)
        if not token_data_bypassword:
            logging.error('Failed to request token by email and password')
            return False

        token_data_bytoken = self.__oauth_token_get_bytoken(token_data_bypassword)
        if not token_data_bytoken:
            logging.error('Failed to request token by token')
            return False

        self._token_data = token_data_bytoken
        pprint.pprint(token_data_bytoken)
        return True

    def __get_url(self, url):
        if self._realm == 'RU':
            return 'https://ru.wargaming.net' + url
        if self._realm == 'EU':
            return 'https://eu.wargaming.net' + url
        if self._realm == 'NA':
            return 'https://na.wargaming.net' + url
        if self._realm == 'ASIA':
            return 'https://asia.wargaming.net' + url

        return None

    def __oauth_challenge_get(self):
        r = self._session.get(self.__get_url(self.OUATH_URL_CHALLENGE))
        if r.status_code != 200:
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

    def __oauth_token_get_bypassword(self, email, password, pow_number):
        body = dict()
        body['username'] = email
        body['password'] = password
        body['grant_type'] = self.OAUTH_GRANT_TYPE_BYPASSWORD
        body['client_id'] = self.OAUTH_CLIENT_ID
        body['tid'] = self._tracking_id
        body['pow'] = pow_number

        r = self._session.post(self.__get_url(self.OAUTH_URL_TOKEN), data = body)
        if r.status_code != 202:
            return None

        r2 = self._session.get(r.headers['Location'])
        if r2.status_code != 200:
            return None

        return json.loads(r2.text)

    def __oauth_token_get_bytoken(self, token_data):
        body = dict()
        body['access_token'] = token_data['access_token']
        body['grant_type'] = self.OAUTH_GRANT_TYPE_BYTOKEN
        body['client_id'] = self.OAUTH_CLIENT_ID
        body['exchange_code'] = self.OAUTH_EXCHANGE_CODE
        body['tid'] = self._tracking_id

        r = self._session.post(self.__get_url(self.OAUTH_URL_TOKEN), data = body)
        if r.status_code != 202:
            return None

        r2 = self._session.get(r.headers['Location'])
        if r2.status_code != 200:
            return None

        return json.loads(r2.text)