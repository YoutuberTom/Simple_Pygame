"""
The built-in `audioop` module but implemented in Python.
"""
import struct, sys
from array import array
try:
    from math import gcd
except ImportError:
    from fractions import gcd
from builtins import min as builtins_min, max as builtins_max
from typing import Union, Optional, Callable, Generator, Sized, Tuple

AdpcmState = Tuple[int, int]
RatecvState = Tuple[int, Tuple[Tuple[int, int], ...]]
ReadableBuffer = Union[bytes, bytearray, array, memoryview]

is_big_endian = sys.byteorder != "little"

class error(Exception):
    pass

def _check_size(size: int) -> None:
    if size < 1 or size > 4:
        raise error("Size should be 1, 2, 3 or 4")

def _check_params(length: int, size: int) -> None:
    _check_size(size)

    if length % size != 0:
        raise error("not a whole number of frames")

def _get_minval(size: int, signed: bool = True) -> int:
    if not signed:
        return 0
    elif size == 1:
        return -0x80
    elif size == 2:
        return -0x8000
    elif size == 3:
        return -0x800000
    elif size == 4:
        return -0x80000000

    raise NotImplementedError("Unsupported size.")

def _get_maxval(size: int, signed: bool = True) -> int:
    if size == 1:
        return 0x7f if signed else 0xff
    elif size == 2:
        return 0x7fff if signed else 0xffff
    elif size == 3:
        return 0x7fffff if signed else 0xffffff
    elif size == 4:
        return 0x7fffffff if signed else 0xffffffff

    raise NotImplementedError("Unsupported size.")

def _struct_format(size: int, signed: bool) -> str:
    if size == 1:
        return "b" if signed else "B"
    elif size == 2:
        return "h" if signed else "H"
    elif size == 4:
        return "i" if signed else "I"

    raise NotImplementedError("Unsupported size.")

def _pack_int24(buffer: ReadableBuffer, offset: int, value: int) -> None:
    buffer = memoryview(buffer)

    if is_big_endian:
        buffer[offset + 2] = value & 0xff
        buffer[offset + 1] = (value >> 8) & 0xff
        buffer[offset] = (value >> 16) & 0xff
    else:
        buffer[offset] = value & 0xff
        buffer[offset + 1] = (value >> 8) & 0xff
        buffer[offset + 2] = (value >> 16) & 0xff

def _unpack_int24(buffer: ReadableBuffer) -> int:
    if is_big_endian:
        value = (buffer[2] & 0xff) | ((buffer[1] & 0xff) << 8) | ((buffer[0] & 0xff) << 16)
    else:
        value = (buffer[0] & 0xff) | ((buffer[1] & 0xff) << 8) | ((buffer[2] & 0xff) << 16)

    return value - 0x1000000 if value & 0x800000 else value

def _sample_count(buffer: Sized, size: int) -> int:
    return len(buffer) // size

def _get_sample(buffer: ReadableBuffer, size: int, index: int, signed: bool = True) -> int:
    start = index * size
    end = start + size
    buffer = memoryview(buffer)[start:end]

    return _unpack_int24(buffer) if size == 3 else struct.unpack_from(_struct_format(size, signed), buffer)[0]

def _get_samples(buffer: ReadableBuffer, size: int, signed: bool = True) -> Generator[int, None, None]:
    for index in range(_sample_count(buffer, size)):
        yield _get_sample(buffer, size, index, signed)

def _put_sample(buffer: ReadableBuffer, size: int, index: int, value: int, signed: bool = True) -> None:
    _pack_int24(buffer, index * size, value) if size == 3 else struct.pack_into(_struct_format(size, signed), buffer, index * size, value)

def _get_clipfn(size: int, signed: bool = True) -> Callable[[int], int]:
    return lambda value: builtins_min(builtins_max(value, _get_minval(size, signed)), _get_maxval(size, signed))

