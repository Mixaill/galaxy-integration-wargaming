# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

from collections import namedtuple
import json
import logging
import os
import platform
import pprint

import ssl
import sys
import threading
from typing import Any, Dict, List
from urllib.parse import parse_qs

import asyncio

from .wgc_application_owned import WGCOwnedApplication
from .wgc_constants import WGCIds, WGCAuthorizationResult, WGCRealms, GAMES_F2P
from .wgc_http import WgcHttp
from .wgc_wgni import WgcWgni

class WgcApi:

    WGCPS_FETCH_PRODUCT_INFO = '/platform/api/v1/fetchProductList'
    WGCPS_LOGINSESSION = '/auth/api/v1/loginSession'
    
    WGUSCS_SHOWROOM = '/api/v18/content/showroom/'
    
    WGUS_METADATA = '/api/v1/metadata'
    
    WGC_PUBLISHER_ID = 'wargaming'

    def __init__(self, http : WgcHttp, wgni : WgcWgni, country_code : str = '', language_code : str = 'en'):
        self.__logger = logging.getLogger('wgc_api')

        self.__http = http
        self.__wgni = wgni

        self._country_code = country_code
        self._language_code = language_code

    async def shutdown(self):
        pass

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
            self.__logger.error('fetch_product_list: error on retrieving showroom data')
            return product_list

        for product in showroom_data['data']['showcase']:
            #check that instances are exists
            if not product['instances']:
                self.__logger.warn('fetch_product_list: product has no instances %s' % product)
                continue

            #prase game id
            app_gameid = None
            try:
                app_gameid = product['instances'][0]['application_id'].split('.')[0]
            except:
                self.__logger.exception('fetch_product_list: failed to get app_id')

            if app_gameid in GAMES_F2P or app_gameid in purchased_gameids:
                is_purchased = app_gameid in purchased_gameids and app_gameid not in GAMES_F2P
                product_list.append(WGCOwnedApplication(product, is_purchased, self))
            else:
                self.__logger.warning('fetch_product_list: unknown ID %s' % app_gameid)

        return product_list

    async def __wgcps_fetch_product_list(self):
        response = await self.__http.request_post_simple(
            'wgcps', self.__wgni.get_account_realm(), self.WGCPS_FETCH_PRODUCT_INFO, 
            json = { 'account_id' : self.__wgni.get_account_id(), 'country' : self._country_code, 'storefront' : 'wgc_showcase' })

        if response.status == 502:
            self.__logger.warning('__wgcps_fetch_product_list: failed to get data: bad gateway')
            return None

        if response.status == 504:
            self.__logger.warning('__wgcps_fetch_product_list: failed to get data: gateway timeout')
            return None

        response_content = None
        try:
            response_content = json.loads(response.text)
        except Exception:
            self.__logger.exception('__wgcps_fetch_product_list: failed for parse json: %s' % response.text)
            return None

        if response.status != 200:
            #{"status": "error", "errors": [{"code": "platform_error", "context": {"result_code": "EXCEPTION"}}, {"code": "retry", "context": {"interval": 30}}]}
            if 'errors' in response_content and response_content['errors'][0]['code'] == 'platform_error':
                self.__logger.warning('__wgcps_fetch_product_list: platform error: %s' % response.text)
            else:
                self.__logger.error('__wgcps_fetch_product_list: error on retrieving account info: %s' % response.text)
            return None

        #load additional adata
        response_content['data']['product_content'] = list()
        for product_uri in response_content['data']['product_uris']:
            product_response = await self.__http.request_get(product_uri)
            if product_response.status != 200:
                self.__logger.error('__wgcps_fetch_product_list: error on retrieving product info: %s' % product_uri)
                continue

            response_content['data']['product_content'].append(json.loads(product_response.text))

        return response_content

    async def __wguscs_get_showroom(self, additional_urls : List[str] = None):
        additionals = ''
        if additional_urls:     
            additionals = '&showcase_products=' + str.join('&showcase_products=', additional_urls)

        url = self.__http.get_url('wguscs', self.__wgni.get_account_realm(), self.WGUSCS_SHOWROOM)
        url = url + '?lang=%s' % self._language_code.upper()
        url = url + '&gameid=%s' % WGCIds[self.__wgni.get_account_realm()]
        url = url + '&wgc_publisher_id=%s' % WgcApi.WGC_PUBLISHER_ID
        url = url + '&format=json'
        url = url + '&country_code=%s' % self._country_code
        url = url + additionals

        showroom_response = await self.__http.request_get(url)
        
        if showroom_response.status != 200:
            self.__logger.error('__wguscs_get_showroom: error on retrieving showroom data: %s' % showroom_response.text)
            return None

        return json.loads(showroom_response.text)

    #
    # Metadata download
    # 

    async def fetch_app_metadata(self, update_server: str, app_id: str) -> str:
        url = '%s/%s/?guid=%s&chain_id=unknown&protocol_version=6.4' % (update_server, self.WGUS_METADATA, app_id)
        
        response = await self.__http.request_get(url) 
        if response.status != 200:
            self.__logger.error('fetch_app_metadata: error on retrieving showroom data: (%s, %s)' % (url, response.text))
            return None

        return response.text
