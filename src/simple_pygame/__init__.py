"""
Simple Pygame is a Python library that provides many features using Pygame and other libraries. It can help you create multimedia programs much easier and cleaner.
"""
from .version import __version__

from . import mixer

SoundEnded = "SoundEnded"
MusicIsLoading = "MusicIsLoading"
MusicEnded = "MusicEnded"

SInt8 = "SInt8"
SInt16 = "SInt16"
SInt32 = "SInt32"

MixerModule = "MixerModule"
SoundClass = "SoundClass"
MusicClass = "MusicClass"

__init = False

def get_init() -> bool:
    """
    Return `True` if Simple Pygame is currently initialized, otherwise `False`.
    """
    return __init

def init() -> tuple:
    """
    Initialize all imported Simple Pygame modules and return successfully initialized modules.
    """
    global __init

    if get_init():
        return ()
    __init = True
    
    successfully_imported = []

    mixer_successfully_imported = mixer.init()
    if mixer_successfully_imported:
        successfully_imported.append(MixerModule)

    if len(successfully_imported) == 0:
        __init = False
    
    return (*successfully_imported,)

def quit() -> tuple:
    """
    Uninitialize all imported Simple Pygame modules and return successfully uninitialized modules.
    """
    global __init

    if not get_init():
        return ()
    __init = False
    
    import gc

    successfully_quit = []

    mixer_successfully_quit = mixer.quit()
    if mixer_successfully_quit:
        successfully_quit.append(MixerModule)

    gc.collect()
    return (*successfully_quit,)
