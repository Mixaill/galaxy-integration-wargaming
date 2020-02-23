# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

from typing import Dict, List

from .wgc_constants import SPAIDRealms

def sort_by_realms(accounts_ids : List[int]) -> Dict[str,List[int]]:
    result = dict()

    for account_id in [int(x) for x in accounts_ids]:
        for realm,realm_limits in SPAIDRealms.items():
            if account_id >= realm_limits[0] and account_id <= realm_limits[1]:
                if realm not in result:
                    result[realm] = list()
                result[realm].append(account_id)

    return result
    