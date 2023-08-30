"""
A module that holds all Simple Pygame exceptions.
"""
class SimplePygameException(Exception):
    """
    Base class for all Simple Pygame exceptions.
    """

class BytesDecodeError(SimplePygameException):
    """
    Bytes decoding error.
    """

class NoOutputError(SimplePygameException):
    """
    Device doesn't contain output channels.
    """

class NoAudioError(SimplePygameException):
    """
    File doesn't contain audio.
    """

class FFmpegError(SimplePygameException):
    """
    FFmpeg related errors.
    """

class FFprobeError(SimplePygameException):
    """
    FFprobe related errors.
    """

__all__ = ["SimplePygameException", "BytesDecodeError", "NoOutputError", "NoAudioError", "FFmpegError", "FFprobeError"]