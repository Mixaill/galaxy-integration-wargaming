import hashlib
import json
import os
import sys
import pprint

#add 3rdparty to sys
trdparty =  os.path.join(os.getcwd(),'3rdparty\\')
if trdparty not in sys.path:
    sys.path.insert(0, trdparty)

#import 3rdparty    
from Crypto.Hash import keccak
import requests

class WGCAuthorization:
    API_VERSION = 'v2'
    URL_OAUTH_CHALLENGE = '/account/credentials/create/oauth/token/challenge/'
    URL_OAUTH_TOKEN = '/account/credentials/create/oauth/token/'
    USER_AGENT = 'wgc/19.03.00.5220'
    CLIENT_ID = '77cxLwtEJ9uvlcm2sYe4O8viIIWn1FEWlooMTTqF'

    def __init__(self, realm, tracking_id = ''):
        self._tracking_id = tracking_id

        self._realm = realm.upper()
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': self.USER_AGENT})

    def do_auth(self, email, password):
        challenge_data = self.__create_challenge()
        if not challenge_data:
            print('ERROR: failed to create challenge')
            return False

        pow_number = self.__calculate_pow(challenge_data)

        if not self.__request_token_emailpass(email, password, pow_number):
            print('ERROR: failed to request token')
            return False

        return True

    def __get_server(self):
        if self._realm == 'RU':
            return 'https://ru.wargaming.net'
        if self._realm == 'EU':
            return 'https://eu.wargaming.net'
        if self._realm == 'NA':
            return 'https://na.wargaming.net'
        if self._realm == 'ASIA':
            return 'https://asia.wargaming.net'

    def __create_link(self, link):
        return self.__get_server() + '/id/api/' + self.API_VERSION + link

    def __create_challenge(self):
        r = self._session.get(self.__create_link(self.URL_OAUTH_CHALLENGE), verify=False)
        if r.status_code != 200:
           return None

        results = dict()
        content = json.loads(r.text)['pow']
        results['timestamp'] = content['timestamp']
        results['complexity'] = content['complexity']
        results['random_string'] = content['random_string']
        results['resourse'] = content['algorithm']['resourse']
        results['extension'] = content['algorithm']['extension']
        results['version'] = content['algorithm']['version']
        return results
        
    def __calculate_pow(self, challenge_data):
        prefix = '0' * challenge_data['complexity']
        hashcash_str = '%s:%s:%s:%s:%s:%s:' % (challenge_data['version'], challenge_data['complexity'], challenge_data['timestamp'], challenge_data['resourse'], challenge_data['extension'], challenge_data['random_string'])
        hashcash_str = hashcash_str.encode('utf-8')

        pow_number = 0
        while True:
            keccak_hash = keccak.new(digest_bits=512)
            keccak_hash.update(hashcash_str+str(pow_number).encode('utf-8'))
            digest = keccak_hash.hexdigest()

            if digest.startswith(prefix):
                return pow_number

            pow_number = pow_number + 1

    def __request_token_emailpass(self, email, password, pow_number):
        body = dict()
        body['username'] = email
        body['password'] = password
        body['grant_type'] = 'urn:wargaming:params:oauth:grant-type:basic'
        body['client_id'] = self.CLIENT_ID
        body['tid'] = self._tracking_id
        body['pow'] = pow_number

        r = self._session.post(self.__create_link(self.URL_OAUTH_TOKEN), data = body)
        if r.status_code != 202:
            return False

        r2 = self._session.get(r.headers['Location'])
        if r2.status_code != 200:
            return False

        return True
