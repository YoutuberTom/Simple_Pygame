"""
A module for working with the terminal.
"""
import enum, sys
from typing import Union

try:
    import msvcrt
except ModuleNotFoundError:
    try:
        import getch, fcntl, os
    except ModuleNotFoundError:
        raise OSError("This module doesn't support your OS.") from None

characters = """0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ """
bytes_characters = b"""0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ """

class Keys_Windows(enum.Enum):
    """
    An enum class that contains Windows keys for convenient representation.
    """
    Tab = b"\t"
    Enter = b"\r"
    Backspace = b"\x08"
    Up_Arrow = b"\x00H"
    Down_Arrow = b"\x00P"
    Right_Arrow = b"\x00M"
    Left_Arrow = b"\x00K"
    F1 = b"\x00;"
    F2 = b"\x00<"
    F3 = b"\x00="
    F4 = b"\x00>"
    F5 = b"\x00?"
    F6 = b"\x00@"
    F7 = b"\x00A"
    F8 = b"\x00B"
    F9 = b"\x00C"
    F10 = b"\x00D"
    F11 = b"\x00\x85"
    F12 = b"\x00\x86"
    Esc = b"\x1b"
    Insert = b"\x00R"
    Delete = b"\x00S"
    Home = b"\x00G"
    End = b"\x00O"
    Page_Up = b"\x00I"
    Page_Down = b"\x00Q"
    Ctrl_C = b"\x03"
    Unknown = "Unknown"

class Keys_Unix(enum.Enum):
    """
    An enum class that contains Unix keys for convenient representation.
    """
    Tab = "\t"
    Enter = "\r"
    Backspace = "\x7f"
    Up_Arrow = "\x1b[A"
    Down_Arrow = "\x1b[B"
    Right_Arrow = "\x1b[C"
    Left_Arrow = "\x1b[D"
    F1 = "\x1bOP"
    F2 = "\x1bOQ"
    F3 = "\x1bOR"
    F4 = "\x1bOS"
    F5 = "\x1b[15~"
    F6 = "\x1b[17~"
    F7 = "\x1b[18~"
    F8 = "\x1b[19~"
    F9 = "\x1b[20~"
    F10 = "\x1b[21~"
    F11 = "\x1b[23~"
    F12 = "\x1b[24~"
    Esc = "\x1b"
    Insert = "\x1b[2~"
    Delete = "\x1b[3~"
    Home = "\x1b[H"
    End = "\x1b[F"
    Ctrl_C = "\x03"
    Unknown = "Unknown"

def getch_Windows() -> Union[Keys_Windows, str]:
    """
    Read a keypress and return the resulting character as a `Keys_Windows` object or as a string.
    """
    key = msvcrt.getch()

    if key in (b"\x00", b"\xe0"):
        key = b"\x00" + msvcrt.getch()
    elif key in bytes_characters:
        return key.decode(sys.stdin.encoding)

    try:
        return Keys_Windows(key)
    except ValueError:
        return Keys_Windows.Unknown

def getch_Unix() -> Union[Keys_Unix, str]:
    """
    Read a keypress and return the resulting character as a `Keys_Unix` object or as a string.
    """
    getch.setraw()
    key = getch.getch()
    getch.setcooked()

    if key == "\x1b":
        flags = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        while True:
            data = getch.getch()
            if data:
                key += data
            break

        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flags)
    elif key in characters:
        return key

    try:
        return Keys_Unix(key)
    except ValueError:
        return Keys_Unix.Unknown