def _overflow(value: int, size: int, signed: bool = True) -> int:
    if _get_minval(size, signed) <= value <= _get_maxval(size, signed):
        return value

    bits = size * 8
    if signed:
        offset = 2 ** (bits - 1)
        return ((value + offset) % (2 ** bits)) - offset
    return value % (2 ** bits)

def _sum2(fragment_1: bytes, fragment_2: bytes, length: int) -> int:
    return sum(getsample(fragment_1, 2, index) * getsample(fragment_2, 2, index) for index in range(length))

def add(fragment_1: bytes, fragment_2: bytes, width: int) -> bytes:
    """
    Return a fragment which is the addition of the two samples passed as parameters.
    """
    _check_params(len(fragment_1), width)

    if len(fragment_1) != len(fragment_2):
        raise error("Lengths should be the same")

    sample_count = _sample_count(fragment_1, width)
    clip = _get_clipfn(width)
    result = bytearray(len(fragment_1))

    for index in range(sample_count):
        sample1 = getsample(fragment_1, width, index)
        sample2 = getsample(fragment_2, width, index)
        sample = clip(sample1 + sample2)

        _put_sample(result, width, index, sample)

    return bytes(result)

def avg(fragment: bytes, width: int) -> int:
    """
    Return the average over all samples in the fragment.
    """
    _check_params(len(fragment), width)

    sample_count = _sample_count(fragment, width)
    return 0 if sample_count == 0 else sum(_get_samples(fragment, width)) // sample_count

def avgpp(fragment: bytes, width: int) -> int:
    """
    Return the average peak-peak value over all samples in the fragment.
    """
    _check_params(len(fragment), width)

    sample_count = _sample_count(fragment, width)
    if sample_count <= 2:
        return 0

    previous_extreme_valid = False
    previous_extreme = None
    average = 0
    number_of_extremes = 0

    previous_value = getsample(fragment, width, 0)
    value = getsample(fragment, width, 1)
    previous_difference = value - previous_value

    for index in range(1, sample_count):
        value = getsample(fragment, width, index)
        difference = value - previous_value

        if difference * previous_difference < 0:
            if previous_extreme_valid:
                average += abs(previous_value - previous_extreme)
                number_of_extremes += 1

            previous_extreme_valid = True
            previous_extreme = previous_value

        previous_value = value
        if difference != 0:
            previous_difference = difference

    return 0 if number_of_extremes == 0 else average // number_of_extremes

def bias(fragment: bytes, width: int, bias: int) -> bytes:
    """
    Return a fragment that is the original fragment with a bias added to each sample.
    """
    _check_params(len(fragment), width)

    result = bytearray(len(fragment))

    for index, sample in enumerate(_get_samples(fragment, width)):
        sample = _overflow(sample + bias, width)
        _put_sample(result, width, index, sample)

    return bytes(result)

def byteswap(fragment: bytes, width: int) -> bytes:
    """
    Convert big-endian samples to little-endian and vice versa.
    """
    _check_params(len(fragment), width)

    result = bytearray(len(fragment))
    base = width
    next_bump = 0
    bump = 2 * width

    for index in range(len(fragment)):
        base -= 1
        result[index] = fragment[base]

        if base == next_bump:
            base += bump
            next_bump += width

    return bytes(result)

def cross(fragment: bytes, width: int) -> int:
    """
    Return the number of zero crossings in the fragment passed as an argument.
    """
    _check_params(len(fragment), width)

    crossings = -1
    last_sample = 17
    for sample in _get_samples(fragment, width):
        sample = sample < 0
        if sample != last_sample:
            crossings += 1
        last_sample = sample

    return crossings

def findfactor(fragment: bytes, reference: bytes) -> float:
    """
    Return a factor F such that rms(add(fragment, mul(reference, -F))) is minimal.
    """
    if len(fragment) % 2 != 0:
        raise error("Strings should be even-sized")

    if len(fragment) != len(reference):
        raise error("Samples should be same size")

    sample_count = _sample_count(fragment, 2)
    return _sum2(fragment, reference, sample_count) / _sum2(reference, reference, sample_count)

