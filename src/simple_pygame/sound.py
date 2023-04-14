import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import simple_pygame, pygame.mixer, moviepy.audio.io.AudioFileClip as AudioFileClip, time
from typing import Optional, Union

class Sound:
    def __init__(self, path: str, channel: int = 0, initialize: bool = True) -> None:
        """
        A sound from a file contains audio. This class will load the entire file.

        Warning
        -------

        This class is deprecated because of its low speed when loading large files and sometimes inaccuracy. You can use `simple_pygame.mixer.Music()` instead.

        Requirements
        ------------
        
        - Pygame library.

        - MoviePy library.

        Parameters
        ----------

        path: Path to the file contains audio.

        channel (optional): Channel id for playing the sound. The id must be a value from 0 to the value of `pygame.mixer.get_num_channels()`.

        initialize (optional): Initialize the mixer module with some adjustments.
        """
        self.path = path
        self._bit_depth = 2
        self.currently_pause = False

        self._audio = AudioFileClip.AudioFileClip(path, nbytes = self._bit_depth)
        
        if not pygame.mixer.get_init():
            if initialize:
                pygame.mixer.pre_init(self._audio.fps, -16, self._audio.nchannels, 1024)

            pygame.mixer.init()
        elif initialize:
            pygame.mixer.quit()
            pygame.mixer.init(self._audio.fps, -16, self._audio.nchannels, 1024)

        self._sound = self.make_sound(self._audio, self._audio.fps, self._bit_depth)
        self._channel = pygame.mixer.Channel(channel)

    def make_sound(self, audio: AudioFileClip.AudioFileClip, sample_rate: Optional[int] = None, bit_depth: int = 2) -> pygame.mixer.Sound:
        """
        Return the sound transformed from the audio. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        audio: `AudioFileClip` to transform.

        sample_rate (optional): Sample rate of the audio for the conversion.
        - None for original audio sample rate.

        bit_depth (optional): Bit depth to encode the audio.
        """
        array = audio.to_soundarray(fps = sample_rate, nbytes = bit_depth, quantize = True)
        return pygame.sndarray.make_sound(array)
    
    def play(self, position: Union[int, float] = 0) -> None:
        """
        Play the sound. If any sound is current playing it will be restarted.

        Parameters
        ----------

        position (optional): Where to set the sound position in seconds.
        """
        if self.currently_pause:
            self.resume()
        self.stop()

        if position >= self.get_length():
            pass
        else:
            if position <= 0:
                sound = self._sound
                self._offset = 0
            else:
                sound = self.make_sound(self._audio.cutout(0, position), self._audio.fps, self._bit_depth)
                self._offset = position * 1000000000
            self._channel.play(sound)
            self._start = time.time_ns()

            self._pause_time = 0
            self._start_pause = False
            self.currently_pause = False
    
    def pause(self) -> None:
        """
        Pause the sound if it's current playing and not paused. It can be resumed with `resume()` function.
        """
        if self.get_busy() and not self.currently_pause:
            self._channel.pause()
            self._start_pause = time.time_ns()

            self.currently_pause = True
    
    def resume(self) -> None:
        """
        Resume the sound after it has been paused.
        """
        if self.get_busy() and self.currently_pause:
            self._channel.unpause()

            self._pause_time += time.time_ns() - self._start_pause
            self._start_pause = False
            self.currently_pause = False
    
    def stop(self) -> None:
        """
        Stop the sound if it's current playing.
        """
        self._channel.stop()

        self.currently_pause = False
    
    def set_position(self, position: Union[int, float]) -> None:
        """
        Set the current sound position where the sound will continue to play.

        Parameters
        ----------

        position: Where to set the sound position in seconds.
        """
        is_pausing = self.currently_pause

        self.play(position)

        if is_pausing:
            self.pause()
    
    def get_position(self) -> any:
        """
        Return the current sound position in seconds if it's current playing or pausing, otherwise `simple_pygame.SoundEnded`.
        """
        if self.get_busy():
            if self._start_pause:
                return self.nanoseconds_to_seconds(self._pause_time + self._offset + self._start_pause - self._start)
            else:
                return self.nanoseconds_to_seconds(time.time_ns() - self._start - self._pause_time + self._offset)
        else:
            return simple_pygame.SoundEnded
    
    def set_volume(self, volume: Union[int, float]) -> None:
        """
        Set the current channel volume.

        Parameters
        ----------

        volume: Channel volume.
        """
        if volume >= 0 and volume <= 1:
            self._channel.set_volume(volume)

    def get_volume(self) -> float:
        """
        Return the current channel volume.
        """
        return self._channel.get_volume()
    
    def get_busy(self) -> bool:
        """
        Return `True` if the channel is current playing or pausing, otherwise `False`.
        """
        return self._channel.get_busy()
    
    def get_sound(self) -> pygame.mixer.Sound:
        """
        Return the sound.
        """
        return self._sound

    def get_length(self, digit: int = 4) -> Union[int, float]:
        """
        Return the total sound length in seconds.

        Parameters
        ----------

        digit: Number of digits to round.
        """
        return round(self._sound.get_length(), digit)

    def nanoseconds_to_seconds(self, time: Union[int, float], digit: int = 4) -> Union[int, float]:
        """
        Convert nanoseconds to seconds. It's meant for use by the `Class` and not for general use.

        Parameters
        ----------

        time: Time in nanoseconds.

        digit: Number of digits to round.
        """
        return round(time / 1000000000, digit)
