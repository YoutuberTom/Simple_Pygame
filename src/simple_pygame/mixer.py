"""A module for playing sounds and music."""
try:
    from .sound import Sound
except ImportError:
    pass

try:
    from .music import Music
except ImportError:
    pass