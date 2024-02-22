"""
A module for working with sys.stdin on Unix.
"""
import termios, tty, select, sys

_original_tty_attributes = termios.tcgetattr(sys.stdin)

def setcooked() -> None:
    """
    Change the mode of sys.stdin to what it was when this module was imported.
    """
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, _original_tty_attributes)

def setraw() -> None:
    """
    Change the mode of sys.stdin to raw.
    """
    tty.setraw(sys.stdin)

def setcbreak() -> None:
    """
    Change the mode of sys.stdin to cbreak.
    """
    tty.setcbreak(sys.stdin)

def getch() -> str:
    """
    Return a character read from sys.stdin.
    """
    return sys.stdin.read(1)

def kbhit() -> bool:
    """
    Return `True` if a new keypress is detected. After any character has been read, `False` will be returned instead.
    """
    return sys.stdin in select.select((sys.stdin,), (), (), 0)[0]
