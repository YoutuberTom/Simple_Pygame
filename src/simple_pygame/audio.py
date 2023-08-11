"""
A module for playing audio.

Requirements
------------

- Pyaudio library.

- FFmpeg.

- FFprobe (optional).
"""
import pyaudio, audioop, subprocess, threading, time, json, re, platform, sys
from .constants import SInt8, SInt16, SInt32, UInt8, AudioIsLoading, AudioEnded
from typing import Optional, Union, Iterable, Tuple, Dict, Any

class Audio:
    def __init__(self, path: Optional[str] = None, stream: int = 0, chunk: int = 4096, frames_per_buffer: Union[int, Any] = pyaudio.paFramesPerBufferUnspecified, encoding: Optional[str] = None, use_ffmpeg: bool = False, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        """
        An audio object from a file contains audio. This class won't load the entire file.

        Requirements
        ------------

        - Pyaudio library.

        - FFmpeg.

        - FFprobe (optional).

        Parameters
        ----------

        path (optional): Path to the file contains audio.

        stream (optional): Which stream to use if the file has more than 1 audio streams. Use the default stream if the given stream is invalid.

        chunk (optional): Number of bytes per chunk when playing audio.

        frames_per_buffer (optional): Number of frames per buffer. Defaults to `pyaudio.paFramesPerBufferUnspecified`.

        encoding (optional): Encoding for decoding. Use the default encoding if the given encoding is `None`.

        use_ffmpeg (optional): Specifies whether to use `ffmpeg` or `ffprobe` to get the file's information.

        ffmpeg_path (optional): Path to `ffmpeg`.

        ffprobe_path (optional): Path to `ffprobe`.
        """
        if path != None and type(path) != str:
            raise TypeError("Path must be None/a string.")

        if type(stream) != int:
            raise TypeError("Stream must be an integer.")

        if type(chunk) != int:
            raise TypeError("Chunk must be an integer.")
        elif chunk <= 0:
            raise ValueError("Chunk must be greater than 0.")

        if frames_per_buffer != pyaudio.paFramesPerBufferUnspecified and type(frames_per_buffer) != int:
            raise TypeError("Frames per buffer must be pyaudio.paFramesPerBufferUnspecified/an integer.")
        elif type(frames_per_buffer) == int and frames_per_buffer < 0:
            raise ValueError("Frames per buffer must be non-negative.")

        if encoding != None and type(encoding) != str:
            raise TypeError("Encoding must be None/a string.")

        if type(ffmpeg_path) != str:
            raise TypeError("FFmpeg path must be a string.")

        if type(ffprobe_path) != str:
            raise TypeError("FFprobe path must be a string.")

        self.path = path
        self.stream = stream
        self.chunk = chunk
        self.frames_per_buffer = frames_per_buffer
        self.encoding = encoding
        self.use_ffmpeg = use_ffmpeg
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.currently_pause = False
        self.exception = None
        self.information = None
        self.stream_information = None
        self._output_device_index = None
        self._audio_thread = None
        self._start = None
        self._reposition = False
        self._terminate = False

        self._position = 0
        self._pause_offset = None
        self._duration = None
        self._chunk_time = None
        self._chunk_length = None
        self._volume = 1.0

        self._pa = pyaudio.PyAudio()
        self.set_format()

    @classmethod
    def get_information(self, path: str, encoding: Optional[str] = None, use_ffmpeg: bool = False, executable_path: str = "ffprobe") -> Dict[str, Any]:
        """
        Return a dict contains all the file's information.

        Parameters
        ----------

        path: Path to the file to get information.

        encoding (optional): Encoding for decoding. Use the default encoding if the given encoding is `None`.

        use_ffmpeg (optional): Specifies whether to use `ffmpeg` or `ffprobe` to get the file's information.

        executable_path (optional): Path to `ffmpeg` or `ffprobe` depends on the value of `use_ffmpeg`.
        """
        if type(path) != str:
            raise TypeError("Path must be a string.")

        if encoding != None and type(encoding) != str:
            raise TypeError("Encoding must be None/a string.")

        if type(executable_path) != str:
            raise TypeError("FFmpeg/FFprobe path must be a string.")

        if use_ffmpeg:
            try:
                result = subprocess.run([executable_path, "-i", path], capture_output = True, encoding = encoding, text = True)
            except FileNotFoundError:
                raise FileNotFoundError("No ffmpeg found on your system. Make sure you've it installed and you can try specifying the ffmpeg path.") from None
            except LookupError:
                raise ValueError("Invalid encoding.") from None

            if result.stderr == None:
                raise ValueError(f"""{'Default encoding' if encoding == None else f'Encoding "{repr(encoding)[1:-1]}"'} cannot decode the byte sequence. You can try using other encodings.""")

            raw_data = result.stderr.split("\n")[:-1]
            if raw_data[-1] != "At least one output file must be specified":
                raise RuntimeError(raw_data[-1])

            return self.extract_information(raw_data)
        else:
            try:
                result = subprocess.run([executable_path, "-print_format", "json", "-show_format", "-show_programs", "-show_streams", "-show_chapters", "-i", path], capture_output = True, check = True, encoding = encoding, text = True)

                if result.stdout == None:
                    raise ValueError(f"""{'Default encoding' if encoding == None else f'Encoding "{repr(encoding)[1:-1]}"'} cannot decode the byte sequence. You can try using other encodings.""")

                return json.loads(result.stdout)
            except FileNotFoundError:
                raise FileNotFoundError("No ffprobe found on your system. Make sure you've it installed and you can try specifying the ffprobe path.") from None
            except subprocess.CalledProcessError:
                raise ValueError("Invalid ffprobe path or path or data.") from None
            except LookupError:
                raise ValueError("Invalid encoding.")

    @classmethod
    def extract_information(self, raw_data: Iterable[str]) -> Dict[str, Any]:
        """
        Return a dict contains all the file's information.

        Parameters
        ----------

        raw_data: An iterable object contains the file's raw information from `ffmpeg`.
        """
        try:
            if len(raw_data) == 0:
                raise ValueError("Raw data mustn't be empty.")

            raw_data = iter(raw_data)
        except TypeError:
            raise TypeError("Raw data is not iterable.") from None

        data = {}
        data["format"] = {}
        data["format"]["tags"] = {}
        data["programs"] = []
        data["streams"] = []
        data["chapters"] = []

        metadata = None
        program_index, stream_index, chapter_index = -1, -1, -1
        for information in raw_data:
            if type(information) != str:
                raise TypeError("Raw data must contain only strings.")
            elif information == "":
                continue

            information = information.lstrip()
            if information == "Metadata:" or information == "Chapters:" or information[:1] == "[":
                continue
            elif information[:5] == "Input":
                metadata = "format"

                small_information = re.split(r", (?=(?:[^']*'[^']*')*[^']*$)", information)[1:]
                data[metadata]["format_name"] = small_information[0]
                data[metadata]["filename"] = re.search(r"'((?:[^']|'[^']+')*)'", small_information[1]).group(1)
            elif information[:7] == "Program":
                metadata = "programs"
                program_index += 1

                data[metadata].append({"program_num": program_index})
                data[metadata][program_index]["tags"] = {}
            elif information[:6] == "Stream":
                metadata = "streams"
                stream_index += 1

                data[metadata].append({"index": stream_index})
                data[metadata][stream_index]["tags"] = {}
                data[metadata][stream_index]["disposition"] = {"default": 0, "dub": 0, "original": 0, "comment": 0, "lyrics": 0, "karaoke": 0, "forced": 0, "hearing_impaired": 0, "visual_impaired": 0, "clean_effects": 0, "attached_pic": 0, "timed_thumbnails": 0, "captions": 0, "descriptions": 0, "metadata": 0, "dependent": 0, "still_image": 0}

                small_informations = re.split(r", (?![^(]*\))", information)
                for index, small_information in enumerate(small_informations):
                    if index == len(small_informations) - 1:
                        found_match = re.search(r"^(.*?)(?: \((.*?)\))?$", small_information)

                        if found_match.group(2):
                            small_information = found_match.group(1)
                            data[metadata][stream_index]["disposition"][found_match.group(2).replace(" ", "_")] = 1

                    if index == 0:
                        found_match = re.search(r"((?:Video|Audio)): (.*?)(?: (\(.*?\)))?$", small_information)
                        data[metadata][stream_index]["codec_type"] = found_match.group(1).lower()
                        data[metadata][stream_index]["codec_name"] = found_match.group(2)

                        if data[metadata][stream_index]["codec_type"] == "audio":
                            data[metadata][stream_index].update({"avg_frame_rate": "0/0", "r_frame_rate": "0/0"})

                        if not found_match.group(3):
                            continue

                        matches = re.findall(r"\((.*?)\)", found_match.group(3))
                        found_match = re.search(r"(.*) / (.*)", matches[0])
                        if found_match:
                            data[metadata][stream_index]["codec_tag_string"], data[metadata][stream_index]["codec_tag"] = found_match.group(1), found_match.group(2)
                        else:
                            data[metadata][stream_index]["profile"] = matches[0]

                        if len(matches) == 1:
                            continue

                        found_match = re.search(r"(.*) / (.*)", matches[1])
                        data[metadata][stream_index]["codec_tag_string"], data[metadata][stream_index]["codec_tag"] = found_match.group(1), found_match.group(2)
                    elif small_information[-4:] == "kb/s":
                        data[metadata][stream_index]["bit_rate"] = int(re.search(r"(\d+) kb/s", small_information).group(1)) * 1000
                    elif data[metadata][stream_index]["codec_type"] == "video":
                        if index == 1:
                            found_match = re.search(r"^(.*?)(?:\s*\((.*?)\))?$", small_information)
                            data[metadata][stream_index]["pix_fmt"] = found_match.group(1)

                            if not found_match.group(2):
                                continue

                            matches = found_match.group(2).split(", ")
                            matches_len = len(matches)

                            if matches_len == 1:
                                data[metadata][stream_index]["color_range" if matches[0] in ["tv", "pc"] else "field_order"] = matches[0]
                                continue
                            data[metadata][stream_index]["color_range"] = matches[0]

                            colors = matches[1].split("/")
                            if len(colors) == 1:
                                data[metadata][stream_index].update({key: colors[0] for key in ["color_space", "color_primaries", "color_transfer"]})
                            else:
                                data[metadata][stream_index].update({"color_space": colors[0]} if colors[0] != "unknown" else {})
                                data[metadata][stream_index].update({"color_primaries": colors[1]} if colors[1] != "unknown" else {})
                                data[metadata][stream_index].update({"color_transfer": colors[2]} if colors[2] != "unknown" else {})

                            if matches_len == 3:
                                data[metadata][stream_index]["field_order"] = matches[2]
                        elif small_information[-3:] == "fps":
                            data[metadata][stream_index]["avg_frame_rate"] = float(re.search(r"(\d+\.\d+|\d+) fps", small_information).group(1))
                        elif small_information[-3:] == "tbr":
                            found_match = re.search(r"(\d+\.\d+|\d+)(.*) tbr", small_information)
                            data[metadata][stream_index]["r_frame_rate"] = float(found_match.group(1)) * (1000 if found_match.group(2) == "k" else 1)
                        elif small_information[-3:] == "tbn":
                            found_match = re.search(r"(\d+\.\d+|\d+)(.*) tbn", small_information)
                            data[metadata][stream_index]["time_base"] = 1 / (float(found_match.group(1)) * (1000 if found_match.group(2) == "k" else 1))
                        elif small_information[-3:] == "tbc":
                            found_match = re.search(r"(\d+\.\d+|\d+)(.*) tbc", small_information)
                            data[metadata][stream_index]["codec_time_base"] = 1 / (float(found_match.group(1)) * (1000 if found_match.group(2) == "k" else 1))
                        else:
                            found_match = re.search(r"(\d+)x(\d+)", small_information)
                            if not found_match:
                                found_match = re.search(r"SAR (.*) DAR (.*)", small_information)
                                data[metadata][stream_index].update({"sample_aspect_ratio": found_match.group(1), "display_aspect_ratio": found_match.group(2)})

                                continue

                            width, height = found_match.group(1), found_match.group(2)
                            data[metadata][stream_index].update({"width": width, "height": height, "coded_width": width, "coded_height": height})

                            found_match = re.search(r"\[SAR (.*) DAR (.*)\]", small_information)
                            if not found_match:
                                continue

                            data[metadata][stream_index].update({"sample_aspect_ratio": found_match.group(1), "display_aspect_ratio": found_match.group(2)})
                    elif data[metadata][stream_index]["codec_type"] == "audio":
                        if small_information[-2:] == "Hz":
                            data[metadata][stream_index]["sample_rate"] = int(re.search(r"(\d+) Hz", small_information).group(1))
                        elif index == 2:
                            data[metadata][stream_index]["channel_layout"] = small_information
                            channels = {"mono": 1, "stereo": 2}.get(small_information, None)
                            data[metadata][stream_index]["channels"] = channels if channels else sum([int(number) for number in small_information.split(".")])
                        elif index == 3:
                            data[metadata][stream_index]["sample_fmt"] = small_information
            elif information[:7] == "Chapter":
                metadata = "chapters"
                chapter_index += 1

                data[metadata].append({"id": chapter_index})
                data[metadata][chapter_index]["tags"] = {}

                found_match = re.search(r"start (\d+\.\d+), end (\d+\.\d+)", information)
                data[metadata][chapter_index]["start_time"] = float(found_match.group(1))
                data[metadata][chapter_index]["end_time"] = float(found_match.group(2))
                data[metadata][chapter_index].update({"start": data[metadata][chapter_index]["start_time"] * 1000, "end": data[metadata][chapter_index]["end_time"] * 1000})
            elif metadata:
                found_match = re.search(r"Duration: (.*), start: (.*), bitrate: (.*)$", information)
                if found_match:
                    if found_match.group(1) != "N/A":
                        data["format"]["duration"] = sum([float(value) * (60 ** (2 - index)) for index, value in enumerate(found_match.group(1).split(":"))])
                    data["format"]["start_time"] = float(found_match.group(2))
                    if found_match.group(3) != "N/A":
                        data["format"]["bit_rate"] = int(re.search(r"(\d+)", found_match.group(3)).group(1)) * 1000

                    continue

                found_match = re.search(r"Duration: (.*), bitrate: (.*)$", information)
                if found_match:
                    if found_match.group(1) != "N/A":
                        data["format"]["duration"] = sum([float(value) * (60 ** (2 - index)) for index, value in enumerate(found_match.group(1).split(":"))])
                    if found_match.group(2) != "N/A":
                        data["format"]["bit_rate"] = int(re.search(r"(\d+)", found_match.group(2)).group(1)) * 1000

                    continue

                if information.count(":") == 0:
                    continue

                colon_index = information.index(":")
                tags_dictionary = (data[metadata] if metadata == "format" else data[metadata][program_index if metadata == "programs" else stream_index if metadata == "streams" else chapter_index])["tags"]
                tags_dictionary[information[:colon_index].rstrip()] = information[colon_index + 2:]

        if len(data["format"]["tags"]) == 0:
            del data["format"]["tags"]

        for key, index in [("programs", program_index), ("streams", stream_index), ("chapters", chapter_index)]:
            for sub_index in range(index + 1):
                if len(data[key][sub_index]["tags"]) == 0:
                    del data[key][sub_index]["tags"]

        return data

    @classmethod
    def create_pipe(self, path: str, position: Union[int, float] = 0, stream: int = 0, encoding: Optional[str] = None, data_format: Any = None, use_ffmpeg: bool = False, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe", loglevel: str = "quiet") -> Tuple[subprocess.Popen, Dict[str, Any], Dict[str, Any]]:
        """
        Return a pipe contains the output of `ffmpeg`, a dict contains the file's information and a dict contains the stream's information. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        path: Path to the file to create pipe.

        position (optional): Where to set the audio's position in seconds.

        stream (optional): Which stream to use if the file has more than 1 audio streams. Use the default stream if the given stream is invalid.

        encoding (optional): Encoding for decoding. Use the default encoding if the given encoding is `None`.

        data_format (optional): Output data format for `ffmpeg`. Use the format from the previous `set_format` function call if the given data format is `None`.

        use_ffmpeg (optional): Specifies whether to use `ffmpeg` or `ffprobe` to get the file's information.

        ffmpeg_path (optional): Path to `ffmpeg`.

        ffprobe_path (optional): Path to `ffprobe`.

        loglevel (optional): Logging level and flags used by `ffmpeg`.
        """
        if type(path) != str:
            raise TypeError("Path must be a string.")

        if type(position) != int and type(position) != float:
            raise TypeError("Position must be an integer/a float.")
        elif position < 0:
            position = 0

        if type(stream) != int:
            raise TypeError("Stream must be an integer.")

        if encoding != None and type(encoding) != str:
            raise TypeError("Encoding must be None/a string.")

        if data_format == None:
            try:
                data_format = self.ffmpeg_format
            except AttributeError:
                raise ValueError("Output data format must be specified.") from None

        if type(ffmpeg_path) != str:
            raise TypeError("FFmpeg path must be a string.")

        if type(ffprobe_path) != str:
            raise TypeError("FFprobe path must be a string.")

        if type(loglevel) != str:
            raise TypeError("Loglevel must be a string.")

        information = self.get_information(path, encoding, use_ffmpeg, ffmpeg_path if use_ffmpeg else ffprobe_path)
        streams = information["streams"]

        audio_streams = []
        for data in streams:
            if data["codec_type"] == "audio":
                audio_streams.append(data)

        if len(audio_streams) == 0:
            raise ValueError("The file doesn't contain audio.")
        elif stream < 0 or stream >= len(audio_streams):
            stream = 0

        creationflags = 0
        if platform.system() == "Windows":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            return subprocess.Popen([ffmpeg_path, "-nostdin", "-accurate_seek", "-vn", "-loglevel", loglevel, "-ss", str(position), "-i", path, "-map", f"0:a:{stream}", "-f", data_format, "pipe:1"], stdout = subprocess.PIPE, creationflags = creationflags), information, audio_streams[stream]
        except FileNotFoundError:
            raise FileNotFoundError("No ffmpeg found on your system. Make sure you've it installed and you can try specifying the ffmpeg path.") from None

    def change_attributes(self, path: Optional[str] = None, stream: int = 0, chunk: int = 4096, frames_per_buffer: Union[int, Any] = pyaudio.paFramesPerBufferUnspecified, encoding: Optional[str] = None, use_ffmpeg: bool = False, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        """
        An easier way to change some attributes.

        Parameters
        ----------

        path (optional): Path to the file contains audio.

        stream (optional): Which stream to use if the file has more than 1 audio streams. Use the default stream if the given stream is invalid.

        chunk (optional): Number of bytes per chunk when playing audio.

        frames_per_buffer (optional): Number of frames per buffer. Defaults to `pyaudio.paFramesPerBufferUnspecified`.

        encoding (optional): Encoding for decoding. Use the default encoding if the given encoding is `None`.

        use_ffmpeg (optional): Specifies whether to use `ffmpeg` or `ffprobe` to get the file's information.

        ffmpeg_path (optional): Path to `ffmpeg`.

        ffprobe_path (optional): Path to `ffprobe`.
        """
        if path != None and type(path) != str:
            raise TypeError("Path must be None/a string.")

        if type(stream) != int:
            raise TypeError("Stream must be an integer.")

        if type(chunk) != int:
            raise TypeError("Chunk must be an integer.")
        elif chunk <= 0:
            raise ValueError("Chunk must be greater than 0.")

        if frames_per_buffer != pyaudio.paFramesPerBufferUnspecified and type(frames_per_buffer) != int:
            raise TypeError("Frames per buffer must be pyaudio.paFramesPerBufferUnspecified/an integer.")
        elif type(frames_per_buffer) == int and frames_per_buffer < 0:
            raise ValueError("Frames per buffer must be non-negative.")

        if encoding != None and type(encoding) != str:
            raise TypeError("Encoding must be None/a string.")

        if type(ffmpeg_path) != str:
            raise TypeError("FFmpeg path must be a string.")

        if type(ffprobe_path) != str:
            raise TypeError("FFprobe path must be a string.")

        self.path = path
        self.stream = stream
        self.chunk = chunk
        self.frames_per_buffer
        self.encoding = encoding
        self.use_ffmpeg = use_ffmpeg
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def set_format(self, data_format: Any = SInt16) -> None:
        """
        Set output data format. Defaults to `simple_pygame.SInt16`.

        Parameters
        ----------

        data_format (optional): Specifies what format to use.
        """
        if data_format == SInt8:
            self.pyaudio_format = pyaudio.paInt8
            self.ffmpeg_format = "s8"
            self.audioop_format = 1
        elif data_format == SInt16:
            self.pyaudio_format = pyaudio.paInt16
            self.ffmpeg_format = "s16le" if sys.byteorder == "little" else "s16be"
            self.audioop_format = 2
        elif data_format == SInt32:
            self.pyaudio_format = pyaudio.paInt32
            self.ffmpeg_format = "s32le" if sys.byteorder == "little" else "s32be"
            self.audioop_format = 4
        elif data_format == UInt8:
            self.pyaudio_format = pyaudio.paUInt8
            self.ffmpeg_format = "u8"
            self.audioop_format = 1
        else:
            raise ValueError("Invalid format.")

    def get_device_count(self) -> int:
        """
        Return the number of PortAudio Host APIs.
        """
        return self._pa.get_device_count()

    def set_output_device_by_index(self, device_index: Optional[int] = None) -> None:
        """
        Set output device by index.

        Parameters
        ----------

        device_index: Device's index. Set output device to the default output device if the given device index is `None`.
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

    def get_device_info(self, device_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Return device's information.

        Parameters
        ----------

        device_index: Device's index. Return the default output device's information if the given device index is `None`.
        """
        if device_index == None:
            return self._pa.get_default_output_device_info()

        if type(device_index) != int:
            raise TypeError("The device's index must be an integer.")

        if device_index < 0 or device_index > self.get_device_count() - 1:
            raise ValueError("Invalid index.")

        return self._pa.get_device_info_by_index(device_index)

    def play(self, loop: int = 0, start: Union[int, float] = 0, delay: Union[int, float] = 0.1, exception_on_underflow: bool = False) -> None:
        """
        Start the audio. If the audio is currently playing it will be restarted.

        Parameters
        ----------

        loop (optional): How many times to repeat the audio. If the given loop is `-1` repeats indefinitely.

        start (optional): Where the audio starts playing in seconds.

        delay (optional): Interval between each check to determine if the audio has resumed when it's currently pausing in seconds.

        exception_on_underflow (optional): Specifies whether an exception should be thrown (or silently ignored) on buffer underflow. Defaults to `False` for improved performance, especially on slower platforms.
        """
        self.stop()

        if self.path == None:
            raise ValueError("Please specify the path before starting the audio.")

        if type(loop) != int:
            raise TypeError("Loop must be an integer.")
        elif loop < -1:
            raise ValueError("Loop must be -1 or greater.")

        if type(start) != int and type(start) != float:
            raise TypeError("Start position must be an integer/a float.")

        if type(delay) != int and type(delay) != float:
            raise TypeError("Delay must be an integer/a float.")
        elif delay < 0:
            raise ValueError("Delay must be non-negative.")

        self.currently_pause = False
        self.exception = None
        self.information = None
        self.stream_information = None
        self._start = None
        self._reposition = False
        self._terminate = False

        self._position = 0 if start < 0 else start
        self._pause_offset = None
        self._duration = None
        self._chunk_time = None
        self._chunk_length = None

        self._audio_thread = threading.Thread(target = self.audio, args = (self.path, loop, self.stream, self.chunk, self.frames_per_buffer, self.encoding, delay, exception_on_underflow, self.use_ffmpeg, self.ffmpeg_path, self.ffprobe_path))
        self._audio_thread.daemon = True
        self._audio_thread.start()

    def pause(self) -> None:
        """
        Pause the audio if it's currently playing and not pausing. It can be resumed with `resume` function.
        """
        if self.get_busy() and not self.get_pause():
            self.currently_pause = True

    def resume(self) -> None:
        """
        Resume the audio after it has been paused.
        """
        if not self.get_busy() or not self.get_pause():
            return
        self.currently_pause = False

        if self._pause_offset != None:
            self._start = time.monotonic_ns() - self.seconds_to_nanoseconds(self._pause_offset)
        self._pause_offset = None

    def stop(self, delay: Union[int, float] = 0.1) -> None:
        """
        Stop the audio if it's currently playing.

        Parameters
        ----------

        delay (optional): Interval between each check to determine if the audio is currently busy in seconds.
        """
        if type(delay) != int and type(delay) != float:
            raise TypeError("Delay must be an integer/a float.")
        elif delay < 0:
            raise ValueError("Delay must be non-negative.")

        if not self.get_busy():
            return

        self._terminate = True
        while self.get_busy():
            time.sleep(delay)
        self._audio_thread = None

    def join(self, delay: Union[int, float] = 0.1, raise_exception: bool = True) -> None:
        """
        Wait until the audio stops.

        Parameters
        ----------

        delay (optional): Interval between each check to determine if the audio is currently busy in seconds.

        raise_exception (optional): Specifies whether an exception should be thrown (or silently ignored).
        """
        if type(delay) != int and type(delay) != float:
            raise TypeError("Delay must be an integer/a float.")
        elif delay < 0:
            raise ValueError("Delay must be non-negative.")

        while self.get_busy():
            time.sleep(delay)

        if not raise_exception:
            return
        self.get_exception()

    def get_pause(self) -> bool:
        """
        Return `True` if the audio is currently pausing, otherwise `False`.
        """
        return self.currently_pause if self.get_busy() else False

    def set_position(self, position: Union[int, float]) -> None:
        """
        Set the audio's position where the audio will continue to play.

        Parameters
        ----------

        position: Where to set the audio's position in seconds.
        """
        if type(position) != int and type(position) != float:
            raise TypeError("Position must be an integer/a float.")

        if self.get_busy():
            self._position = 0 if position < 0 else position
            self._reposition = True
        else:
            self.play(start = position)

    def get_position(self, digit: Optional[int] = 4) -> Any:
        """
        Return the current audio's position in seconds if the audio currently playing or pausing, `simple_pygame.AudioIsLoading` if the audio is loading, otherwise `simple_pygame.AudioEnded`.

        Parameters
        ----------

        digit (optional): Number of digits for rounding.
        """
        if digit != None and type(digit) != int:
            raise TypeError("Digit must be None/an integer.")

        if not self.get_busy():
            return AudioEnded

        if self._start == None:
            return AudioIsLoading

        position = min([self._chunk_time + (self._pause_offset if self.get_pause() and self._pause_offset != None else min(self.nanoseconds_to_seconds(max(time.monotonic_ns() - self._start, 0)), self._chunk_length)), self._duration][:1 if self._duration == None else 2])
        return position if digit == None else round(position, digit)

    def set_volume(self, volume: Union[int, float]) -> None:
        """
        Set the audio's volume. The volume must be an integer/a float between `0` and `2`, `1` is the original volume.

        Parameters
        ----------

        volume: The audio's volume.
        """
        if type(volume) != int and type(volume) != float:
            raise TypeError("Volume must be an integer/a float.")

        if 0 <= volume <= 2:
            self._volume = round(volume, 2)
        else:
            raise ValueError("Volume must be an integer/a float between 0 and 2.")

    def get_volume(self) -> Union[int, float]:
        """
        Return the audio's volume.
        """
        return self._volume

    def get_busy(self) -> bool:
        """
        Return `True` if the audio is currently playing or pausing, otherwise `False`.
        """
        if not self._audio_thread:
            return False

        return self._audio_thread.is_alive()

    def get_exception(self) -> None:
        """
        If an exception is found then raise it, otherwise do nothing.
        """
        if self.exception:
            raise self.exception

    def audio(self, path: str, loop: int = 0, stream: int = 0, chunk: int = 4096, frames_per_buffer: Union[int, Any] = pyaudio.paFramesPerBufferUnspecified, encoding: Optional[str] = None, delay: Union[int, float] = 0.1, exception_on_underflow: bool = False, use_ffmpeg: bool = False, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        """
        Start the audio. This function is meant for use by the `Class` and not for general use.

        Parameters
        ----------

        path: Path to the file contains audio.

        loop (optional): How many times to repeat the audio. If the given loop is `-1` repeats indefinitely.

        stream (optional): Which stream to use if the file has more than 1 audio streams. Use the default stream if the given stream is invalid.

        chunk (optional): Number of bytes per chunk when playing audio.

        frames_per_buffer (optional): Number of frames per buffer. Defaults to `pyaudio.paFramesPerBufferUnspecified`.

        encoding (optional): Encoding for decoding. Use the default encoding if the given encoding is `None`.

        delay (optional): Interval between each check to determine if the audio has resumed when it's currently pausing in seconds.

        exception_on_underflow (optional): Specifies whether an exception should be thrown (or silently ignored) on buffer underflow. Defaults to `False` for improved performance, especially on slower platforms.

        use_ffmpeg (optional): Specifies whether to use `ffmpeg` or `ffprobe` to get the file's information.

        ffmpeg_path (optional): Path to `ffmpeg`.

        ffprobe_path (optional): Path to `ffprobe`.
        """
        try:
            pyaudio_format, ffmpeg_format, audioop_format = self.pyaudio_format, self.ffmpeg_format, self.audioop_format
            position = 0 if self._position < 0 else self._position

            pipe, self.information, self.stream_information = self.create_pipe(path, position, stream, encoding, ffmpeg_format, use_ffmpeg, ffmpeg_path, ffprobe_path)
            self.stream_information["sample_rate"], self.stream_information["channels"] = int(self.stream_information["sample_rate"]), int(self.stream_information["channels"])
            stream_out = self._pa.open(self.stream_information["sample_rate"], self.stream_information["channels"], pyaudio_format, output = True, output_device_index = self._output_device_index, frames_per_buffer = frames_per_buffer)

            duration = self.stream_information.get("duration", None)
            if duration == None:
                duration = self.information["format"].get("duration", None)
            self._duration = float(duration) if duration != None else duration

            self._chunk_length = chunk / (audioop_format * self.stream_information["channels"] * self.stream_information["sample_rate"])
            self._chunk_time = position if duration == None or position < self._duration else self._duration
            while not self._terminate:
                if self._reposition:
                    position = 0 if self._position < 0 else self._position

                    pipe, self.information, self.stream_information = self.create_pipe(path, position, stream, encoding, ffmpeg_format, use_ffmpeg, ffmpeg_path, ffprobe_path)
                    self._reposition = False

                    self._chunk_time = position if duration == None or position < self._duration else self._duration
                    self._start = time.monotonic_ns()

                if self.get_pause():
                    if self._pause_offset == None:
                        self._pause_offset = min(self.nanoseconds_to_seconds(max(time.monotonic_ns() - self._start, 0)), self._chunk_length) if self._start != None else 0

                    time.sleep(delay)
                    continue

                data = pipe.stdout.read(chunk)
                if data:
                    data = audioop.mul(data, audioop_format, self._volume)

                    if self._start == None:
                        self._start = time.monotonic_ns()

                    stream_out.write(data, exception_on_underflow = exception_on_underflow)

                    self._chunk_time += self._chunk_length
                    self._start = time.monotonic_ns()
                    continue

                if loop == -1:
                    pipe, self.information, self.stream_information = self.create_pipe(path, stream = stream, encoding = encoding, data_format = ffmpeg_format, use_ffmpeg = use_ffmpeg, ffmpeg_path = ffmpeg_path, ffprobe_path = ffprobe_path)
                    self._chunk_time = 0
                    self._start = time.monotonic_ns()
                elif loop > 0:
                    loop -= 1

                    pipe, self.information, self.stream_information = self.create_pipe(path, stream = stream, encoding = encoding, data_format = ffmpeg_format, use_ffmpeg = use_ffmpeg, ffmpeg_path = ffmpeg_path, ffprobe_path = ffprobe_path)
                    self._chunk_time = 0
                    self._start = time.monotonic_ns()
                else:
                    break
        except Exception as exception:
            self.exception = exception
        finally:
            try:
                pipe.terminate()
            except NameError:
                pass
            try:
                if stream_out.is_active():
                    stream_out.stop_stream()
            except (NameError, OSError):
                pass
            try:
                stream_out.close()
            except NameError:
                pass

            self.currently_pause = False

    @classmethod
    def enquote(self, value: Any) -> Any:
        """
        Add single quotation marks at the start and end of a string, while leaving other types unchanged.

        Parameters
        ----------

        value: Any value.
        """
        return f"'{value}'" if type(value) == str else value

    @classmethod
    def nanoseconds_to_seconds(self, time: Union[int, float]) -> Union[int, float]:
        """
        Convert nanoseconds to seconds.

        Parameters
        ----------

        time: Time in nanoseconds.
        """
        if type(time) != int and type(time) != float:
            raise TypeError("Time must be an integer/a float.")
        elif time < 0:
            raise ValueError("Time must be non-negative.")

        return time / 1000000000

    @classmethod
    def seconds_to_nanoseconds(self, time: Union[int, float]) -> Union[int, float]:
        """
        Convert seconds to nanoseconds.

        Parameters
        ----------

        time: Time in seconds.
        """
        if type(time) != int and type(time) != float:
            raise TypeError("Time must be an integer/a float.")
        elif time < 0:
            raise ValueError("Time must be non-negative.")

        return time * 1000000000

    def __str__(self) -> str:
        """
        Return a string which contains the object's information.
        """
        return f"<Audio(path={self.enquote(repr(self.path)[1:-1] if type(self.path) == str else self.path)}, stream={self.enquote(repr(self.stream)[1:-1] if type(self.stream) == str else self.stream)}, chunk={self.enquote(repr(self.chunk)[1:-1] if type(self.chunk) == str else self.chunk)}, frames_per_buffer={self.enquote(repr(self.frames_per_buffer)[1:-1] if type(self.frames_per_buffer) == str else self.frames_per_buffer)}, ffmpeg_path={self.enquote(repr(self.ffmpeg_path)[1:-1] if type(self.ffmpeg_path) == str else self.ffmpeg_path)}, ffprobe_path={self.enquote(repr(self.ffprobe_path)[1:-1] if type(self.ffprobe_path) == str else self.ffprobe_path)})>"

    def __repr__(self) -> str:
        """
        Return a string which contains the object's information.
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
