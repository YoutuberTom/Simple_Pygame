"""
A module for working with sys.stdin on Unix.
"""
import termios as _termios, tty as _tty, sys as _sys
from select import select

_original_tty_attributes = _termios.tcgetattr(_sys.stdin)

def setcooked() -> None:
    """
    Change the mode of sys.stdin to what it was when this module was imported.
    """
    _termios.tcsetattr(_sys.stdin, _termios.TCSADRAIN, _original_tty_attributes)

def setraw() -> None:
    """
    Change the mode of sys.stdin to raw.
    """
    _tty.setraw(_sys.stdin)

def setcbreak() -> None:
    """
    Change the mode of sys.stdin to cbreak.
    """
    _tty.setcbreak(_sys.stdin)

def getch() -> str:
    """
    Return a character read from sys.stdin.
    """
    return _sys.stdin.read(1)

def kbhit() -> bool:
    """
    Return `True` if a new keypress is detected on sys.stdin. After any character has been read, `False` will be returned instead.
    """
    return _sys.stdin in select((_sys.stdin,), (), (), 0)[0]
