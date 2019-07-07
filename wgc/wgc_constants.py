from enum import Enum

class WGCAuthorizationResult(Enum):
    UNKNOWN = 0
    FAILED = 1
    FINISHED = 2
    REQUIRES_2FA = 3
    INCORRECT_2FA = 4
    INVALID_LOGINPASS = 5
    ACCOUNT_NOT_FOUND = 6


WGCRealms = { 
    'RU'   : {'domain_wgnet': 'ru.wargaming.net'  , 'domain_wgcps' : 'wgcps-ru.wargaming.net'  , 'client_id': '77cxLwtEJ9uvlcm2sYe4O8viIIWn1FEWlooMTTqF'},
    'EU'   : {'domain_wgnet': 'eu.wargaming.net'  , 'domain_wgcps' : 'wgcps-eu.wargaming.net'  , 'client_id': 'JJ5yuABVKqZekaktUR8cejMzxbbHAtUVmY2eamsS'},
    'NA'   : {'domain_wgnet': 'na.wargaming.net'  , 'domain_wgcps' : 'wgcps-na.wargaming.net'  , 'client_id': 'AJ5PLrEuz5C2d0hHmmjQJtjaMpueSahYY8CiswHE'},
    'ASIA' : {'domain_wgnet': 'asia.wargaming.net', 'domain_wgcps' : 'wgcps-asia.wargaming.net', 'client_id': 'Xe2oDM8Z6A4N70VZIV8RyVLHpvdtVPYNRIIYBklJ'},
}