def findfit(fragment: bytes, reference: bytes) -> Tuple[int, float]:
    """
    Try to match reference as well as possible to a portion of fragment.
    """
    if len(fragment) % 2 != 0 or len(reference) % 2 != 0:
        raise error("Strings should be even-sized")

    if len(fragment) < len(reference):
        raise error("First sample should be longer")

    len_fragment = _sample_count(fragment, 2)
    len_reference = _sample_count(reference, 2)

    sum_ri_2 = _sum2(reference, reference, len_reference)
    sum_aij_2 = _sum2(fragment, fragment, len_reference)
    sum_aij_ri = _sum2(fragment, reference, len_reference)

    result = (sum_ri_2 * sum_aij_2 - sum_aij_ri * sum_aij_ri) / sum_aij_2

    best_result = result
    best_index = 0

    for index in range(1, len_fragment - len_reference + 1):
        aj_m1 = _get_sample(fragment, 2, index - 1)
        aj_lm1 = _get_sample(fragment, 2, index + len_reference - 1)

        sum_aij_2 += aj_lm1 ** 2 - aj_m1 ** 2
        sum_aij_ri = _sum2(memoryview(fragment)[index * 2:], reference, len_reference)

        result = (sum_ri_2 * sum_aij_2 - sum_aij_ri * sum_aij_ri) / sum_aij_2

        if result < best_result:
            best_result = result
            best_index = index

    factor = _sum2(memoryview(fragment)[best_index * 2:], reference, len_reference) / sum_ri_2
    return best_index, factor

def findmax(fragment: bytes, length: int) -> int:
    """
    Search fragment for a slice of specified number of samples with maximum energy.
    """
    sample_count = _sample_count(fragment, 2)

    if len(fragment) % 2 != 0:
        raise error("Strings should be even-sized")

    if length < 0 or sample_count < length:
        raise error("Input sample should be longer")

    if sample_count == 0:
        return 0

    result = _sum2(fragment, fragment, length)
    best_result = result
    best_index = 0

    for index in range(1, sample_count - length + 1):
        sample_leaving_window = getsample(fragment, 2, index - 1)
        sample_entering_window = getsample(fragment, 2, index + length - 1)

        result -= sample_leaving_window ** 2
        result += sample_entering_window ** 2

        if result > best_result:
            best_result = result
            best_index = index

    return best_index

