import json
from typing import Dict, List

import aiohttp

from .wgc_constants import PAPI_WOT_REALMS
from .wgc_spa import sort_by_realms

class PAPIWoT(object):

    URL_WOT_ACCOUNT_INFO = 'wot/account/info/'

    @staticmethod
    async def get_account_info(account_ids : List[int]) -> Dict[str, Dict[int, object]]:

        info = dict()

        for realm_id, realm_spa_ids in sort_by_realms(account_ids).items():
            params = dict()
            params['application_id'] = PAPI_WOT_REALMS[realm_id]['client_id']
            params['account_id'] = str.join(',', [str(spa_id) for spa_id in realm_spa_ids])

            url = 'https://%s/%s' % (PAPI_WOT_REALMS[realm_id]['host'], PAPIWoT.URL_WOT_ACCOUNT_INFO)
            
            async with aiohttp.ClientSession().get(url, params = params) as response:
                response_json = json.loads(await response.text())
                info[realm_id] = response_json['data']

        return info
