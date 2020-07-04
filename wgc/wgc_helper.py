# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import os
import platform

from .wgc_constants import USER_PROFILE_URLS

### Platform
def get_platform() -> str:
    system = platform.system()
    if system == 'Windows':
        return 'windows'

    if system == 'Darwin':
        return 'macos'

    logging.error('get_platform: unknown platform %s' % system)
    return 'unknown'

### Process
DETACHED_PROCESS = 0x00000008

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