def getsample(fragment: bytes, width: int, index: int) -> int:
    """
    Return the value of sample index from the fragment.
    """
    _check_params(len(fragment), width)

    if not (0 <= index < len(fragment) // width):
        raise error("Index out of range")

    return _get_sample(fragment, width, index)

def lin2lin(fragment: bytes, width: int, new_width: int) -> bytes:
    """
    Convert samples between 1-, 2-, 3- and 4-byte formats.
    """
    _check_params(len(fragment), width)
    _check_size(new_width)

    if width == new_width:
        return fragment

    new_len = (len(fragment) // width) * new_width
    result = bytearray(new_len)

    for index in range(_sample_count(fragment, width)):
        sample = _get_sample(fragment, width, index)
        if width == 1:
            sample <<= 24
        elif width == 2:
            sample <<= 16
        elif width == 3:
            sample <<= 8
        if new_width == 1:
            sample >>= 24
        elif new_width == 2:
            sample >>= 16
        elif new_width == 3:
            sample >>= 8

        sample = _overflow(sample, new_width)
        _put_sample(result, new_width, index, sample)

    return bytes(result)

def max(fragment: bytes, width: int) -> int:
    """
    Return the maximum of the absolute value of all samples in a fragment.
    """
    _check_params(len(fragment), width)

    return 0 if len(fragment) == 0 else builtins_max(abs(sample) for sample in _get_samples(fragment, width))

def maxpp(fragment: bytes, width: int) -> int:
    """
    Return the maximum peak-peak value in the sound fragment.
    """
    _check_params(len(fragment), width)

    sample_count = _sample_count(fragment, width)
    if sample_count <= 1:
        return 0

    previous_extreme_valid = False
    previous_extreme = None
    maximum = 0

    previous_value = getsample(fragment, width, 0)
    value = getsample(fragment, width, 1)
    previous_difference = value - previous_value

    for index in range(1, sample_count):
        value = getsample(fragment, width, index)
        difference = value - previous_value

        if difference * previous_difference < 0:
            if previous_extreme_valid:
                extreme_difference = abs(previous_value - previous_extreme)
                if extreme_difference > maximum:
                    maximum = extreme_difference

            previous_extreme_valid = True
            previous_extreme = previous_value

        previous_value = value
        if difference != 0:
            previous_difference = difference

    return maximum

def minmax(fragment: bytes, width: int) -> Tuple[int, int]:
    """
    Return the minimum and maximum values of all samples in the sound fragment.
    """
    _check_params(len(fragment), width)

    min_sample, max_sample = 0x7fffffff, -0x80000000
    for sample in _get_samples(fragment, width):
        min_sample = builtins_min(sample, min_sample)
        max_sample = builtins_max(sample, max_sample)

    return min_sample, max_sample

def mul(fragment: bytes, width: int, factor: Union[int, float]) -> bytes:
    """
    Return a fragment that has all samples in the original fragment multiplied by the floating-point value factor.
    """
    _check_params(len(fragment), width)

    clip = _get_clipfn(width)
    result = bytearray(len(fragment))

    for index, sample in enumerate(_get_samples(fragment, width)):
        sample = clip(int(sample * factor))
        _put_sample(result, width, index, sample)

    return bytes(result)

def ratecv(fragment: bytes, width: int, number_of_channels: int, in_rate: int, out_rate: int, state: Optional[RatecvState], weight_A: int = 1, weight_B: int = 0) -> Tuple[bytes, RatecvState]:
    """
    Convert the frame rate of the input fragment.
    """
    _check_params(len(fragment), width)

    if number_of_channels < 1:
        raise error("# of channels should be >= 1")

    bytes_per_frame = width * number_of_channels
    frame_count = len(fragment) // bytes_per_frame

    if bytes_per_frame // number_of_channels != width:
        raise OverflowError("width * number_of_channels too big for a C int")

    if weight_A < 1 or weight_B < 0:
        raise error("weight_A should be >= 1, weight_B should be >= 0")

    if len(fragment) % bytes_per_frame != 0:
        raise error("not a whole number of frames")

    if in_rate <= 0 or out_rate <= 0:
        raise error("sampling rate not > 0")

    d = gcd(in_rate, out_rate)
    in_rate //= d
    out_rate //= d

    if state is None:
        d = -out_rate
        previous_index = [0] * number_of_channels
        current_index = [0] * number_of_channels
    else:
        d, samples = state

        if len(samples) != number_of_channels:
            raise error("illegal state argument")

        previous_index, current_index = zip(*samples)
        previous_index, current_index = list(previous_index), list(current_index)

    result = bytearray((frame_count // in_rate + 1) * out_rate * bytes_per_frame)

    samples = _get_samples(fragment, width)
    out_index = 0
    while True:
        while d < 0:
            if frame_count == 0:
                samples = zip(previous_index, current_index)
                return_value = bytes(result)

                trim_index = out_index * bytes_per_frame - len(return_value)
                return_value = bytearray(return_value)[:trim_index * width]

                return (bytes(return_value), (d, tuple(samples)))

            for channel in range(number_of_channels):
                previous_index[channel] = current_index[channel]
                current_index[channel] = ((weight_A * next(samples) + weight_B * previous_index[channel]) / (weight_A + weight_B))

            frame_count -= 1
            d += out_rate

        while d >= 0:
            for channel in range(number_of_channels):
                current_out = int((previous_index[channel] * d + current_index[channel] * (out_rate - d)) / out_rate)
                _put_sample(result, width, out_index, _overflow(current_out, width))
                out_index += 1

            d -= in_rate

def reverse(fragment: bytes, width: int) -> bytes:
    """
    Reverse the samples in a fragment and returns the modified fragment.
    """
    _check_params(len(fragment), width)

    sample_count = _sample_count(fragment, width)
    result = bytearray(len(fragment))

    for index, sample in enumerate(_get_samples(fragment, width)):
        _put_sample(result, width, sample_count - index - 1, sample)

    return bytes(result)

def rms(fragment: bytes, width: int) -> int:
    """
    Return the root-mean-square of the fragment, i.e. sqrt(sum(S_i^2)/n).
    """
    _check_params(len(fragment), width)

    sample_count = _sample_count(fragment, width)
    return 0 if sample_count == 0 else int((sum(sample ** 2 for sample in _get_samples(fragment, width)) // sample_count) ** 0.5)

def tomono(fragment: bytes, width: int, left_factor: float, right_factor: float) -> bytes:
    """
    Convert a stereo fragment to a mono fragment.
    """
    _check_params(len(fragment), width)

    sample_count = _sample_count(fragment, width)
    clip = _get_clipfn(width)
    result = bytearray(len(fragment) // 2)

    for index in range(0, sample_count, 2):
        l_sample = getsample(fragment, width, index)
        r_sample = getsample(fragment, width, index + 1)
        sample = (l_sample * left_factor) + (r_sample * right_factor)
        sample = int(clip(sample))

        _put_sample(result, width, index // 2, sample)

    return bytes(result)

def tostereo(fragment: bytes, width: int, left_factor: float, right_factor: float) -> bytes:
    """
    Generate a stereo fragment from a mono fragment.
    """
    _check_params(len(fragment), width)

    sample_count = _sample_count(fragment, width)
    clip = _get_clipfn(width)
    result = bytearray(len(fragment) * 2)

    for index in range(sample_count):
        sample = _get_sample(fragment, width, index)
        l_sample = clip(sample * left_factor)
        r_sample = clip(sample * right_factor)

        _put_sample(result, width, index * 2, l_sample)
        _put_sample(result, width, index * 2 + 1, r_sample)

    return bytes(result)

def adpcm2lin(fragment: bytes, width: int, state: Optional[AdpcmState]) -> Tuple[bytes, AdpcmState]:
    """
    Decode an Intel/DVI ADPCM coded fragment to a linear fragment.
    """
    raise NotImplementedError("adpcm2lin() hasn't been implemented.")

def alaw2lin(fragment: bytes, width: int) -> bytes:
    """
    Convert sound fragments in a-LAW encoding to linearly encoded sound fragments.
    """
    raise NotImplementedError("alaw2lin() hasn't been implemented.")

def lin2adpcm(fragment: bytes, width: int, state: Optional[AdpcmState]) -> Tuple[bytes, AdpcmState]:
    """
    Convert samples to 4 bit Intel/DVI ADPCM encoding.
    """
    raise NotImplementedError("lin2adpcm() hasn't been implemented.")

def lin2alaw(fragment: bytes, width: int) -> bytes:
    """
    Convert samples in the audio fragment to a-LAW encoding.
    """
    raise NotImplementedError("lin2alaw() hasn't been implemented.")

def lin2ulaw(fragment: bytes, width: int) -> bytes:
    """
    Convert samples in the audio fragment to u-LAW encoding.
    """
    raise NotImplementedError("lin2ulaw() hasn't been implemented.")

def ulaw2lin(fragment: bytes, width: int) -> bytes:
    """
    Convert sound fragments in u-LAW encoding to linearly encoded sound fragments.
    """
    raise NotImplementedError("ulaw2lin() hasn't been implemented.")
