# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import json
import logging
from typing import Dict, List

import aiohttp

from .wgc_constants import PAPI_WGNET_REALMS
from .wgc_spa import sort_by_realms

class PAPIWgnet(object):

    URL_WGN_ACCOUNT_INFO = 'wgn/account/info/'

    @staticmethod
    async def get_account_info(account_ids : List[int]) -> Dict[str, Dict[int, object]]:

        info = dict()

        for realm_id, realm_spa_ids in sort_by_realms(account_ids).items():
            if realm_id not in PAPI_WGNET_REALMS:
                logging.warn('PAPIWgnet/get_account_info: realm %s is not supported by WGnet PAPI' % realm_id)
                continue
            params = dict()
            params['application_id'] = PAPI_WGNET_REALMS[realm_id]['client_id']
            params['account_id'] = str.join(',', [str(spa_id) for spa_id in realm_spa_ids])

            url = 'https://%s/%s' % (PAPI_WGNET_REALMS[realm_id]['host'], PAPIWgnet.URL_WGN_ACCOUNT_INFO)
            
            async with aiohttp.ClientSession().get(url, params = params) as response:
                response_json = json.loads(await response.text())
                info[realm_id] = response_json['data']

        return info
