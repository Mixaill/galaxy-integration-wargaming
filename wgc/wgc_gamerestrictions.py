# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
from typing import List
import xml.etree.ElementTree as ElementTree

class WGCGameRestrictions():
    def __init__(self, path: str):
        self.__logger = logging.getLogger('WGCGameRestrictions')
    
        self.__xml = None
        try:
            self.__xml = ElementTree.parse(path).getroot()
        except Exception:
            self.__logger.error('__init__: failed to parse file %s' % path)
            pass

    def get_allowed_ids(self) -> List[str]:
        result = list()

        if not self.__xml:
            self.__logger.warn('get_allowed_id(): object was not initialized properly')
            return result

        for item in self.__xml.find('allowed'):
            result.append(item.text)

        return result
