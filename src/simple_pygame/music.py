import simple_pygame, pyaudio, audioop, subprocess, threading, json, time, sys
from typing import Optional, Union, Iterable

class Music:
    def __init__(self, path: Optional[str] = None, stream: int = 0, chunk: int = 4096, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        """
        A music stream from a file contains audio. This class won't load the entire file.

        Requirements
        ------------

        - Pyaudio library.

        - FFmpeg.

        - FFprobe (optional).

        Parameters
        ----------

        path (optional): Path to the file contains audio.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        chunk (optional): Number of bytes per chunk when playing music.

        ffmpeg_path (optional): Path to ffmpeg.

        ffprobe_path (optional): Path to ffprobe.
        """
        if path != None and type(path) != str:
            raise TypeError("Path must be None or a string.")

        if type(stream) != int:
            raise TypeError("Stream must be an integer.")

        if type(chunk) != int:
            raise TypeError("Chunk must be an integer.")

        if type(ffmpeg_path) != str:
            raise TypeError("FFmpeg path must be a string.")

        if type(ffprobe_path) != str:
            raise TypeError("FFprobe path must be a string.")

        self.path = path
        self.stream = stream
        self.chunk = chunk
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.currently_pause = False
        self.exception = None
        self._output_device_index = None
        self._music_thread = None
        self._start = None
        self._reposition = False
        self._terminate = False

        self._pause_time = 0
        self._position = 0
        self._volume = 1.0

        self._pa = pyaudio.PyAudio()
        self.set_format()

    @classmethod
    def get_information(self, path: str, use_ffmpeg: bool = False, ffmpeg_or_ffprobe_path: str = "ffprobe", loglevel: str = "quiet") -> Optional[dict]:
        """
        Return a dict contains all the file information. Return `None` if cannot read the file.

        Parameters
        ----------

        path: Path to the file to get information.

        use_ffmpeg (optional): Specify whether to use ffmpeg or ffprobe to get the file information.

        ffmpeg_or_ffprobe_path (optional): Path to ffmpeg or ffprobe.

        loglevel (optional): Logging level and flags used by ffprobe.
        """
        if type(path) != str:
            raise TypeError("Path must be a string.")

        if type(ffmpeg_or_ffprobe_path) != str:
            raise TypeError("FFmpeg/FFprobe path must be a string.")

        if type(loglevel) != str:
            raise TypeError("Loglevel must be a string.")

        if use_ffmpeg:
            try:
                raw_data = subprocess.check_output([ffmpeg_or_ffprobe_path, "-i", path], stderr = subprocess.STDOUT)
                raw_data = self.extract_information([data.strip() for data in raw_data.decode().replace("  ", " ").split("\r\n") if data != ""])
            except FileNotFoundError:
                raise FileNotFoundError("No ffmpeg found on your system. Make sure you've it installed and you can try specifying the ffmpeg path.") from None
            except subprocess.CalledProcessError as error:
                raw_data = [data.strip() for data in error.stdout.decode().replace("  ", " ").split("\r\n") if data != ""]

                if "No such file or directory" in raw_data[-1]:
                    raise ValueError("Invalid path.") from None
                elif "Invalid data found when processing input" in raw_data[-1]:
                    raise ValueError("Invalid data found.") from None

            return self.extract_information(raw_data)
        else:
            ffprobe_command = [ffmpeg_or_ffprobe_path, "-loglevel", loglevel, "-print_format", "json", "-show_format", "-show_streams", "-i", path]

            try:
                data = subprocess.check_output(ffprobe_command, stderr = subprocess.STDOUT)

                if data:
                    return json.loads(data.split(b"ffprobe")[0])
            except FileNotFoundError:
                raise FileNotFoundError("No ffprobe found on your system. Make sure you've it installed and you can try specifying the ffprobe path.") from None
            except subprocess.CalledProcessError as error:
                if b"Invalid loglevel" in error.stdout:
                    raise ValueError("Invalid loglevel.") from None
                else:
                    raise ValueError("Invalid ffprobe path or path or data.") from None

    @classmethod
    def extract_information(self, raw_data: Iterable[str]) -> dict:
        """
        Return a dict contains the processed information of the file. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        raw_data: An iterable object contains raw information of the file from ffmpeg.
        """
        try:
            raw_data = iter(raw_data)
        except TypeError:
            raise TypeError("Raw data is not iterable.") from None

        data = {}
        data["format"] = {}
        data["streams"] = []

        stream_index = 0
        for information in raw_data:
            if "Input" in information:
                data["format"]["tags"] = {}
                data["format"]["format_name"] = ""

                for small_information in information.split(",")[1:]:
                    if "from" in small_information:
                        data["format"]["filename"] = small_information[small_information.index("'") + 1: small_information.rindex("'")]
                    else:
                        data["format"]["format_name"] += small_information.strip() + ","

                data["format"]["format_name"] = data["format"]["format_name"][:-1]
            elif "major_brand" in information:
                data["format"]["tags"]["major_brand"] = information.split(":")[-1].strip()
            elif "minor_version" in information:
                data["format"]["tags"]["minor_version"] = information.split(":")[-1].strip()
            elif "compatible_brands" in information:
                data["format"]["tags"]["compatible_brands"] = information.split(":")[-1].strip()
            elif "encoder" in information:
                data["format"]["tags"]["encoder"] = information.split(":")[-1].strip()
            elif "encoded_by" in information:
                data["format"]["tags"]["encoded_by"] = information.split(":")[-1].strip()
            elif "Duration" in information or "start" in information or "bitrate" in information:
                for small_information in information.split(","):
                    if "Duration" in small_information:
                        time = small_information[small_information.index(":") + 1:].strip().split(":")
                        data["format"]["duration"] = float(time[0]) * 3600 + float(time[1]) * 60 + float(time[2])
                    elif "start" in small_information:
                        data["format"]["start_time"] = small_information.split(":")[-1].strip()
                    elif "bitrate" in small_information:
                        if "N/A" not in small_information and "Estimating duration from bitrate" not in small_information:
                            data["format"]["bit_rate"] = int(small_information.split()[-2]) * 1000
            elif "handler_name" in information:
                data["streams"][stream_index - 1]["tags"]["handler_name"] = information.split(":")[-1].strip()
            elif "HANDLER_NAME" in information:
                data["format"]["tags"]["HANDLER_NAME"] = information.split(":")[-1].strip()
            elif "title" in information:
                if stream_index == 0:
                    data["format"]["tags"]["title"] = information.split(":")[-1].strip()
                else:
                    data["streams"][stream_index - 1]["tags"]["title"] = information.split(":")[-1].strip()
            elif "album" in information:
                data["format"]["tags"]["album"] = information.split(":")[-1].strip()
            elif "TBPM" in information:
                data["format"]["tags"]["TBPM"] = int(information.split(":")[-1].strip())
            elif "genre" in information:
                data["format"]["tags"]["genre"] = information.split(":")[-1].strip()
            elif "TSRC" in information:
                data["format"]["tags"]["TSRC"] = information.split(":")[-1].strip()
            elif "track" in information:
                data["format"]["tags"]["track"] = int(information.split(":")[-1].strip())
            elif "artist" in information:
                data["format"]["tags"]["artist"] = information.split(":")[-1].strip()
            elif "comment" in information:
                if stream_index == 0:
                    data["format"]["tags"]["comment"] = information.split(":")[-1].strip()
                else:
                    data["streams"][stream_index - 1]["tags"]["comment"] = information.split(":")[-1].strip()
            elif "COMMENT" in information:
                data["streams"][stream_index - 1]["tags"]["COMMENT"] = information.split(":")[-1].strip()
            elif "Stream" in information:
                data["streams"].append({"index": stream_index})
                data["streams"][stream_index]["tags"] = {}

                for order, small_information in enumerate(information.split(",")):
                    if "Stream" in small_information:
                        small_information = small_information.split(":")
                        data["streams"][stream_index]["codec_type"] = small_information[-2].strip().lower()

                        small_information = small_information[-1].strip().split()
                        data["streams"][stream_index]["codec_name"] = small_information[0]

                        if len(small_information) == 5:
                            data["streams"][stream_index]["profile"] = small_information[1][1:-1]

                            if "/" == small_information[3]:
                                data["streams"][stream_index]["codec_tag_string"] = small_information[2][1:]
                                data["streams"][stream_index]["codec_tag"] = small_information[4][:-1]
                        if len(small_information) == 4:
                            if "/" == small_information[2]:
                                data["streams"][stream_index]["codec_tag_string"] = small_information[1][1:]
                                data["streams"][stream_index]["codec_tag"] = small_information[3][:-1]
                    elif order == 1 and data["streams"][stream_index]["codec_type"] == "video":
                        data["streams"][stream_index]["pix_fmt"] = small_information.strip()
                    elif "SAR" in small_information and "DAR" in small_information:
                        size = small_information[:small_information.index("[")].strip().split("x")
                        data["streams"][stream_index]["width"] = int(size[0])
                        data["streams"][stream_index]["height"] = int(size[1])

                        small_information = small_information[small_information.index("[") + 1:small_information.rindex("]")].split()
                        data["streams"][stream_index]["sample_aspect_ratio"] = small_information[small_information.index("SAR") + 1]
                        data["streams"][stream_index]["display_aspect_ratio"] = small_information[small_information.index("DAR") + 1]
                    elif "kb/s" in small_information:
                        data["streams"][stream_index]["bit_rate"] = int(small_information[:small_information.rindex("kb/s")].strip()) * 1000
                    elif "fps" in small_information:
                        data["streams"][stream_index]["avg_frame_rate"] = float(small_information[:small_information.rindex("fps")].strip())
                    elif "tbn" in small_information:
                        time_base = small_information[:small_information.rindex("tbn")].strip()
                        if "k" in time_base:
                            data["streams"][stream_index]["time_base"] = "1/" + str(int(time_base[:-1]) * 1000)
                        else:
                            data["streams"][stream_index]["time_base"] = "1/" + time_base
                    elif "Hz" in small_information:
                        data["streams"][stream_index]["sample_rate"] = int(small_information[:small_information.rindex("Hz")].strip())
                    elif "mono" in small_information:
                        data["streams"][stream_index]["channels"] = 1
                    elif "stereo" in small_information:
                        data["streams"][stream_index]["channels"] = 2
                    elif order == 3 and data["streams"][stream_index]["codec_type"] == "audio":
                        data["streams"][stream_index]["sample_fmt"] = small_information.strip()

                stream_index += 1

        if len(data["format"]["tags"]) == 0:
            del data["format"]["tags"]

        for index in range(stream_index):
            if len(data["streams"][index]["tags"]) == 0:
                del data["streams"][index]["tags"]

        return data

    @classmethod
    def create_pipe(self, path: str, position: Union[int, float] = 0, stream: int = 0, data_format: any = None, use_ffmpeg: bool = False, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe", loglevel: str = "quiet") -> list:
        """
        Return a pipe contains ffmpeg output, a dict contains the file information and a dict contains the stream information. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        path: Path to the file to create pipe.

        position (optional): Where to set the music position in seconds.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        data_format (optional): Output data format. Use format from the `set_format()` function if `None`.

        use_ffmpeg (optional): Specify whether to use ffmpeg or ffprobe to get the file information.

        ffmpeg_path (optional): Path to ffmpeg.

        ffprobe_path (optional): Path to ffprobe.

        loglevel (optional): Logging level and flags used by ffmpeg and ffprobe.
        """
        if type(path) != str:
            raise TypeError("Path must be a string.")

        if type(position) != int and type(position) != float:
            raise TypeError("Position must be an integer/a float.")

        if type(stream) != int:
            raise TypeError("Stream must be an integer.")

        if data_format == None:
            try:
                data_format = self.ffmpegFormat
            except AttributeError:
                raise ValueError("Must specify the output data format.") from None

        if type(ffmpeg_path) != str:
            raise TypeError("FFmpeg path must be a string.")

        if type(ffprobe_path) != str:
            raise TypeError("FFprobe path must be a string.")

        if type(loglevel) != str:
            raise TypeError("Loglevel must be a string.")

        if use_ffmpeg:
            information = self.get_information(path, use_ffmpeg, ffmpeg_path, loglevel)
        else:
            information = self.get_information(path, use_ffmpeg, ffprobe_path, loglevel)
        streams = information["streams"]

        audio_streams = []
        for data in streams:
            if data["codec_type"] == "audio":
                audio_streams.append(data)
        
        if len(audio_streams) == 0:
            raise ValueError("The file doesn't contain audio.")
        else:
            stream = int(stream)

            if stream < 0:
                stream = 0
            elif stream >= len(audio_streams):
                stream = 0

        ffmpeg_command = [ffmpeg_path, "-nostdin", "-loglevel", loglevel, "-accurate_seek", "-ss", str(position), "-vn", "-i", path, "-map", f"0:a:{stream}", "-f", data_format, "pipe:1"]

        try:
            return subprocess.Popen(ffmpeg_command, stdout = subprocess.PIPE, creationflags = subprocess.CREATE_NO_WINDOW), information, audio_streams[stream]
        except FileNotFoundError:
            raise FileNotFoundError("No ffmpeg found on your system. Make sure you've it installed and you can try specifying the ffmpeg path.") from None

    def change_attributes(self, path: Optional[str] = None, stream: int = 0, chunk: int = 4096, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        """
        An easier way to change some attributes.

        Parameters
        ----------

        path (optional): Path to the file contains audio.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        chunk (optional): Number of bytes per chunk when playing music.

        ffmpeg_path (optional): Path to ffmpeg.

        ffprobe_path (optional): Path to ffprobe.
        """
        if path != None and type(path) != str:
            raise TypeError("Path must be None or a string.")

        if type(stream) != int:
            raise TypeError("Stream must be an integer.")

        if type(chunk) != int:
            raise TypeError("Chunk must be an integer.")

        if type(ffmpeg_path) != str:
            raise TypeError("FFmpeg path must be a string.")

        if type(ffprobe_path) != str:
            raise TypeError("FFprobe path must be a string.")

        self.path = path
        self.stream = stream
        self.chunk = chunk
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def set_format(self, data_format: any = simple_pygame.SInt16) -> None:
        """
        Set the output data format. Default is `simple_pygame.SInt16`.

        Parameters
        ----------

        data_format (optional): Specify what format to use.
        """
        if data_format == simple_pygame.SInt8:
            self.paFormat = pyaudio.paInt8
            self.ffmpegFormat = "s8"
            self.aoFormat = 1
        elif data_format == simple_pygame.SInt16:
            self.paFormat = pyaudio.paInt16
            self.ffmpegFormat = "s16le" if sys.byteorder == "little" else "s16be"
            self.aoFormat = 2
        elif data_format == simple_pygame.SInt32:
            self.paFormat = pyaudio.paInt32
            self.ffmpegFormat = "s32le" if sys.byteorder == "little" else "s32be"
            self.aoFormat = 4
        elif data_format == simple_pygame.UInt8:
            self.paFormat = pyaudio.paUInt8
            self.ffmpegFormat = "u8"
            self.aoFormat = 1
        else:
            raise ValueError("Invalid format.")

    def get_device_count(self) -> int:
        """
        Return the number of PortAudio Host APIs.
        """
        return self._pa.get_device_count()

    def set_output_device_by_index(self, device_index: Optional[int] = None) -> None:
        """
        Set the output device by index.

        Parameters
        ----------

        device_index: The device's index. Set the output device to default output device if `None`.
        """
        if device_index == None:
            self._output_device_index = self.get_device_info()["index"]
            return

        if type(device_index) != int:
            raise TypeError("The device's index must be an integer.")

        if device_index < 0 or device_index > self.get_device_count() - 1:
            raise ValueError("Invalid index.")

        if self.get_device_info(device_index)["maxOutputChannels"] == 0:
            raise ValueError("The device doesn't have any output channels.")

        self._output_device_index = device_index

    def get_device_info(self, device_index: Optional[int] = None) -> dict:
        """
        Return the device info.

        Parameters
        ----------

        device_index: The device's index. Return the default output device info if `None`.
        """
        if device_index == None:
            return self._pa.get_default_output_device_info()
        
        if type(device_index) != int:
            raise TypeError("The device's index must be an integer.")
        
        if device_index < 0 or device_index > self.get_device_count() - 1:
            raise ValueError("Invalid index.")
    
        return self._pa.get_device_info_by_index(device_index)

    def play(self, loop: int = 0, start: Union[int, float] = 0, exception_on_underflow: bool = False, use_ffmpeg: bool = False) -> None:
        """
        Start the music stream. If the music stream is current playing it will be restarted.

        Parameters
        ----------

        loop (optional): How many times to repeat the music. If this args is set to `-1` repeats indefinitely.

        start (optional): Where the music stream starts playing in seconds.

        exception_on_underflow (optional): Specify whether an exception should be thrown (or silently ignored) on buffer underflow. Default to `False` for improved performance, especially on slower platforms.

        use_ffmpeg (optional): Specify whether to use ffmpeg or ffprobe to get the file information.
        """
        self.stop()

        if self.path == None:
            raise ValueError("Please specify the path before starting the music stream.")

        if type(loop) != int:
            raise TypeError("Loop must be an integer.")
        elif loop < -1:
            return

        if type(start) != int and type(start) != float:
            raise TypeError("Start position must be an integer/a float.")

        self.currently_pause = False
        self.exception = None
        self._start = None
        self._start_pause = None
        self._reposition = False
        self._terminate = False

        self._pause_time = 0
        if start < 0:
            self._position = 0
        else:
            self._position = start

        self._music_thread = threading.Thread(target = self.music, args = (self.path, loop, self.stream, self.chunk, exception_on_underflow, use_ffmpeg))
        self._music_thread.daemon = True
        self._music_thread.start()

    def pause(self) -> None:
        """
        Pause the music stream if it's current playing and not paused. It can be resumed with `resume()` function.
        """
        if self.get_busy() and not self.get_pause():
            self.currently_pause = True

    def resume(self) -> None:
        """
        Resume the music stream after it has been paused.
        """
        if self.get_busy() and self.get_pause():
            self.currently_pause = False

    def stop(self) -> None:
        """
        Stop the music stream if it's current playing.
        """
        if self.get_busy():
            self._terminate = True

            while self.get_busy():
                pass
        
        self._music_thread = None

    def join(self, delay: Union[int, float] = 0.1, raise_exception: bool = True) -> None:
        """
        Wait until the music stream stops.

        Parameters
        ----------

        delay (optional): The interval between each check to determine if the music stream is currently busy in seconds.

        raise_exception (optional): Specify whether an exception should be thrown (or silently ignored).
        """
        while self.get_busy():
            time.sleep(delay)

        if not raise_exception:
            return

        exception = self.get_exception()
        if exception:
            raise exception
    
    def get_pause(self) -> bool:
        """
        Return `True` if currently pausing the music stream, otherwise `False`.
        """
        if self.get_busy():
            return self.currently_pause
        return False

    def set_position(self, position: Union[int, float]) -> None:
        """
        Set the current music position where the music will continue to play.

        Parameters
        ----------

        position: Where to set the music stream position in seconds.
        """
        if type(position) != int and type(position) != float:
            raise TypeError("Position must be an integer/a float.")

        if self.get_busy():
            if position < 0:
                self._position = 0
            else:
                self._position = position
            self._reposition = True
        else:
            self.play(start = position)

    def get_position(self) -> any:
        """
        Return the current music position in seconds if it's current playing or pausing, `simple_pygame.MusicIsLoading` if the music stream is loading, otherwise `simple_pygame.MusicEnded`.
        """
        if self.get_busy():
            position = self._start

            if position:
                if self._start_pause:
                    return self.nanoseconds_to_seconds(self._start_pause - position - self._pause_time)
                else:
                    return self.nanoseconds_to_seconds(time.time_ns() - position - self._pause_time)
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
        if type(volume) != int and type(volume) != float:
            raise TypeError("Volume must be an integer/a float.")

        if volume >= 0 and volume <= 2:
            self._volume = round(volume, 2)

    def get_volume(self) -> Union[int, float]:
        """
        Return the music stream volume.
        """
        return self._volume

    def get_busy(self) -> bool:
        """
        Return `True` if currently playing or pausing the music stream, otherwise `False`.
        """
        if self._music_thread:
            if self._music_thread.is_alive():
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

    def music(self, path: str, loop: int = 0, stream: int = 0, chunk: int = 4096, exception_on_underflow: bool = False, use_ffmpeg: bool = False) -> None:
        """
        Start the music stream. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        path: Path to the file contains audio.

        loop (optional): How many times to repeat the music. If this args is set to `-1` repeats indefinitely.

        stream (optional): Which stream to use if the file has more than 1 audio stream. Use the default stream if stream is invalid.

        chunk (optional): Number of bytes per chunk when playing music.

        exception_on_underflow (optional): Specifies whether an exception should be thrown (or silently ignored) on buffer underflow. Default to `False` for improved performance, especially on slower platforms.

        use_ffmpeg (optional): Specify whether to use ffmpeg or ffprobe to get the file information.
        """
        def clean_up() -> None:
            """
            Clean up everything before stopping the music stream.
            """
            try:
                pipe.terminate()
            except NameError:
                pass

            try:
                stream_out.stop_stream()
                stream_out.close()
            except NameError:
                pass

            self.currently_pause = False

        def calculate_offset(position: Union[int, float]) -> Union[int, float]:
            """
            Return the music stream offset position.

            Parameters
            ----------

            position: The music stream position in seconds.
            """
            try:
                duration = float(stream_info["duration"])
            except KeyError:
                duration = float(info["format"]["duration"])

            if position >= duration:
                return self.seconds_to_nanoseconds(duration)
            else:
                return self.seconds_to_nanoseconds(position)

        try:
            ffmpeg_path = self.ffmpeg_path
            ffprobe_path = self.ffprobe_path
            paFormat = self.paFormat
            ffmpegFormat = self.ffmpegFormat
            aoFormat = self.aoFormat
            position = self._position

            pipe, info, stream_info = self.create_pipe(path, position, stream, ffmpegFormat, use_ffmpeg, ffmpeg_path, ffprobe_path)
            stream_out = self._pa.open(int(stream_info["sample_rate"]), stream_info["channels"], paFormat, output = True, output_device_index = self._output_device_index, frames_per_buffer = chunk)

            offset = calculate_offset(position)
            self._start = time.time_ns() - offset
            while not self._terminate:
                if self._reposition:
                    position = self._position
                    pipe, info, stream_info = self.create_pipe(path, position, stream, ffmpegFormat, use_ffmpeg, ffmpeg_path, ffprobe_path)
                    self._reposition = False

                    offset = calculate_offset(position)
                    if self._start_pause:
                        self._start = self._start_pause - offset - self._pause_time
                    else:
                        self._start = time.time_ns() - offset - self._pause_time

                if not self.get_pause():
                    if self._start_pause:
                        self._pause_time += time.time_ns() - self._start_pause
                        self._start_pause = None

                    data = pipe.stdout.read(chunk)

                    if data:
                        data = audioop.mul(data, aoFormat, self._volume)
                        stream_out.write(data, exception_on_underflow = exception_on_underflow)
                    else:
                        self._pause_time = 0

                        if loop == -1:
                            pipe, info, stream_info = self.create_pipe(path, 0, stream, ffmpegFormat, use_ffmpeg, ffmpeg_path, ffprobe_path)
                            self._start = time.time_ns()
                        elif loop == 0:
                            break
                        else:
                            loop -= 1

                            pipe, info, stream_info = self.create_pipe(path, 0, stream, ffmpegFormat, use_ffmpeg, ffmpeg_path, ffprobe_path)
                            self._start = time.time_ns()
                elif not self._start_pause:
                    self._start_pause = time.time_ns()
        except Exception as error:
            self.exception = error
        finally:
            clean_up()

    @classmethod
    def nanoseconds_to_seconds(self, time: Union[int, float], digit: int = 4) -> Union[int, float]:
        """
        Convert nanoseconds to seconds. It's meant for use by the `Class` and not for general use.

        Parameters
        ----------

        time: Time in nanoseconds.

        digit: Number of digits to round.
        """
        if type(time) != int and type(time) != float:
            raise TypeError("Time must be an integer/a float.")

        if type(digit) != int:
            raise TypeError("Digit must be an integer.")

        return round(time / 1000000000, digit)

    @classmethod
    def seconds_to_nanoseconds(self, time: Union[int, float], digit: int = 4) -> Union[int, float]:
        """
        Convert seconds to nanoseconds. It's meant for use by the `Class` and not for general use.

        Parameters
        ----------

        time: Time in seconds.

        digit: Number of digits to round.
        """
        if type(time) != int and type(time) != float:
            raise TypeError("Time must be an integer/a float.")

        if type(digit) != int:
            raise TypeError("Digit must be an integer.")

        return round(time * 1000000000, digit)
    
    def __str__(self) -> str:
        """
        Return a string represents the object.
        """
        if self.path == None:
            return "<Music()>"

        return f"<Music('{self.path}')>"

    def __repr__(self) -> str:
        """
        Return a string represents the object.
        """
        return self.__str__()

    def __del__(self) -> None:
        """
        Clean up everything before deleting the class.
        """
        try:
            self.stop()
        except AttributeError:
            pass

        try:
            self._pa.terminate()
        except AttributeError:
            pass
