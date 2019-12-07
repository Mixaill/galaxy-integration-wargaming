import ctypes
import logging
import os

from .wgc_constants import USER_PROFILE_URLS

### Process
DETACHED_PROCESS = 0x00000008

### Mutex

SYNCHRONIZE = 0x00100000
MUTANT_QUERY_STATE = 0x0001
STANDARD_RIGHTS_REQUIRED = 0x000F0000
MUTEX_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | MUTANT_QUERY_STATE

def is_mutex_exists(mutex_name) -> bool:
    kerneldll = ctypes.windll.kernel32
    mutex_handle = kerneldll.OpenMutexW(MUTEX_ALL_ACCESS, 0, str(mutex_name))
    if mutex_handle != 0:
        kerneldll.CloseHandle(mutex_handle)
        return True

    return False

### FS

def scantree(path):
    """Recursively yield DirEntry objects for given directory."""
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from scantree(entry.path)
        else:
            yield entry

### Names

def fixup_gamename(name):
    if name == 'STD2':
        return 'Steel Division 2'

    return name

def get_profile_url(game_id: str, realm: str, user_id: str) -> str:
    if game_id not in USER_PROFILE_URLS:
        logging.error('wgc_helper/get_profile_url: unknown game_id %s' % game_id)
        return None

    game_urls = USER_PROFILE_URLS[game_id]
    if realm not in game_urls:
        logging.error('wgc_helper/get_profile_url: unknown realm %s' % realm)

    return '%s/%s' % (game_urls[realm], user_id)
