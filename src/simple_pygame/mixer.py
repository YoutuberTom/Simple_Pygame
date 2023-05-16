"""
A module for playing music.
"""
import gc
from .constants import MusicClass

_init = False

def get_init() -> bool:
    """
    Returns `True` if the mixer module is currently initialized, otherwise `False`.
    """
    return _init

def init() -> tuple:
    """
    Initializes the mixer module and return successfully initialized classes.
    """
    global _init

    if get_init():
        return ()
    _init = True
    
    successfully_imported = []

    try:
        global Music
        from .music import Music
        successfully_imported.append(MusicClass)
    except ImportError:
        pass

    if len(successfully_imported) == 0:
        _init = False

    return (*successfully_imported,)

def quit() -> tuple:
    """
    Uninitializes the mixer module and return successfully uninitialized classes.
    """
    global _init

    if not get_init:
        return ()
    _init = False

    successfully_quit = []

    try:
        global Music
        del Music
        successfully_quit.append(MusicClass)
    except NameError:
        pass

    gc.collect()
    return (*successfully_quit,)
