import ctypes
import os

SYNCHRONIZE = 0x00100000
MUTANT_QUERY_STATE = 0x0001
STANDARD_RIGHTS_REQUIRED = 0x000F0000
MUTEX_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | MUTANT_QUERY_STATE

def is_mutex_exists(mutex_name):
    kerneldll = ctypes.windll.kernel32
    mutex_handle = kerneldll.OpenMutexW(MUTEX_ALL_ACCESS, 0, str(mutex_name))
    if mutex_handle != 0:
        kerneldll.CloseHandle(mutex_handle)
        return True

    return False


def scantree(path):
    """Recursively yield DirEntry objects for given directory."""
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from scantree(entry.path)
        else:
            yield entry