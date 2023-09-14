"""
A module for working with audio.
"""
import gc
from typing import Iterable, Tuple
from .constants import AudioClass

def init(classes: Iterable = []) -> Tuple[str, ...]:
    """
    Initialize the mixer module and return successfully initialized classes.

    Parameters
    ----------

    classes (optional): Specifies which classes to initialize. If it's empty, initialize all mixer module classes.
    """
    try:
        classes_len = len(classes)
        iter(classes)
    except TypeError:
        raise TypeError("Classes is not iterable.") from None

    successfully_initialized = []

    if classes_len == 0 or AudioClass in classes:
        try:
            global Audio
            from .audio import Audio
            successfully_initialized.append(AudioClass)
        except ModuleNotFoundError:
            pass

    return (*successfully_initialized,)

def quit(classes: Iterable = []) -> Tuple[str, ...]:
    """
    Uninitialize the mixer module and return successfully uninitialized classes.

    Parameters
    ----------

    classes (optional): Specifies which classes to uninitialize. If it's empty, uninitialize all mixer module classes.
    """
    try:
        classes_len = len(classes)
        iter(classes)
    except TypeError:
        raise TypeError("Classes is not iterable.") from None

    successfully_uninitialized = []

    if classes_len == 0 or AudioClass in classes:
        try:
            global Audio
            del Audio
            successfully_uninitialized.append(AudioClass)
        except NameError:
            pass

    gc.collect()
    return (*successfully_uninitialized,)
