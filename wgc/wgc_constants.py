from enum import Enum

class WGCAuthorizationResult(Enum):
    UNKNOWN = 0
    FAILED = 1
    FINISHED = 2
    REQUIRES_2FA = 3
    INCORRECT_2FA = 4
    INVALID_LOGINPASS = 5
    ACCOUNT_NOT_FOUND = 6
    INCORRECT_2FA_BACKUP = 7

WGCInstallDocs = {
    'RU'   : 'https://worldoftanks.ru/ru/wgc/',
    'EU'   : 'https://worldoftanks.eu/en/wgc/',
    'NA'   : 'https://worldoftanks.com/en/wgc/',
    'ASIA' : 'https://worldoftanks.asia/en/wgc/',
}

WGCRealms = { 
    'RU'   : {'domain_wgnet': 'ru.wargaming.net'  , 'domain_wgcps' : 'wgcps-ru.wargaming.net'  , 'domain_wguscs' : 'wguscs-wotru.wargaming.net', 'client_id': '77cxLwtEJ9uvlcm2sYe4O8viIIWn1FEWlooMTTqF'},
    'EU'   : {'domain_wgnet': 'eu.wargaming.net'  , 'domain_wgcps' : 'wgcps-eu.wargaming.net'  , 'domain_wguscs' : 'wguscs-wotru.wargaming.net', 'client_id': 'JJ5yuABVKqZekaktUR8cejMzxbbHAtUVmY2eamsS'},
    'NA'   : {'domain_wgnet': 'na.wargaming.net'  , 'domain_wgcps' : 'wgcps-us.wargaming.net'  , 'domain_wguscs' : 'wguscs-wotru.wargaming.net', 'client_id': 'AJ5PLrEuz5C2d0hHmmjQJtjaMpueSahYY8CiswHE'},
    'ASIA' : {'domain_wgnet': 'asia.wargaming.net', 'domain_wgcps' : 'wgcps-asia.wargaming.net', 'domain_wguscs' : 'wguscs-wotru.wargaming.net', 'client_id': 'Xe2oDM8Z6A4N70VZIV8RyVLHpvdtVPYNRIIYBklJ'},
}


XMPPRealms = {
    'WOT'  : {
        'RU' : {
            'host'  : 'wotru.xmpp.wargaming.net',
            'port'  : 5222,
            'domain': 'wot-ru.loc',
        },
        'EU' : {
            'host'  : 'woteu.xmpp.wargaming.net',
            'port'  : 5222,
            'domain': 'wot-eu.loc',
        },
        'NA' : {
            'host'  : 'wotna.xmpp.wargaming.net',
            'port'  : 5222,
            'domain': 'wot-na.loc',
        },
        'ASIA' : {
            'host'  : 'wotasia.xmpp.wargaming.net',
            'port'  : 5222,
            'domain': 'wot-asia.loc',
        }
    }
}

SPAIDRealms = {
        'RU' : (1, 499999999),
        'EU' : (500000000, 999999999),
        'NA' : (1000000000, 1499999999),
        'ASIA' : (2000000000, 3499999999)
}

PAPI_WGNET_REALMS = {
    'RU' : {
        'host': 'api.worldoftanks.ru',
        'client_id' : 'ebe303a75bd983f67f21b43578a1e498'
    },
    'EU' : {
        'host': 'api.worldoftanks.eu',
        'client_id' : 'ebe303a75bd983f67f21b43578a1e498'
    },
    'NA' : {
        'host': 'api.worldoftanks.com',
        'client_id' : 'ebe303a75bd983f67f21b43578a1e498'
    }
}

PAPI_WOT_REALMS = {
    'RU' : {
        'host': 'api.worldoftanks.ru',
        'client_id' : 'ebe303a75bd983f67f21b43578a1e498'
    },
    'EU' : {
        'host': 'api.worldoftanks.eu',
        'client_id' : 'ebe303a75bd983f67f21b43578a1e498'
    },
    'NA' : {
        'host': 'api.worldoftanks.com',
        'client_id' : 'ebe303a75bd983f67f21b43578a1e498'
    },
    'ASIA' : {
        'host': 'api.worldoftanks.asia',
        'client_id' : 'ebe303a75bd983f67f21b43578a1e498'
    }
}

FALLBACK_COUNTRY = ''
FALLBACK_LANGUAGE = 'en'

WGC_MUTEXES = {
    'CLBR': 'wgc_game_mtx_2333225295',
    'STD2': 'wgc_game_mtx_3816339327',
}
