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
    Tab = [b"\t"]
    Enter = [b"\r"]
    Backspace = [b"\x08"]
    Up_Arrow = [b"\x00", b"H"]
    Down_Arrow = [b"\x00", b"P"]
    Right_Arrow = [b"\x00", b"M"]
    Left_Arrow = [b"\x00", b"K"]
    F1 = [b'\x00', b';']
    F2 = [b'\x00', b'<']
    F3 = [b'\x00', b'=']
    F4 = [b'\x00', b'>']
    F5 = [b'\x00', b'?']
    F6 = [b'\x00', b'@']
    F7 = [b'\x00', b'A']
    F8 = [b'\x00', b'B']
    F9 = [b'\x00', b'C']
    F10 = [b'\x00', b'D']
    F11 = [b'\x00', b'\x85']
    F12 = [b'\x00', b'\x86']
    Esc = [b'\x1b']
    Insert = [b'\x00', b'R']
    Delete = [b'\x00', b'S']
    Home = [b'\x00', b'G']
    End = [b'\x00', b'O']
    Page_Up = [b'\x00', b'I']
    Page_Down = [b'\x00', b'Q']
    Ctrl_C = [b"\x03"]
    Unknown = "Unknown"

class Keys_Unix(enum.Enum):
    """
    An enum class that contains Unix keys for convenient representation.
    """
    Tab = ["\t"]
    Enter = ["\r"]
    Backspace = ["\x7f"]
    Up_Arrow = ["\x1b", "[", "A"]
    Down_Arrow = ["\x1b", "[", "B"]
    Right_Arrow = ["\x1b", "[", "C"]
    Left_Arrow = ["\x1b", "[", "D"]
    F1 = ["\x1b", "O", "P"]
    F2 = ["\x1b", "O", "Q"]
    F3 = ["\x1b", "O", "R"]
    F4 = ["\x1b", "O", "S"]
    F5 = ["\x1b", "[", "1", "5", "~"]
    F6 = ["\x1b", "[", "1", "7", "~"]
    F7 = ["\x1b", "[", "1", "8", "~"]
    F8 = ["\x1b", "[", "1", "9", "~"]
    F9 = ["\x1b", "[", "2", "0", "~"]
    F10 = ["\x1b", "[", "2", "1", "~"]
    F11 = ["\x1b", "[", "2", "3", "~"]
    F12 = ["\x1b", "[", "2", "4", "~"]
    Esc = ["\x1b"]
    Insert = ["\x1b", "[", "2", "~"]
    Delete = ["\x1b", "[", "3", "~"]
    Home = ["\x1b", "[", "H"]
    End = ["\x1b", "[", "F"]
    Ctrl_C = ["\x03"]
    Unknown = "Unknown"

def getch_Windows() -> Union[Keys_Windows, str]:
    """
    Read a keypress and return the resulting character as a `Keys_Windows` object or as a string.
    """
    key = [msvcrt.getch()]

    if key[0] in (b"\x00", b"\xe0"):
        key = [b"\x00", msvcrt.getch()]

    if len(key) == 1 and key[0] in bytes_characters:
        return key[0].decode(sys.stdin.encoding)
    try:
        return Keys_Windows(key)
    except ValueError:
        return Keys_Windows.Unknown

def getch_Unix() -> Union[Keys_Unix, str]:
    """
    Read a keypress and return the resulting character as a `Keys_Unix` object or as a string.
    """
    getch.setraw()
    key = [getch.getch()]
    getch.setcooked()

    if key[0] == "\x1b":
        flags = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        while True:
            data = getch.getch()

            if data == "":
                break
            else:
                key.append(data)

        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flags)

    if len(key) == 1 and key[0] in characters:
        return key[0]
    try:
        return Keys_Unix(key)
    except ValueError:
        return Keys_Unix.Unknown