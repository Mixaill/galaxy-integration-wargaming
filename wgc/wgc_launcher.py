# (c) 2019-2020 Mikhail Paulyshka
# SPDX-License-Identifier: MIT

import logging
import subprocess

from .wgc_helper import get_platform, DETACHED_PROCESS
from .wgc_location import WGCLocation

class WgcLauncher:

    #
    # WGC Launch
    #
    @staticmethod
    def launch_wgc(minimized: bool = False) -> bool:
        if not WGCLocation.is_wgc_installed():
            logging.getLogger('wgc_launcher').warning('launch_wgc: WGC is not installed')
        
        if get_platform() == "macos":
            return WgcLauncher.__launch_wgc_macos(minimized)
        elif get_platform() == 'windows':
            return WgcLauncher.__launch_wgc_windows(minimized)
        else:
            logging.getLogger('wgc_launcher').warning('launch_wgc: unsupported platform (%s)' % (get_platform()))
            return False

    @staticmethod
    def __launch_wgc_macos(minimized: bool = False) -> bool:
        if minimized:
            logging.getLogger('wgc_launcher').warning('__launch_wgc_macos: minimized is not supported')
        
        subprocess.Popen([WGCLocation.get_wgc_exe_macos_path()], close_fds=True)
        return True

    @staticmethod
    def __launch_wgc_windows(minimized: bool = False) -> bool:
        subprocess.Popen([WGCLocation.get_wgc_exe_path(), '--background' if minimized else ''], creationflags=DETACHED_PROCESS)
        return True

    #
    # WGC Game Install
    #

    @staticmethod
    def launch_wgc_gameinstall(install_uri: str) -> bool:
        if get_platform() == "macos":
           logging.getLogger('wgc_launcher').error('launch_wgc_gameinstall: unsupported on macos')
           return False

        return WgcLauncher.__launch_wgc_gameinstall_windows(install_uri)
    
    @staticmethod
    def __launch_wgc_gameinstall_windows(install_uri: str) -> bool:
        subprocess.Popen([WGCLocation.get_wgc_exe_path(), '--install', '-g', install_uri, '--skipJobCheck'], creationflags=DETACHED_PROCESS)
        return True

