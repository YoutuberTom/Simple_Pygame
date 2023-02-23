"""Simple Pygame is a Python library that provides many features using Pygame and other libraries. It can help you create multimedia applications much easier and save you a lot of time."""
from .version import __version__

SoundEnded = -1
MusicIsLoading = -2
MusicEnded = -3

SInt8 = 1
SInt16 = 2
SInt32 = 3

def init() -> None:
    "Initialize all Simple Pygame modules."
    global mixer
    from . import mixer