import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import simple_pygame, pygame, moviepy.editor, time

class Sound:
    def __init__(self, path: str, channel: int = 0, initialize: bool = True) -> None:
        """
        A sound read from a file contains audio. This class will load the entire file.

        Warning
        -------

        This class is deprecated because of its low speed when loading large files and sometimes inaccuracy. You can use `simple_pygame.mixer.music.Music()` instead.

        Requirements
        ------------
        
        - Pygame library.

        - MoviePy library.

        Parameters
        ----------

        path: Path to the file contains audio.

        channel (optional): Channel id for playing the sound. The id must be a value from 0 to the value of `pygame.mixer.get_num_channels()`.

        initialize (optional): initialize the mixer module with some adjustments.
        """
        self.path = path
        self.__bit_depth = 2
        self.is_pausing = False
        self.initialize = initialize

        self.channel = pygame.mixer.Channel(channel)

        self.__audio = moviepy.editor.AudioFileClip(path, nbytes = self.__bit_depth)
        self.__sound = self.make_sound(self.__audio, self.__audio.fps, self.__bit_depth)

        if initialize:
            pygame.mixer.quit()
            pygame.mixer.init(self.__audio.fps, -16, self.__audio.nchannels, 1024)

    def make_sound(self, audio: moviepy.editor.AudioFileClip, sample_rate: int = None, bit_depth: int = 2) -> pygame.mixer.Sound:
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
    
    def play(self, position: float = 0.0) -> None:
        """
        Play the sound. If any sound is current playing it will be restarted.

        Parameters
        ----------

        position (optional): Where to set the sound position in seconds.
        """
        if self.is_pausing:
            self.unpause()
        self.stop()

        if position >= self.get_length():
            pass
        else:
            if position <= 0:
                sound = self.__sound
                self.offset = 0
            else:
                sound = self.make_sound(self.__audio.cutout(0, position), self.__audio.fps, self.__bit_depth)
                self.offset = position * 1000000000
            self.channel.play(sound)
            self.start = time.time_ns()

            self.pause_time = 0
            self.start_pause = False
            self.is_pausing = False
    
    def pause(self) -> None:
        """
        Pause the sound if it's current playing and not paused. It can be resumed with `unpause()` function.
        """
        if self.get_busy() and not self.is_pausing:
            self.channel.pause()
            self.start_pause = time.time_ns()

            self.is_pausing = True
    
    def unpause(self) -> None:
        """
        Resume the sound after it has been paused.
        """
        if self.get_busy() and self.is_pausing:
            self.channel.unpause()

            self.pause_time += time.time_ns() - self.start_pause
            self.start_pause = False
            self.is_pausing = False
    
    def stop(self) -> None:
        """
        Stop the sound if it's current playing.
        """
        self.channel.stop()

        self.is_pausing = False
    
    def set_position(self, position: float) -> None:
        """
        Set the current sound position where the sound will continue to play.

        Parameters
        ----------

        position: Where to set the sound position in seconds.
        """
        is_pausing = self.is_pausing

        self.play(position)

        if is_pausing:
            self.pause()
    
    def get_position(self) -> float:
        """
        Return the current sound position in seconds if it's current playing or pausing, otherwise `simple_pygame.SoundEnded`.
        """
        if self.get_busy():
            if self.start_pause:
                return self.nanoseconds_to_seconds(self.pause_time + self.offset + self.start_pause - self.start)
            else:
                return self.nanoseconds_to_seconds(time.time_ns() - self.start - self.pause_time + self.offset)
        else:
            return simple_pygame.SoundEnded
    
    def set_volume(self, volume: float) -> None:
        """
        Set the current channel volume.

        Parameters
        ----------

        volume: Channel volume.
        """
        if volume >= 0 and volume <= 1:
            self.channel.set_volume(volume)

    def get_volume(self) -> float:
        """
        Return the current channel volume.
        """
        return self.channel.get_volume()
    
    def get_busy(self) -> bool:
        """
        Return `True` if the channel is current playing or pausing, otherwise `False`.
        """
        return self.channel.get_busy()
    
    def get_sound(self) -> pygame.mixer.Sound:
        """
        Return the sound.
        """
        return self.__sound

    def get_length(self, digit: int = 4) -> float:
        """
        Return the total sound length in seconds.

        Parameters
        ----------

        digit: Number of digits to round.
        """
        return round(self.__sound.get_length(), digit)

    def nanoseconds_to_seconds(self, time: float, digit: int = 4) -> float:
        """
        Convert nanoseconds to seconds. It's meant for use by the `Class` and not for general use.

        Parameters
        ----------

        time: Time in nanoseconds.

        digit: Number of digits to round.
        """
        return round(time / 1000000000, digit)