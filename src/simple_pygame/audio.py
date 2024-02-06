"""
A module for playing audio.

Requirements
------------

- Pyaudio library.

- FFmpeg.

- FFprobe (optional).
"""
import pyaudio, subprocess, threading, time, json, re, sys, os
from .constants import SInt8, SInt16, SInt24, SInt32, UInt8, VideoAndAudioType, VideoType, AudioType, AudioIsLoading, AudioEnded
from .exceptions import BytesDecodeError, NoOutputError, NoAudioError, FFmpegError, FFprobeError
from typing import Optional, Union, BinaryIO, Iterable, Tuple, List, Dict, Any

try:
    import audioop
except ModuleNotFoundError:
    from . import pyaudioop as audioop

class Audio:
    def __init__(self, path: Optional[Union[str, os.PathLike]] = None, stream: int = 0, chunk: int = 4096, frames_per_buffer: Union[int, Any] = pyaudio.paFramesPerBufferUnspecified, data_format: Any = SInt16, encoding: Optional[str] = None, use_ffmpeg: bool = False, loglevel: str = "quiet", ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
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

        data_format (optional): Specifies what output data format to use. Defaults to `simple_pygame.SInt16`.

        encoding (optional): Encoding for decoding. Use the default encoding if the given encoding is `None`.

        use_ffmpeg (optional): Specifies whether to use `ffmpeg` or `ffprobe` to get the file's information.

        loglevel (optional): Logging level and flags used by `ffmpeg`.

        ffmpeg_path (optional): Path to `ffmpeg`.

        ffprobe_path (optional): Path to `ffprobe`.
        """
        if path != None:
            try:
                path = os.fspath(path)
            except TypeError:
                pass

            if not isinstance(path, str):
                raise TypeError("Path must be None/a string/a path-like object.")

        if not isinstance(stream, int):
            raise TypeError("Stream must be an integer.")

        if not isinstance(chunk, int):
            raise TypeError("Chunk must be an integer.")
        elif chunk <= 0:
            raise ValueError("Chunk must be greater than 0.")

        if frames_per_buffer != pyaudio.paFramesPerBufferUnspecified and not isinstance(frames_per_buffer, int):
            raise TypeError("Frames per buffer must be pyaudio.paFramesPerBufferUnspecified/an integer.")
        elif frames_per_buffer != pyaudio.paFramesPerBufferUnspecified and frames_per_buffer < 0:
            raise ValueError("Frames per buffer must be non-negative.")

        if data_format not in (SInt8, SInt16, SInt24, SInt32, UInt8):
            raise ValueError("Invalid data format.")

        if encoding != None and not isinstance(encoding, str):
            raise TypeError("Encoding must be None/a string.")

        if not isinstance(loglevel, str):
            raise TypeError("Loglevel must be a string.")

        if not isinstance(ffmpeg_path, str):
            raise TypeError("FFmpeg path must be a string.")

        if not isinstance(ffprobe_path, str):
            raise TypeError("FFprobe path must be a string.")

        self.path = path
        self.stream = stream
        self.chunk = chunk
        self.frames_per_buffer = frames_per_buffer
        self.set_format(data_format)
        self.encoding = encoding
        self.use_ffmpeg = use_ffmpeg
        self.loglevel = loglevel
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.input_options = ["-accurate_seek"]
        self.output_options = []
        self.currently_pause = False
        self.exception = None
        self.returncode = None
        self.stderr = None
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

    @classmethod
    def get_information(self, path: Union[str, os.PathLike], encoding: Optional[str] = None, use_ffmpeg: bool = False, executable_path: str = "ffprobe") -> Dict[str, Any]:
        """
        Return a dict contains the file's information.

        Parameters
        ----------

        path: Path to the file to get information.

        encoding (optional): Encoding for decoding. Use the default encoding if the given encoding is `None`.

        use_ffmpeg (optional): Specifies whether to use `ffmpeg` or `ffprobe` to get the file's information.

        executable_path (optional): Path to `ffmpeg`/`ffprobe` depends on the value of `use_ffmpeg`.
        """
        try:
            path = os.fspath(path)
        except TypeError:
            pass

        if not isinstance(path, str):
            raise TypeError("Path must be a string/a path-like object.")

        if encoding != None and not isinstance(encoding, str):
            raise TypeError("Encoding must be None/a string.")

        if not isinstance(executable_path, str):
            raise TypeError("FFmpeg/FFprobe path must be a string.")

        try:
            startupinfo = subprocess.STARTUPINFO(dwFlags = subprocess.CREATE_NO_WINDOW)
            creationflags = subprocess.CREATE_NO_WINDOW
        except AttributeError:
            startupinfo = None
            creationflags = 0

        if use_ffmpeg:
            try:
                result = subprocess.run([executable_path, "-i", path], stderr = subprocess.PIPE, startupinfo = startupinfo, creationflags = creationflags, encoding = encoding, text = True)
            except FileNotFoundError:
                raise FFmpegError("No ffmpeg found on your system. Make sure you've it installed and you can try specifying the ffmpeg path.") from None
            except LookupError:
                raise ValueError("Invalid encoding.") from None
            except UnicodeError:
                raise BytesDecodeError(f"""{'Default encoding' if encoding == None else f'Encoding "{encoding}"'} cannot decode the file's information (as bytes) returned by ffmpeg. You can try using other encodings.""") from None

            raw_data = result.stderr.split("\n")[:-1]
            if raw_data[-1] != "At least one output file must be specified":
                raise FFmpegError(raw_data[-1])

            return self.extract_information(raw_data)
        else:
            try:
                return json.loads(subprocess.run([executable_path, "-print_format", "json", "-show_format", "-show_programs", "-show_streams", "-show_chapters", "-i", path], stdout = subprocess.PIPE, stderr = subprocess.DEVNULL, startupinfo = startupinfo, creationflags = creationflags, check = True, encoding = encoding, text = True).stdout)
            except FileNotFoundError:
                raise FFprobeError("No ffprobe found on your system. Make sure you've it installed and you can try specifying the ffprobe path.") from None
            except subprocess.CalledProcessError:
                raise FFprobeError("Invalid ffprobe path or path or data.") from None
            except LookupError:
                raise ValueError("Invalid encoding.") from None
            except UnicodeError:
                raise BytesDecodeError(f"""{'Default encoding' if encoding == None else f'Encoding "{encoding}"'} cannot decode the file's information (as bytes) returned by ffprobe. You can try using other encodings.""") from None

    @staticmethod
    def extract_information(raw_data: Iterable[str]) -> Dict[str, Any]:
        """
        Return a dict contains the file's information.

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
            if not isinstance(information, str):
                raise ValueError("Raw data must contain only strings.")
            elif information == "":
                continue

            information = information.lstrip()
            if information in ("Metadata:", "Chapters:") or information.startswith("["):
                continue
            elif information.startswith("Input"):
                metadata = "format"

                small_information = information.split(", ", 2)[1:]
                data[metadata]["format_name"] = small_information[0]
                data[metadata]["filename"] = re.search(r"'(.*)'", small_information[1]).group(1)
            elif information.startswith("Program"):
                metadata = "programs"
                program_index += 1

                data[metadata].append({"program_num": program_index})
                data[metadata][program_index]["tags"] = {}
            elif information.startswith("Stream"):
                metadata = "streams"
                stream_index += 1

                data[metadata].append({"index": stream_index})
                data[metadata][stream_index]["tags"] = {}
                data[metadata][stream_index]["disposition"] = {"default": 0, "dub": 0, "original": 0, "comment": 0, "lyrics": 0, "karaoke": 0, "forced": 0, "hearing_impaired": 0, "visual_impaired": 0, "clean_effects": 0, "attached_pic": 0, "timed_thumbnails": 0, "captions": 0, "descriptions": 0, "metadata": 0, "dependent": 0, "still_image": 0}

                small_informations = re.split(r", (?![^(]*\))", information)
                for index, small_information in enumerate(small_informations):
                    if index == len(small_informations) - 1:
                        matches = re.search(r"^(.*?)(?: \((.*?)\))?$", small_information)

                        if matches.group(2):
                            small_information = matches.group(1)
                            data[metadata][stream_index]["disposition"][matches.group(2).replace(" ", "_")] = 1

                    if index == 0:
                        matches = re.search(r"((?:Video|Audio)): (.*?)(?: (\(.*?\)))?$", small_information)
                        data[metadata][stream_index]["codec_type"] = matches.group(1).lower()
                        data[metadata][stream_index]["codec_name"] = matches.group(2)

                        if data[metadata][stream_index]["codec_type"] == "audio":
                            data[metadata][stream_index].update({"avg_frame_rate": "0/0", "r_frame_rate": "0/0"})

                        if not matches.group(3):
                            continue

                        sub_matches = re.findall(r"\((.*?)\)", matches.group(3))
                        matches = re.search(r"(.*) / (.*)", sub_matches[0])
                        if matches:
                            data[metadata][stream_index]["codec_tag_string"], data[metadata][stream_index]["codec_tag"] = matches.group(1), matches.group(2)
                        else:
                            data[metadata][stream_index]["profile"] = sub_matches[0]

                        if len(sub_matches) == 1:
                            continue

                        matches = re.search(r"(.*) / (.*)", sub_matches[1])
                        data[metadata][stream_index]["codec_tag_string"], data[metadata][stream_index]["codec_tag"] = matches.group(1), matches.group(2)
                    elif small_information.endswith("kb/s"):
                        data[metadata][stream_index]["bit_rate"] = int(re.search(r"(\d+) kb/s", small_information).group(1)) * 1000
                    elif data[metadata][stream_index]["codec_type"] == "video":
                        if index == 1:
                            matches = re.search(r"^(.*?)(?:\s*\((.*?)\))?$", small_information)
                            data[metadata][stream_index]["pix_fmt"] = matches.group(1)

                            if not matches.group(2):
                                continue

                            sub_matches = matches.group(2).split(", ")
                            sub_matches_len = len(sub_matches)

                            if sub_matches_len == 1:
                                data[metadata][stream_index]["color_range" if sub_matches[0] in ("tv", "pc") else "field_order"] = sub_matches[0]
                                continue
                            data[metadata][stream_index]["color_range"] = sub_matches[0]

                            colors = sub_matches[1].split("/")
                            if len(colors) == 1:
                                data[metadata][stream_index].update({key: colors[0] for key in ("color_space", "color_primaries", "color_transfer")})
                            else:
                                data[metadata][stream_index].update({"color_space": colors[0]} if colors[0] != "unknown" else {})
                                data[metadata][stream_index].update({"color_primaries": colors[1]} if colors[1] != "unknown" else {})
                                data[metadata][stream_index].update({"color_transfer": colors[2]} if colors[2] != "unknown" else {})

                            if sub_matches_len == 3:
                                data[metadata][stream_index]["field_order"] = sub_matches[2]
                        elif small_information.endswith("fps"):
                            data[metadata][stream_index]["avg_frame_rate"] = float(re.search(r"(\d+\.\d+|\d+) fps", small_information).group(1))
                        elif small_information.endswith("tbr"):
                            matches = re.search(r"(\d+\.\d+|\d+)(.*) tbr", small_information)
                            data[metadata][stream_index]["r_frame_rate"] = float(matches.group(1)) * (1000 if matches.group(2) == "k" else 1)
                        elif small_information.endswith("tbn"):
                            matches = re.search(r"(\d+\.\d+|\d+)(.*) tbn", small_information)
                            data[metadata][stream_index]["time_base"] = 1 / (float(matches.group(1)) * (1000 if matches.group(2) == "k" else 1))
                        elif small_information.endswith("tbc"):
                            matches = re.search(r"(\d+\.\d+|\d+)(.*) tbc", small_information)
                            data[metadata][stream_index]["codec_time_base"] = 1 / (float(matches.group(1)) * (1000 if matches.group(2) == "k" else 1))
                        else:
                            matches = re.search(r"(\d+)x(\d+)", small_information)
                            if not matches:
                                matches = re.search(r"SAR (.*) DAR (.*)", small_information)
                                data[metadata][stream_index].update({"sample_aspect_ratio": matches.group(1), "display_aspect_ratio": matches.group(2)})

                                continue

                            width, height = matches.group(1), matches.group(2)
                            data[metadata][stream_index].update({"width": width, "height": height, "coded_width": width, "coded_height": height})

                            matches = re.search(r"\[SAR (.*) DAR (.*)\]", small_information)
                            if not matches:
                                continue

                            data[metadata][stream_index].update({"sample_aspect_ratio": matches.group(1), "display_aspect_ratio": matches.group(2)})
                    elif data[metadata][stream_index]["codec_type"] == "audio":
                        if small_information.endswith("Hz"):
                            data[metadata][stream_index]["sample_rate"] = int(re.search(r"(\d+) Hz", small_information).group(1))
                        elif index == 2:
                            data[metadata][stream_index]["channel_layout"] = small_information
                            channels = {"mono": 1, "stereo": 2}.get(small_information, None)
                            data[metadata][stream_index]["channels"] = channels if channels else sum((int(number) for number in re.findall(r"\b\d+\b", small_information)))
                        elif index == 3:
                            data[metadata][stream_index]["sample_fmt"] = small_information
            elif information.startswith("Chapter"):
                metadata = "chapters"
                chapter_index += 1

                data[metadata].append({"id": chapter_index})
                data[metadata][chapter_index]["tags"] = {}

                matches = re.search(r"start (\d+\.\d+), end (\d+\.\d+)", information)
                data[metadata][chapter_index]["start_time"] = float(matches.group(1))
                data[metadata][chapter_index]["end_time"] = float(matches.group(2))
                data[metadata][chapter_index].update({"start": data[metadata][chapter_index]["start_time"] * 1000, "end": data[metadata][chapter_index]["end_time"] * 1000})
            elif metadata:
                matches = re.search(r"Duration: (.*), start: (.*), bitrate: (.*)$", information)
                if matches:
                    if matches.group(1) != "N/A":
                        data["format"]["duration"] = sum((float(value) * (60 ** (2 - index)) for index, value in enumerate(matches.group(1).split(":"))))
                    data["format"]["start_time"] = float(matches.group(2))
                    if matches.group(3) != "N/A":
                        data["format"]["bit_rate"] = int(re.search(r"(\d+)", matches.group(3)).group(1)) * 1000

                    continue

                matches = re.search(r"Duration: (.*), bitrate: (.*)$", information)
                if matches:
                    if matches.group(1) != "N/A":
                        data["format"]["duration"] = sum((float(value) * (60 ** (2 - index)) for index, value in enumerate(matches.group(1).split(":"))))
                    if matches.group(2) != "N/A":
                        data["format"]["bit_rate"] = int(re.search(r"(\d+)", matches.group(2)).group(1)) * 1000

                    continue

                if information.count(":") == 0:
                    continue

                colon_index = information.index(":")
                tags_dictionary = (data[metadata] if metadata == "format" else data[metadata][program_index if metadata == "programs" else stream_index if metadata == "streams" else chapter_index])["tags"]
                tags_dictionary[information[:colon_index].rstrip()] = information[colon_index + 2:]

        if len(data["format"]["tags"]) == 0:
            del data["format"]["tags"]

        for key, index in (("programs", program_index), ("streams", stream_index), ("chapters", chapter_index)):
            for sub_index in range(index + 1):
                if len(data[key][sub_index]["tags"]) == 0:
                    del data[key][sub_index]["tags"]

        return data

    @staticmethod
    def get_specific_codec_type(information: Dict[str, Any], codec_type: Any = VideoAndAudioType) -> List[Dict[str, Any]]:
        """
        Return a list contains the streams' information of a specific codec type.

        Parameters
        ----------

        information: The file's information.

        codec_type (optional): The codec type used for stream filtering. Defaults to `simple_pygame.VideoAndAudioType`.
        """
        if not isinstance(information, dict):
            raise TypeError("Information must be a dict.")

        try:
            return {
                VideoAndAudioType: information["streams"],
                VideoType: [stream for stream in information["streams"] if stream["codec_type"] == "video"],
                AudioType: [stream for stream in information["streams"] if stream["codec_type"] == "audio"]
            }[codec_type]
        except KeyError:
            raise ValueError("Invalid codec type.") from None

    def create_pipe(self, path: Union[str, os.PathLike], position: Union[int, float] = 0, stream: int = 0, encoding: Optional[str] = None, data_format: Any = None, use_ffmpeg: bool = False, loglevel: str = "quiet", ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe", input_options: Optional[Iterable[str]] = None, output_options: Optional[Iterable[str]] = None) -> Tuple[subprocess.Popen, Dict[str, Any], Dict[str, Any]]:
        """
        Return a pipe contains the output of `ffmpeg`, a dict contains the file's information and a dict contains the stream's information. This function is meant for use by the class and not for general use.

        Parameters
        ----------

        path: Path to the file to create pipe.

        position (optional): Where to set the audio's position in seconds.

        stream (optional): Which stream to use if the file has more than 1 audio streams. Use the default stream if the given stream is invalid.

        encoding (optional): Encoding for decoding. Use the default encoding if the given encoding is `None`.

        data_format (optional): Output data format for `ffmpeg`. Use `self.ffmpeg_format` if the given data format is `None`.

        use_ffmpeg (optional): Specifies whether to use `ffmpeg` or `ffprobe` to get the file's information.

        loglevel (optional): Logging level and flags used by `ffmpeg`.

        ffmpeg_path (optional): Path to `ffmpeg`.

        ffprobe_path (optional): Path to `ffprobe`.

        input_options (optional): Input options for passing to `ffmpeg`. Use `self.input_options` if the given input options is `None`.

        output_options (optional): Output options for passing to `ffmpeg`. Use `self.output_options` if the given output options is `None`.
        """
        try:
            path = os.fspath(path)
        except TypeError:
            pass

        if not isinstance(path, str):
            raise TypeError("Path must be a string/a path-like object.")

        if not isinstance(position, (int, float)):
            raise TypeError("Position must be an integer/a float.")
        elif position < 0:
            position = 0

        if not isinstance(stream, int):
            raise TypeError("Stream must be an integer.")

        if encoding != None and not isinstance(encoding, str):
            raise TypeError("Encoding must be None/a string.")

        if data_format == None:
            data_format = self.ffmpeg_format

        if not isinstance(loglevel, str):
            raise TypeError("Loglevel must be a string.")

        if not isinstance(ffmpeg_path, str):
            raise TypeError("FFmpeg path must be a string.")

        if not isinstance(ffprobe_path, str):
            raise TypeError("FFprobe path must be a string.")

        if input_options == None:
            input_options = self.input_options

        try:
            if any((not isinstance(value, str) for value in iter(input_options))):
                raise ValueError("Input options must contain only strings.")
        except TypeError:
            raise TypeError("Input options is not iterable.") from None

        if output_options == None:
            output_options = self.output_options

        try:
            if any((not isinstance(value, str) for value in iter(output_options))):
                raise ValueError("Output options must contain only strings.")
        except TypeError:
            raise TypeError("Output options is not iterable.") from None

        information = self.get_information(path, encoding, use_ffmpeg, ffmpeg_path if use_ffmpeg else ffprobe_path)
        audio_streams = self.get_specific_codec_type(information, AudioType)

        if len(audio_streams) == 0:
            raise NoAudioError("The file doesn't contain audio.")
        elif stream < 0 or stream >= len(audio_streams):
            stream = 0

        try:
            startupinfo = subprocess.STARTUPINFO(dwFlags = subprocess.CREATE_NO_WINDOW)
            creationflags = subprocess.CREATE_NO_WINDOW
        except AttributeError:
            startupinfo = None
            creationflags = 0

        try:
            return subprocess.Popen([ffmpeg_path, *input_options, "-loglevel", loglevel, "-ss", str(position), "-i", path, *output_options, "-map", f"0:a:{stream}", "-f", data_format, f"pipe:1"], stdin = subprocess.DEVNULL, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = startupinfo, creationflags = creationflags), information, audio_streams[stream]
        except FileNotFoundError:
            raise FFmpegError("No ffmpeg found on your system. Make sure you've it installed and you can try specifying the ffmpeg path.") from None

    def change_attributes(self, path: Optional[Union[str, os.PathLike]] = None, stream: int = 0, chunk: int = 4096, frames_per_buffer: Union[int, Any] = pyaudio.paFramesPerBufferUnspecified, data_format: Any = SInt16, encoding: Optional[str] = None, use_ffmpeg: bool = False, loglevel: str = "quiet", ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        """
        An easier way to change some attributes.

        Parameters
        ----------

        path (optional): Path to the file contains audio.

        stream (optional): Which stream to use if the file has more than 1 audio streams. Use the default stream if the given stream is invalid.

        chunk (optional): Number of bytes per chunk when playing audio.

        frames_per_buffer (optional): Number of frames per buffer. Defaults to `pyaudio.paFramesPerBufferUnspecified`.

        data_format (optional): Specifies what output data format to use. Defaults to `simple_pygame.SInt16`.

        encoding (optional): Encoding for decoding. Use the default encoding if the given encoding is `None`.

        use_ffmpeg (optional): Specifies whether to use `ffmpeg` or `ffprobe` to get the file's information.

        loglevel (optional): Logging level and flags used by `ffmpeg`.

        ffmpeg_path (optional): Path to `ffmpeg`.

        ffprobe_path (optional): Path to `ffprobe`.
        """
        if path != None:
            try:
                path = os.fspath(path)
            except TypeError:
                pass

            if not isinstance(path, str):
                raise TypeError("Path must be None/a string/a path-like object.")

        if not isinstance(stream, int):
            raise TypeError("Stream must be an integer.")

        if not isinstance(chunk, int):
            raise TypeError("Chunk must be an integer.")
        elif chunk <= 0:
            raise ValueError("Chunk must be greater than 0.")

        if frames_per_buffer != pyaudio.paFramesPerBufferUnspecified and not isinstance(frames_per_buffer, int):
            raise TypeError("Frames per buffer must be pyaudio.paFramesPerBufferUnspecified/an integer.")
        elif frames_per_buffer != pyaudio.paFramesPerBufferUnspecified and frames_per_buffer < 0:
            raise ValueError("Frames per buffer must be non-negative.")

        if data_format not in (SInt8, SInt16, SInt24, SInt32, UInt8):
            raise ValueError("Invalid data format.")

        if encoding != None and not isinstance(encoding, str):
            raise TypeError("Encoding must be None/a string.")

        if not isinstance(loglevel, str):
            raise TypeError("Loglevel must be a string.")

        if not isinstance(ffmpeg_path, str):
            raise TypeError("FFmpeg path must be a string.")

        if not isinstance(ffprobe_path, str):
            raise TypeError("FFprobe path must be a string.")

        self.path = path
        self.stream = stream
        self.chunk = chunk
        self.frames_per_buffer
        self.set_format(data_format)
        self.encoding = encoding
        self.use_ffmpeg = use_ffmpeg
        self.loglevel = loglevel
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def set_format(self, data_format: Any = SInt16) -> None:
        """
        Set output data format.

        Parameters
        ----------

        data_format (optional): Specifies what output data format to use. Defaults to `simple_pygame.SInt16`.
        """
        try:
            self.pyaudio_format, self.ffmpeg_format, self.audioop_format = {
                SInt8: (pyaudio.paInt8, "s8", 1),
                SInt16: (pyaudio.paInt16, "s16le" if sys.byteorder == "little" else "s16be", 2),
                SInt24: (pyaudio.paInt24, "s24le" if sys.byteorder == "little" else "s24be", 3),
                SInt32: (pyaudio.paInt32, "s32le" if sys.byteorder == "little" else "s32be", 4),
                UInt8: (pyaudio.paUInt8, "u8", 1)
            }[data_format]
        except KeyError:
            raise ValueError("Invalid data format.") from None

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

        if not isinstance(device_index, int):
            raise TypeError("The device's index must be an integer.")

        if device_index < 0 or device_index > self.get_device_count() - 1:
            raise ValueError("Invalid index.")

        if self.get_device_info(device_index)["maxOutputChannels"] == 0:
            raise NoOutputError("The device doesn't have any output channels.")

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

        if not isinstance(device_index, int):
            raise TypeError("The device's index must be an integer.")

        if device_index < 0 or device_index > self.get_device_count() - 1:
            raise ValueError("Invalid index.")

        return self._pa.get_device_info_by_index(device_index)

    def play(self, loop: int = 0, start: Union[int, float] = 0, delay: Union[int, float] = 0.1, daemon: Optional[bool] = None, exception_on_underflow: bool = False, information: Optional[Dict[str, Any]] = None, stream_information: Optional[Dict[str, Any]] = None) -> None:
        """
        Start the audio. If the audio is currently playing it will be restarted.

        Parameters
        ----------

        loop (optional): How many times to repeat the audio. If the given loop is `-1` repeats indefinitely.

        start (optional): Where the audio starts playing in seconds.

        delay (optional): Interval between each check to determine if the audio has resumed when it's currently pausing in seconds.

        daemon (optional): Specifies whether the audio thread is a daemon thread.

        exception_on_underflow (optional): Specifies whether an exception should be thrown (or silently ignored) on buffer underflow. Defaults to `False` for improved performance, especially on slower platforms.

        information (optional): The file's information. Use the information returned by `create_pipe()` if the given information is `None`.

        stream_information (optional): The stream's information. Use the stream information returned by `create_pipe()` if the given stream information is `None`.
        """
        self.stop()

        if self.path == None:
            raise ValueError("Please specify the path before starting the audio.")

        if self.chunk % self.audioop_format != 0:
            raise ValueError(f"Chunk (which is {self.chunk}) must be a multiple of the format's sample width (which is {self.audioop_format}).")

        if not isinstance(loop, int):
            raise TypeError("Loop must be an integer.")
        elif loop < -1:
            raise ValueError("Loop must be -1 or greater.")

        if not isinstance(start, (int, float)):
            raise TypeError("Start position must be an integer/a float.")

        if not isinstance(delay, (int, float)):
            raise TypeError("Delay must be an integer/a float.")
        elif delay < 0:
            raise ValueError("Delay must be non-negative.")

        if information != None and not isinstance(information, dict):
            raise TypeError("Information must be None/a dict.")

        if stream_information != None and not isinstance(stream_information, dict):
            raise TypeError("Stream information must be None/a dict.")

        self.currently_pause = False
        self.exception = None
        self.returncode = None
        self.stderr = None
        self.information = information
        self.stream_information = stream_information
        self._start = None
        self._reposition = False
        self._terminate = False

        self._position = 0 if start < 0 else start
        self._pause_offset = None
        self._duration = None
        self._chunk_time = None
        self._chunk_length = None

        self._audio_thread = threading.Thread(target = self.audio, args = (self.path, loop, self.stream, delay, daemon, exception_on_underflow), daemon = daemon)
        self._audio_thread.start()

    def pause(self) -> None:
        """
        Pause the audio if it's currently playing and not pausing. It can be resumed with `resume()`.
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
        if not isinstance(delay, (int, float)):
            raise TypeError("Delay must be an integer/a float.")
        elif delay < 0:
            raise ValueError("Delay must be non-negative.")

        if not self.get_busy():
            return

        self._terminate = True
        while self.get_busy():
            time.sleep(delay)
        self._audio_thread = None

    def join(self, timeout: Optional[Union[int, float]] = None, raise_exception: bool = True) -> None:
        """
        Wait until the audio stops.

        Parameters
        ----------

        timeout (optional): Specifies the timeout for the operation (playing the audio) in seconds (or fractions thereof). Block until the thread terminates if the given timeout is `None`.

        raise_exception (optional): Specifies whether an exception should be thrown (or silently ignored).
        """
        if timeout != None and not isinstance(timeout, (int, float)):
            raise TypeError("Timeout must be None/an integer/a float.")

        if self._audio_thread:
            self._audio_thread.join(timeout)

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
        if not isinstance(position, (int, float)):
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
        if digit != None and not isinstance(digit, int):
            raise TypeError("Digit must be None/an integer.")

        if not self.get_busy():
            return AudioEnded

        if self._start == None:
            return AudioIsLoading

        position = min([self._chunk_time + (self._pause_offset if self.get_pause() and self._pause_offset != None else min(self.nanoseconds_to_seconds(max(time.monotonic_ns() - self._start, 0)), self._chunk_length)), self._duration][:1 if self._duration == None else 2])
        return position if digit == None else round(position, digit)

    def set_volume(self, volume: Union[int, float]) -> None:
        """
        Set the audio's volume.

        Parameters
        ----------

        volume: The audio's volume (`1` is the original volume).
        """
        if not isinstance(volume, (int, float)):
            raise TypeError("Volume must be an integer/a float.")

        if volume >= 0:
            self._volume = volume
        else:
            raise ValueError("Volume must be non-negative.")

    def get_volume(self) -> Union[int, float]:
        """
        Return the audio's volume.
        """
        return self._volume

    def get_busy(self) -> bool:
        """
        Return `True` if the audio is currently playing or pausing, otherwise `False`.
        """
        return self._audio_thread.is_alive() if self._audio_thread else False

    def get_exception(self) -> None:
        """
        If an exception is found then raise it, otherwise do nothing.
        """
        if self.exception:
            raise self.exception

    def get_returncode(self) -> Optional[int]:
        """
        Return the returncode of the nearest finished `subprocess.Popen()` since `play()` was called. If there are no finished `subprocess.Popen()`, return `None` instead.
        """
        return self.returncode

    def get_stderr(self) -> Optional[bytes]:
        """
        Return the value read from stderr of the nearest finished `subprocess.Popen()` since `play()` was called. If there are no finished `subprocess.Popen()`, return `None` instead.
        """
        return self.stderr

    def terminate(self) -> None:
        """
        Clean up everything. Be sure to call this method for every instance of the `Audio` class.
        """
        self.stop()
        self._pa.terminate()

    def audio(self, path: Union[str, os.PathLike], loop: int = 0, stream: int = 0, delay: Union[int, float] = 0.1, daemon: Optional[bool] = None, exception_on_underflow: bool = False) -> None:
        """
        Start the audio. This function is meant for use by the class and not for general use.

        Parameters
        ----------

        path: Path to the file contains audio.

        loop (optional): How many times to repeat the audio. If the given loop is `-1` repeats indefinitely.

        stream (optional): Which stream to use if the file has more than 1 audio streams. Use the default stream if the given stream is invalid.

        delay (optional): Interval between each check to determine if the audio has resumed when it's currently pausing in seconds.

        daemon (optional): Specifies whether the read thread is a daemon thread.

        exception_on_underflow (optional): Specifies whether an exception should be thrown (or silently ignored) on buffer underflow. Defaults to `False` for improved performance, especially on slower platforms.
        """
        def create_pipe_wrapper(previous_pipe: Optional[subprocess.Popen] = None, read_thread: Optional[threading.Thread] = None, create_new_pipe: bool = True) -> Optional[Tuple[subprocess.Popen, threading.Thread]]:
            """
            A wrapper for `create_pipe()`. This function closes the previous pipe (if it's given) then it returns a pipe contains the output of `ffmpeg` with a `threading.Thread` object (if `create_new_pipe` is `True`).

            Parameters
            ----------

            previous_pipe (optional): The pipe returned by `create_pipe_wrapper()` in the previous call. If it's given, clean it up.

            read_thread (optional): The `threading.Thread` object returned by `create_pipe_wrapper()` in the previous call. If it's given, clean it up.

            create_new_pipe (optional): Specifies whether to create and return a new pipe.
            """
            if previous_pipe:
                previous_pipe.stdout.close()
                previous_pipe.terminate()
                previous_pipe.wait()

                self.returncode = previous_pipe.returncode

            if read_thread:
                read_thread.join()
                if previous_pipe:
                    previous_pipe.stderr.close()

            if not create_new_pipe:
                return

            pipe, information, stream_information = self.create_pipe(path, position, stream, encoding, ffmpeg_format, use_ffmpeg, loglevel, ffmpeg_path, ffprobe_path, input_options, output_options)
            if self.information == None:
                self.information = information
            if self.stream_information == None:
                self.stream_information = stream_information

            read_thread = threading.Thread(target = read_stderr, args = (pipe.stderr,), daemon = daemon)
            read_thread.start()

            return pipe, read_thread

        def read_stderr(stderr: BinaryIO) -> None:
            """
            Read bytes from stderr and assign it to `stderr` variable of this instance.

            Parameters
            ----------

            stderr: A readable byte stream object.
            """
            self.stderr = stderr.read()

        try:
            chunk, frames_per_buffer, encoding, use_ffmpeg, ffmpeg_path, ffprobe_path, loglevel, input_options, output_options = self.chunk, self.frames_per_buffer, self.encoding, self.use_ffmpeg, self.ffmpeg_path, self.ffprobe_path, self.loglevel, self.input_options, self.output_options
            pyaudio_format, ffmpeg_format, audioop_format = self.pyaudio_format, self.ffmpeg_format, self.audioop_format

            position = 0 if self._position < 0 else self._position
            pipe, read_thread = create_pipe_wrapper()

            sample_rate, channels = int(self.stream_information["sample_rate"]), int(self.stream_information["channels"])
            stream_out = self._pa.open(sample_rate, channels, pyaudio_format, output = True, output_device_index = self._output_device_index, frames_per_buffer = frames_per_buffer)

            duration = self.stream_information.get("duration", None)
            if duration == None:
                duration = self.information["format"].get("duration", None)
            self._duration = float(duration) if duration != None else duration

            self._chunk_length = chunk / (audioop_format * channels * sample_rate)
            self._chunk_time = position if duration == None or position < self._duration else self._duration
            while not self._terminate:
                if self._reposition:
                    position = 0 if self._position < 0 else self._position
                    pipe, read_thread = create_pipe_wrapper(pipe, read_thread)

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

                if loop == 0:
                    break
                elif loop != -1:
                    loop -= 1

                position = 0
                pipe, read_thread = create_pipe_wrapper(pipe, read_thread)

                self._chunk_time = 0
                self._start = time.monotonic_ns()
        except Exception as exception:
            self.exception = exception
        finally:
            try:
                create_pipe_wrapper(pipe, read_thread, False)
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

    @staticmethod
    def nanoseconds_to_seconds(time_in_nanoseconds: Union[int, float]) -> Union[int, float]:
        """
        Convert nanoseconds to seconds.

        Parameters
        ----------

        time_in_nanoseconds: Time in nanoseconds.
        """
        if not isinstance(time_in_nanoseconds, (int, float)):
            raise TypeError("Time must be an integer/a float.")
        elif time_in_nanoseconds < 0:
            raise ValueError("Time must be non-negative.")

        return time_in_nanoseconds / 1000000000

    @staticmethod
    def seconds_to_nanoseconds(time_in_seconds: Union[int, float]) -> Union[int, float]:
        """
        Convert seconds to nanoseconds.

        Parameters
        ----------

        time_in_seconds: Time in seconds.
        """
        if not isinstance(time_in_seconds, (int, float)):
            raise TypeError("Time must be an integer/a float.")
        elif time_in_seconds < 0:
            raise ValueError("Time must be non-negative.")

        return time_in_seconds * 1000000000

    def __enter__(self) -> "Audio":
        """
        Return this instance.
        """
        return self

    def __exit__(self, *args) -> None:
        """
        Clean up everything before exiting.
        """
        self.terminate()
