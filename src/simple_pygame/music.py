import simple_pygame, pyaudio, audioop, subprocess, threading, json, time
from typing import Optional, Union

class Music:
    def __init__(self, path: str, stream: int = 0, chunk: int = 8192, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        """
        A music stream from a file contains audio. This class won't load the entire file.

        Requirements
        ------------
        
        - Pyaudio library.

        - FFmpeg.

        Parameters
        ----------

        path: Path to the file contains audio.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        chunk (optional): Number of bytes per chunk when playing music.

        ffmpeg_path (optional): Path to ffmpeg.exe.

        ffprobe_path (optional): Path to ffprobe.exe.
        """
        self.path = path
        self.stream = stream
        self.chunk = chunk
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.currently_pause = None
        self.exception = None
        self.__music_thread = None
        self.__start = None
        self.__reposition = False
        self.__terminate = False

        self.__pause_time = 0
        self.__position = 0
        self.__volume = 1.0

        self.__pa = pyaudio.PyAudio()
        self.set_format()
        
    def get_information(self, path: str, ffprobe_path: str = "ffprobe", loglevel: str = "quiet") -> Optional[dict]:
        """
        Return a dict contains all the file information. Return `None` if ffprobe cannot read the file.

        Parameters
        ----------

        path: Path to the file to get information.

        ffprobe_path (optional): Path to ffprobe.exe.

        loglevel (optional): Logging level and flags used by ffprobe.exe.
        """
        ffprobe_command = [ffprobe_path, "-loglevel", loglevel, "-print_format", "json", "-show_format", "-show_streams", "-i", path]

        try:
            data = subprocess.check_output(ffprobe_command)
            
            if not data:
                return

            return json.loads(data.replace(b"\r\n", b""))
        except FileNotFoundError:
            raise FileNotFoundError("No ffprobe found on your system. Make sure you've it installed and you can try specifying the ffprobe path.") from None
        except subprocess.CalledProcessError:
            raise ValueError("Invalid loglevel or path.") from None

    def create_pipe(self, path: str, position: Union[int, float] = 0, stream: int = 0, format: Optional[int] = None, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe", loglevel: str = "quiet") -> subprocess.Popen:
        """
        Return the pipe contains ffmpeg output and a dict contains the stream information. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        path: Path to the file to create pipe.

        position (optional): Where to set the music position in seconds.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        format (optional): Data output format. Use format from the `set_format()` function if `None`.

        ffmpeg_path (optional): Path to ffmpeg.exe.

        ffprobe_path (optional): Path to ffprobe.exe.

        loglevel (optional): Logging level and flags used by ffmpeg.exe.
        """
        streams = self.get_information(path, ffprobe_path, loglevel)["streams"]

        for order, data in enumerate(streams):
            if data["codec_type"] != "audio":
                del streams[order]
        
        streams_len = len(streams)
        
        if streams_len == 0:
            raise ValueError("The file doesn't contain audio.")
        else:
            stream = int(stream)

            if stream < 0:
                stream = 0
            elif stream >= streams_len:
                stream = 0
        
        if not format:
            format = self.ffmpegFormat

        ffmpeg_command = [ffmpeg_path, "-nostdin", "-loglevel", loglevel, "-accurate_seek", "-ss", str(position), "-vn", "-i", path, "-map", f"0:a:{stream}?", "-f", format, "pipe:1"]

        try:
            return subprocess.Popen(ffmpeg_command, stdout = subprocess.PIPE, creationflags = subprocess.CREATE_NO_WINDOW), streams[stream]
        except FileNotFoundError:
            raise FileNotFoundError("No ffmpeg found on your system. Make sure you've it installed and you can try specifying the ffmpeg path.") from None
    
    def change_path(self, path: str, stream: int = 0, chunk: int = 8192, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        """
        Change the current path if you want to play a different file.

        Parameters
        ----------

        path: Path to the file contains audio.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        chunk (optional): Number of bytes per chunk when playing music.

        ffmpeg_path (optional): Path to ffmpeg.exe.

        ffprobe_path (optional): Path to ffprobe.exe.
        """
        self.path = path
        self.stream = stream
        self.chunk = chunk
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def set_format(self, format: int = simple_pygame.SInt16) -> None:
        """
        Set the music stream output format. Default is `simple_pygame.SInt16`.

        Parameters
        ----------

        format: Specify what format to use.
        """
        if format == simple_pygame.SInt8:
            self.paFormat = pyaudio.paInt8
            self.ffmpegFormat = "s8"
            self.aoFormat = 1
        elif format == simple_pygame.SInt16:
            self.paFormat = pyaudio.paInt16
            self.ffmpegFormat = "s16le"
            self.aoFormat = 2
        elif format == simple_pygame.SInt32:
            self.paFormat = pyaudio.paInt32
            self.ffmpegFormat = "s32le"
            self.aoFormat = 4
        else:
            raise ValueError("Invalid format.")
    
    def play(self, loop: int = 0, start: Union[int, float] = 0, exception_on_underflow: bool = False) -> None:
        """
        Start the music stream. If music stream is current playing it will be restarted.

        Parameters
        ----------

        loop (optional): How many times to repeat the music. If this argument is set to `-1` repeats indefinitely.

        start (optional): Where the music stream starts playing in seconds.

        exception_on_underflow (optional): Specifies whether an exception should be thrown (or silently ignored) on buffer underflow. Defaults to `False` for improved performance, especially on slower platforms.
        """
        self.stop()
        
        if loop.__class__ != int:
            raise TypeError("Loop must be an integer.")
        elif loop < -1:
            return
        
        self.currently_pause = False
        self.exception = None
        self.__start = None
        self.__start_pause = None
        self.__reposition = False
        self.__terminate = False

        self.__pause_time = 0
        if start < 0:
            self.__position = 0
        else:
            self.__position = start

        self.__music_thread = threading.Thread(target = self.music, args = (self.path, loop, self.stream, self.chunk, exception_on_underflow))
        self.__music_thread.daemon = True
        self.__music_thread.start()

    def pause(self) -> None:
        """
        Pause the music stream if it's current playing and not paused. It can be resumed with `resume()` function.
        """
        if self.get_busy() and not self.currently_pause:
            self.currently_pause = True

    def resume(self) -> None:
        """
        Resume the music stream after it has been paused.
        """
        if self.get_busy() and self.currently_pause:
            self.currently_pause = False

    def stop(self) -> None:
        """
        Stop the music stream if it's current playing.
        """
        if self.get_busy():
            self.__terminate = True

            while self.get_busy():
                pass
        
        self.__music_thread = None
    
    def set_position(self, position: Union[int, float]) -> None:
        """
        Set the current music position where the music will continue to play.

        Parameters
        ----------

        position: Where to set the music stream position in seconds.
        """
        if self.get_busy():
            if position < 0:
                self.__position = 0
            else:
                self.__position = position
            self.__reposition = True
        else:
            self.play(start = position)
    
    def get_position(self) -> Union[int, float]:
        """
        Return the current music position in seconds if it's current playing or pausing, `simple_pygame.MusicIsLoading` if the music stream is loading, otherwise `simple_pygame.MusicEnded`.
        """
        if self.get_busy():
            position = self.__start

            if position:
                if self.__start_pause:
                    return self.nanoseconds_to_seconds(self.__start_pause - position - self.__pause_time)
                else:
                    return self.nanoseconds_to_seconds(time.time_ns() - position - self.__pause_time)
            else:
                return simple_pygame.MusicIsLoading
        else:
            return simple_pygame.MusicEnded
    
    def set_volume(self, volume: Union[int, float]) -> None:
        """
        Set the music stream volume. The volume must be a int/float between `0` and `2`, `1` is the original volume.

        Parameters
        ----------

        volume: Music stream volume.
        """
        if volume >= 0 and volume <= 2:
            self.__volume = round(volume, 2)

    def get_volume(self) -> Union[int, float]:
        """
        Return the music stream volume.
        """
        return self.__volume
    
    def get_busy(self) -> bool:
        """
        Return `True` if currently playing or pausing music stream, otherwise `False`.
        """
        if self.__music_thread:
            if self.__music_thread.is_alive():
                return True
            else:
                return False
        else:
            return False
    
    def get_exception(self) -> Optional[Exception]:
        """
        Return `None` if no exception is found, otherwise the exception.
        """
        return self.exception

    def music(self, path: str, loop: int = 0, stream: int = 0, chunk: int = 8192, exception_on_underflow: bool = False) -> None:
        """
        Start the music stream. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        path: Path to the file contains audio.

        loop (optional): How many times to repeat the music. If this argument is set to `-1` repeats indefinitely.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        chunk (optional): Number of bytes per chunk when playing music.

        exception_on_underflow (optional): Specifies whether an exception should be thrown (or silently ignored) on buffer underflow. Defaults to `False` for improved performance, especially on slower platforms.
        """
        def clean_up() -> None:
            """
            Clean up everything before stopping the music stream.
            """
            try:
                pipe.terminate()
            except:
                pass

            try:
                stream_out.close()
            except:
                pass

            self.currently_pause = None

        def calculate_offset(position: Union[int, float]) -> Union[int, float]:
            """
            Return the music stream offset position.

            Parameters
            ----------

            position: The music stream position in seconds.
            """
            duration = float(info["duration"])
            if position >= duration:
                return self.seconds_to_nanoseconds(duration)
            else:
                return self.seconds_to_nanoseconds(position)

        try:
            paFormat = self.paFormat
            ffmpegFormat = self.ffmpegFormat
            aoFormat = self.aoFormat
            position = self.__position

            pipe, info = self.create_pipe(path, position, stream, format = ffmpegFormat)
            stream_out = self.__pa.open(int(info["sample_rate"]), info["channels"], paFormat, output = True, frames_per_buffer = chunk)

            offset = calculate_offset(position)
            self.__start = time.time_ns() - offset
            while not self.__terminate:
                if self.__reposition:
                    position = self.__position
                    pipe, info = self.create_pipe(path, position, stream, format = ffmpegFormat)
                    self.__reposition = False

                    offset = calculate_offset(position)
                    if self.__start_pause:
                        self.__start = self.__start_pause - offset - self.__pause_time
                    else:
                        self.__start = time.time_ns() - offset - self.__pause_time

                if not self.currently_pause:
                    if self.__start_pause:
                        self.__pause_time += time.time_ns() - self.__start_pause
                        self.__start_pause = None

                    data = pipe.stdout.read(chunk)

                    if data:
                        data = audioop.mul(data, aoFormat, self.__volume)
                        stream_out.write(data, exception_on_underflow = exception_on_underflow)
                    else:
                        self.__pause_time = 0

                        if loop == -1:
                            pipe, info = self.create_pipe(path, 0, stream, format = ffmpegFormat)
                            self.__start = time.time_ns()
                        elif loop == 0:
                            break
                        else:
                            loop -= 1

                            pipe, info = self.create_pipe(path, 0, stream, format = ffmpegFormat)
                            self.__start = time.time_ns()
                elif not self.__start_pause:
                    self.__start_pause = time.time_ns()
        except Exception as error:
            self.exception = error

        clean_up()
    
    def nanoseconds_to_seconds(self, time: Union[int, float], digit: int = 4) -> float:
        """
        Convert nanoseconds to seconds. It's meant for use by the `Class` and not for general use.

        Parameters
        ----------

        time: Time in nanoseconds.

        digit: Number of digits to round.
        """
        return round(time / 1000000000, digit)
    
    def seconds_to_nanoseconds(self, time: Union[int, float], digit: int = 4) -> Union[int, float]:
        """
        Convert seconds to nanoseconds. It's meant for use by the `Class` and not for general use.

        Parameters
        ----------

        time: Time in seconds.

        digit: Number of digits to round.
        """
        return round(time * 1000000000, digit)
    
    def __del__(self) -> None:
        """
        Clean up everything before deleting the class.
        """
        self.stop()
        self.__pa.terminate()
