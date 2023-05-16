"""
Simple Pygame is a Python library that provides many features using Pygame and other libraries. It can help you create multimedia programs much easier and cleaner.
"""
import gc
from .constants import *
from . import mixer
from . import transform

_init = False

def get_init() -> bool:
    """
    Returns `True` if Simple Pygame is currently initialized, otherwise `False`.
    """
    return _init

def init() -> tuple:
    """
    Initializes all imported Simple Pygame modules and return successfully initialized modules.
    """
    global _init

    if get_init():
        return ()
    _init = True
    
    successfully_imported = []

    mixer_successfully_imported = mixer.init()
    if mixer_successfully_imported:
        successfully_imported.append(MixerModule)

    if len(successfully_imported) == 0:
        _init = False
    
    return (*successfully_imported,)

def quit() -> tuple:
    """
    Uninitializes all imported Simple Pygame modules and return successfully uninitialized modules.
    """
    global _init

    if not get_init():
        return ()
    _init = False

    successfully_quit = []

    mixer_successfully_quit = mixer.quit()
    if mixer_successfully_quit:
        successfully_quit.append(MixerModule)

    gc.collect()
    return (*successfully_quit,)
