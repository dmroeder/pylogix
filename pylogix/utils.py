import sys


def is_micropython():
    if hasattr(sys, 'implementation'):
        if sys.implementation.name == 'micropython':
            return True
        return False
    return False


def is_python3():
    if hasattr(sys.version_info, 'major'):
        if sys.version_info.major == 3:
            return True
        return False
    return False


def is_python2():
    if hasattr(sys.version_info, 'major'):
        if sys.version_info.major == 2:
            return True
        return False
    return False
