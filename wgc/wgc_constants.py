# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

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
    BANNED = 8
    INPROGRESS = 9

WGCInstallDocs = {
    'RU'   : 'https://worldoftanks.ru/ru/wgc/',
    'EU'   : 'https://worldoftanks.eu/en/wgc/',
    'NA'   : 'https://worldoftanks.com/en/wgc/',
    'ASIA' : 'https://worldoftanks.asia/en/wgc/',
}

WGCIds  = {
    'RU'   : 'WGC.RU.PRODUCTION',
    'EU'   : 'WGC.EU.PRODUCTION',
    'NA'   : 'WGC.NA.PRODUCTION',
    'ASIA' : 'WGC.ASIA.PRODUCTION',
}

WGCRealms = { 
    'RU'   : {'domain_wgnet': 'ru.wargaming.net'  , 'domain_wgcps' : 'wgcps-ru.wargaming.net'  , 'domain_wguscs' : 'wguscs-wgcru.wargaming.net', 'client_id': '77cxLwtEJ9uvlcm2sYe4O8viIIWn1FEWlooMTTqF'},
    'EU'   : {'domain_wgnet': 'eu.wargaming.net'  , 'domain_wgcps' : 'wgcps-eu.wargaming.net'  , 'domain_wguscs' : 'wguscs-wgcru.wargaming.net', 'client_id': 'JJ5yuABVKqZekaktUR8cejMzxbbHAtUVmY2eamsS'},
    'NA'   : {'domain_wgnet': 'na.wargaming.net'  , 'domain_wgcps' : 'wgcps-us.wargaming.net'  , 'domain_wguscs' : 'wguscs-wgcru.wargaming.net', 'client_id': 'AJ5PLrEuz5C2d0hHmmjQJtjaMpueSahYY8CiswHE'},
    'ASIA' : {'domain_wgnet': 'asia.wargaming.net', 'domain_wgcps' : 'wgcps-asia.wargaming.net', 'domain_wguscs' : 'wguscs-wgcru.wargaming.net', 'client_id': 'Xe2oDM8Z6A4N70VZIV8RyVLHpvdtVPYNRIIYBklJ'},
}


XMPPRealms = {
    'WOT'  : {
        'RU' : {
            'host'  : 'wotru.xmpp.wargaming.net',
            'port'  : 5222,
            'domain': 'wot-ru.loc',
            'res'   : 'moba_17e7103f-7f31-4358-bfd8-4be3f0fff650',
            'title' : 'World of Tanks (RU)'
        },
        'EU' : {
            'host'  : 'woteu34.xmpp.wargaming.net',
            'port'  : 5222,
            'domain': 'c2s.xmpp-wot-eu.wargaming.net',
            'res'   : 'moba_17e7103f-7f31-4358-bfd8-4be3f0fff650',
            'title' : 'World of Tanks (EU)'
        },
        'NA' : {
            'host'  : 'wotna34.xmpp.wargaming.net',
            'port'  : 5222,
            'domain': 'c2s.xmpp-wot-na.wargaming.net',
            'res'   : 'moba_17e7103f-7f31-4358-bfd8-4be3f0fff650',
            'title' : 'World of Tanks (NA)'
        },
        'ASIA' : {
            'host'  : 'wotasia34.xmpp.wargaming.net',
            'port'  : 5222,
            'domain': 'c2s.wotasia.xmpp.wargaming.net',
            'res'   : 'moba_17e7103f-7f31-4358-bfd8-4be3f0fff650',
            'title' : 'World of Tanks (ASIA)'
        }
    }
}


XMPPPresence = {
    'WOT': {
        'online': 'wot',
        'mobile': 'moba_17e7103f-7f31-4358-bfd8-4be3f0fff650'
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

ADDITIONAL_EXECUTABLE_NAMES = {
    'WOT' : [ 'win32/WorldOfTanks.exe' ]
}

USER_PROFILE_URLS = {
    'WOT' : {
        'RU'   : 'https://worldoftanks.ru/ru/community/accounts',
        'EU'   : 'https://worldoftanks.eu/en/community/accounts',
        'NA'   : 'https://worldoftanks.com/en/community/accounts',
        'ASIA' : 'https://worldoftanks.asia/en/community/accounts'
    }
}

GAMES_F2P = ['WOT', 'WOWS', 'WOWP']
