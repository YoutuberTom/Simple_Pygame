import simple_pygame, pyaudio, audioop, subprocess, multiprocessing, json, time

class Music:
    def __init__(self, path: str, stream: int = 0, chunk: int = 64000) -> None:
        """
        A music stream read from a file contains audio. This class won't load the entire file. This class need to be ran inside `if __name__ == "__main__":` to work.

        Requirements
        ------------
        
        - Pyaudio library.

        - Ffmpeg.exe.

        Parameters
        ----------

        path: Path to the file contains audio.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        chunk (optional): Number of bytes per chunk when playing music.
        """
        self.path = path
        self.stream = stream
        self.chunk = chunk
        self.is_pausing = False
        self.__music_process = None

        self.set_format()

        self.__start = multiprocessing.Value("d", simple_pygame.MusicIsLoading)
        self.__volume = multiprocessing.Value("d", 1.0)
        self.__position = multiprocessing.Value("d", 0.0)

        self.__exception_pipe = multiprocessing.Pipe()

        self.__reposition_event = multiprocessing.Event()
        self.__pause_event = multiprocessing.Event()
        self.__terminate_event = multiprocessing.Event()
        
    def get_information(self, path: str, loglevel: str = "quiet") -> dict:
        """
        Return a dict contains all the file information. Return `-1` if ffprobe cannot read the file.

        Parameters
        ----------

        path: Path to the file to get information.

        loglevel (optional): Logging level and flags used by ffmpeg.exe.
        """
        ffprobe_command = ["ffprobe", "-loglevel", loglevel, "-print_format", "json", "-show_format", "-show_streams", "-i", path]

        try:
            data = subprocess.check_output(ffprobe_command)
            
            if not data:
                return -1

            return json.loads(data.replace(b"\r\n", b""))
        except FileNotFoundError:
            raise FileNotFoundError("No ffprobe found on your system. Make sure you've it installed and you can try specifying the ffprobe path.") from None
        except subprocess.CalledProcessError:
            raise ValueError("Invalid loglevel or path.") from None

    def create_pipe(self, path: str, position: float = 0.0, stream: int = 0, loglevel: str = "quiet") -> subprocess.Popen:
        """
        Return the pipe contains ffmpeg output and a dict contains the stream information. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        path: Path to the file to create pipe.

        position (optional): Where to set the music position in seconds.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        loglevel (optional): Logging level and flags used by ffmpeg.exe.
        """
        streams = self.get_information(path)["streams"]

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

        if position < 0:
            position = 0

        ffmpeg_command = ["ffmpeg", "-loglevel", loglevel, "-accurate_seek", "-ss", str(position), "-vn", "-i", path, "-map", f"0:a:{stream}?", "-f", self.ffmpegFormat, "pipe:1"]

        try:
            return subprocess.Popen(ffmpeg_command, stdout = subprocess.PIPE), streams[stream]
        except FileNotFoundError:
            raise FileNotFoundError("No ffmpeg found on your system. Make sure you've it installed and you can try specifying the ffmpeg path.") from None

    def set_format(self, format: any = simple_pygame.SInt16) -> None:
        """
        Set the music stream output format. Default is `simple_pygame.SInt16`.
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
    
    def play(self, loop: int = 0, position: float = 0.0) -> None:
        """
        Start the music stream. If music stream is current playing it will be restarted.

        Parameters
        ----------

        loop (optional): How many times to repeat the music. If this argument is set to `-1` repeats indefinitely.

        position (optional): Where to set the music position in seconds.
        """
        if self.get_busy():
            self.__terminate_event.set()
            
            while self.get_busy():
                pass
        
        if type(loop) != type(0):
            raise TypeError("Loop must be an integer.")
        elif loop < -1:
            return
    
        self.__pause_time = 0
        self.__start_pause = None

        if self.__exception_pipe[0].poll():
            self.__exception_pipe[0].recv()

        self.__reposition_event.clear()
        self.__pause_event.clear()
        self.__terminate_event.clear()

        self.__start.value = simple_pygame.MusicIsLoading
        self.__position.value = round(position, 15)

        self.__music_process = multiprocessing.Process(target = self.music, args = (self.__start, self.__volume, self.__exception_pipe[1], self.__reposition_event, self.__pause_event, self.__terminate_event, loop, self.__position))
        self.__music_process.daemon = True
        self.__music_process.start()

    def pause(self) -> None:
        """
        Pause the music stream if it's current playing and not paused. It can be resumed with `unpause()` function.
        """
        if self.get_busy() and not self.__pause_event.is_set():
            self.__pause_event.set()
            self.__start_pause = time.time_ns()

    def unpause(self) -> None:
        """
        Resume the music stream after it has been paused.
        """
        if self.get_busy() and self.__pause_event.is_set():
            self.__pause_event.clear()
            self.__pause_time += time.time_ns() - self.__start_pause
            self.__start_pause = None

    def stop(self) -> None:
        """
        Stop the music stream if it's current playing.
        """
        if self.get_busy():
            self.__terminate_event.set()

            while self.get_busy():
                pass
        
        self.__music_process = None
    
    def set_position(self, position: float) -> None:
        """
        Set the current music position where the music will continue to play.

        Parameters
        ----------

        position: Where to set the music position in seconds.
        """
        if self.get_busy():
            self.__position.value = round(position, 15)
            self.__reposition_event.set()
        else:
            is_pausing = self.__pause_event.is_set()

            self.play(position)

            if is_pausing:
                self.pause()
    
    def get_position(self) -> float:
        """
        Return the current music position in seconds if it's current playing or pausing, `simple_pygame.MusicIsLoading` if the music stream is loading, otherwise `simple_pygame.MusicEnded`.
        """
        if self.get_busy():
            position = self.__start.value

            if position == simple_pygame.MusicIsLoading:
                return simple_pygame.MusicIsLoading
            else:
                if self.__start_pause:
                    return self.nanoseconds_to_seconds(self.__start_pause - position - self.__pause_time)
                else:
                    return self.nanoseconds_to_seconds(time.time_ns() - position - self.__pause_time)
        else:
            return simple_pygame.MusicEnded
    
    def set_volume(self, volume: float) -> None:
        """
        Set the music stream volume. The volume must be a float between `0.0` and `2.0`, `1.0` is the original volume.

        Parameters
        ----------

        volume: Channel volume.
        """
        if volume >= 0 or volume <= 2:
            self.__volume.value = round(volume, 15)

    def get_volume(self) -> float:
        """
        Return the music stream volume.
        """
        return self.__volume.value
    
    def get_busy(self) -> bool:
        """
        Return `True` if currently playing or pausing music stream, otherwise `False`.
        """
        if self.__music_process:
            if self.__music_process.is_alive():
                return True
            else:
                return False
        else:
            return False
    
    def get_exception(self) -> Exception:
        """
        Return `None` if no exception is found, otherwise the exception. Any exceptions that have been returned will be removed from the list.
        """
        if self.__exception_pipe[0].poll():
            return self.__exception_pipe[0].recv()
        else:
            return

    def music(self, start: multiprocessing.Value, volume: multiprocessing.Value, exception_pipe: multiprocessing.Pipe, reposition_event: multiprocessing.Event, pause_event: multiprocessing.Event, terminate_event: multiprocessing.Event, loop: int = 0, position: multiprocessing.Value = multiprocessing.Value("d", 0.0)) -> None:
        """
        Play music from the pipe. This function should be run as a `Thread`/`Process`. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        start: `Value` to set the music stream start time.

        volume: `Value` to set the music stream volume.

        exception_pipe: `Pipe` to set the exception.

        reposition_event: `Event` to check when to reposition music.

        pause_event: `Event` to check if currently pausing music.

        terminate_event: `Event` to safely stop music stream.

        loop (optional): How many times to repeat the music. If this argument is set to `-1` repeats indefinitely.

        position (optional): `Value` to set the music position in seconds.
        """
        def safe_terminate() -> None:
            """
            Safely stop the music stream.
            """
            try:
                pipe.terminate()
            except:
                pass

            try:
                pa.terminate()
            except:
                pass

            reposition_event.clear()
            pause_event.clear()
            terminate_event.clear()

        def calculate_offset() -> float:
            """
            Return the music stream position offset.
            """
            duration = float(info["duration"])
            if position.value >= duration:
                return self.seconds_to_nanoseconds(duration, 0)
            else:
                return self.seconds_to_nanoseconds(position.value, 0)

        try:
            pipe, info = self.create_pipe(self.path, position.value, stream = self.stream)
            pa = pyaudio.PyAudio()
            stream = pa.open(int(info["sample_rate"]), info["channels"], self.paFormat, output = True)

            offset = calculate_offset()
            start.value = time.time_ns() - round(offset, 15)
            while not terminate_event.is_set():
                if not pause_event.is_set():
                    if reposition_event.is_set():
                        pipe, info = self.create_pipe(self.path, position.value, stream = self.stream)
                        reposition_event.clear()

                        offset = calculate_offset()
                        start.value = time.time_ns() - round(offset, 15)

                    data = pipe.stdout.read(self.chunk)

                    if data:
                        data = audioop.mul(data, self.aoFormat, volume.value)
                        stream.write(data)
                    else:
                        if loop == -1:
                            pipe, info = self.create_pipe(self.path, 0.0, stream = self.stream)
                            start.value = time.time_ns()
                        elif loop == 0:
                            break
                        else:
                            loop -= 1

                            pipe, info = self.create_pipe(self.path, 0.0, stream = self.stream)
                            start.value = time.time_ns()
        except OSError:
            exception_pipe.send(OSError("No audio output found."))
        except Exception as error:
            exception_pipe.send(error)

        safe_terminate()
    
    def nanoseconds_to_seconds(self, time: float, digit: int = 4) -> float:
        """
        Convert nanoseconds to seconds. It's meant for use by the `Class` and not for general use.

        Parameters
        ----------

        time: Time in nanoseconds.

        digit: Number of digits to round.
        """
        return round(time / 1000000000, digit)
    
    def seconds_to_nanoseconds(self, time: float, digit: int = 4) -> float:
        """
        Convert seconds to nanoseconds. It's meant for use by the `Class` and not for general use.

        Parameters
        ----------

        time: Time in seconds.

        digit: Number of digits to round.
        """
        return round(time * 1000000000, digit)