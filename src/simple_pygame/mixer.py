"""
A module for playing sounds and music.
"""
_init = False

def get_init() -> bool:
    """
    Return `True` if the mixer module is currently initialized, otherwise `False`.
    """
    return _init

def init() -> tuple:
    """
    Initialize the mixer module and return successfully initialized classes.
    """
    global _init

    if get_init():
        return ()
    _init = True

    import simple_pygame
    
    successfully_imported = []

    try:
        global Sound
        from .sound import Sound
        successfully_imported.append(simple_pygame.SoundClass)
    except ImportError:
        pass

    try:
        global Music
        from .music import Music
        successfully_imported.append(simple_pygame.MusicClass)
    except ImportError:
        pass

    if len(successfully_imported) == 0:
        _init = False

    return (*successfully_imported,)

def quit() -> tuple:
    """
    Uninitialize the mixer module and return successfully uninitialized classes.
    """
    global _init

    if not get_init:
        return ()
    _init = False

    import simple_pygame, gc

    successfully_quit = []

    try:
        global Sound
        del Sound
        successfully_quit.append(simple_pygame.SoundClass)
    except NameError:
        pass

    try:
        global Music
        del Music
        successfully_quit.append(simple_pygame.MusicClass)
    except NameError:
        pass

    gc.collect()
    return (*successfully_quit,)
