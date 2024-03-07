"""
Simple Pygame is a Python library that provides many features using Pygame and other libraries. It can help you create multimedia programs much easier and cleaner.
"""
import gc as _gc
from typing import Iterable as _Iterable, Tuple as _Tuple

from . import mixer
from .constants import *
from .exceptions import *

def init(modules: _Iterable = []) -> _Tuple[str, ...]:
    """
    Import/Initialize Simple Pygame modules and return successfully imported/initialized modules.

    Parameters
    ----------

    modules (optional): Specifies which modules to import/initialize. If it's empty, import/initialize all Simple Pygame modules.
    """
    try:
        modules_len = len(modules)
        iter(modules)
    except TypeError:
        raise TypeError("Modules is not iterable.") from None

    successfully_imported = []

    if modules_len == 0 or MixerModule in modules:
        mixer_successfully_imported = mixer.init()
        if mixer_successfully_imported:
            successfully_imported.append(MixerModule)

    if modules_len == 0 or TransformModule in modules:
        try:
            global transform
            from . import transform
            successfully_imported.append(TransformModule)
        except ModuleNotFoundError:
            pass

    if modules_len == 0 or TerminalModule in modules:
        try:
            global terminal
            from . import terminal
            successfully_imported.append(TerminalModule)
        except ModuleNotFoundError:
            pass

    return (*successfully_imported,)

def quit(modules: _Iterable = []) -> _Tuple[str, ...]:
    """
    Quit/Uninitialize Simple Pygame modules and return successfully quit/uninitialized modules.

    Parameters
    ----------

    modules (optional): Specifies which modules to quit/uninitialize. If it's empty, quit/uninitialize all Simple Pygame modules.
    """
    try:
        modules_len = len(modules)
        iter(modules)
    except TypeError:
        raise TypeError("Modules is not iterable.") from None

    successfully_quit = []

    if modules_len == 0 or MixerModule in modules:
        mixer_successfully_quit = mixer.quit()
        if mixer_successfully_quit:
            successfully_quit.append(MixerModule)

    if modules_len == 0 or TransformModule in modules:
        try:
            global transform
            del transform
            successfully_quit.append(TransformModule)
        except NameError:
            pass

    if modules_len == 0 or TerminalModule in modules:
        try:
            global terminal
            del terminal
            successfully_quit.append(TerminalModule)
        except NameError:
            pass

    _gc.collect()
    return (*successfully_quit,)
