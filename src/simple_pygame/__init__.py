"""
Simple Pygame is a Python library that provides many features using Pygame and other libraries. It can help you create multimedia programs much easier and cleaner.
"""
import gc
from .constants import __version__
from .constants import *
from . import mixer

_init = False

def get_init() -> bool:
    """
    Return `True` if Simple Pygame is currently initialized, otherwise `False`.
    """
    return _init

def init() -> tuple:
    """
    Import/Initialize all Simple Pygame modules and return successfully imported/initialized modules.
    """
    global _init

    if get_init():
        return ()
    _init = True
    
    successfully_imported = []

    mixer_successfully_imported = mixer.init()
    if mixer_successfully_imported:
        successfully_imported.append(MixerModule)
    
    try:
        global transform
        from . import transform
        successfully_imported.append(TransformModule)
    except ImportError:
        pass

    if len(successfully_imported) == 0:
        _init = False
    
    return (*successfully_imported,)

def quit() -> tuple:
    """
    Quit/Uninitialize all Simple Pygame modules and return successfully quit/uninitialized modules.
    """
    global _init

    if not get_init():
        return ()
    _init = False

    successfully_quit = []

    mixer_successfully_quit = mixer.quit()
    if mixer_successfully_quit:
        successfully_quit.append(MixerModule)

    try:
        global transform
        del transform
        successfully_quit.append(TransformModule)
    except NameError:
        pass

    gc.collect()
    return (*successfully_quit,)
