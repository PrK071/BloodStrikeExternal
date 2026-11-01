# Python | ExternalCore/python_values.py | Python 3.12+ | bounded scalar data decoding for pinned CPython 3.14.
"""No conversion slots, __int__, __float__, __bool__ or target code are invoked.

Evidence: integration-evidence/python-values-v6/scalar-layout-proof.json.
The exact builtin types are supported; subclasses/descriptors remain unsupported.
Numeric values expose representation only, never gameplay meaning by themselves.
"""
from dataclasses import dataclass
import math
import struct

from .python_owner import DataReader, PythonLayoutError, STR_TYPE, TRUE, FALSE, NONE
from .registry import _pointer

INT_TYPE = 0x7A18530
FLOAT_TYPE = 0x7A12E10


@dataclass(frozen=True, slots=True)
class ScalarValue:
    address: int
    kind: str
    value: bool | int | float | str | None


def read_scalar(data: DataReader, address: int, *, max_int_bits=128, max_ascii_length=512) -> ScalarValue:
    if type(max_int_bits) is not int or not 1 <= max_int_bits <= 4096:
        raise ValueError("integer bit budget must be in [1,4096]")
    if type(max_ascii_length) is not int or not 0 <= max_ascii_length <= 4096:
        raise ValueError("ASCII length budget must be in [0,4096]")
    _pointer(address,"Python scalar")
    if address == data.module.address(NONE):
        return ScalarValue(address,"none",None)
    if address == data.module.address(TRUE):
        return ScalarValue(address,"bool",True)
    if address == data.module.address(FALSE):
        return ScalarValue(address,"bool",False)
    head = data.read(address,24,mask_ranges=((0,8),))
    kind, = struct.unpack_from("<Q",head,8)
    if kind == data.module.address(INT_TYPE):
        tag, = struct.unpack_from("<Q",head,16)
        count, sign = tag >> 3, tag & 3
        if sign == 3 or (count == 0 and sign != 1) or (count and sign not in (0,2)):
            raise PythonLayoutError("invalid long sign/count tag")
        if count > (max_int_bits+29)//30:
            raise PythonLayoutError("long exceeds the configured bit budget")
        # A zero still has one allocated digit, whose contents are undefined.
        if count == 0:
            return ScalarValue(address,"int",0)
        words = struct.unpack(f"<{count}I",data.read(address+24,4*count))
        if not words[-1] or any(word >= 1 << 30 for word in words):
            raise PythonLayoutError("non-normalized or invalid long digits")
        value = sum(word << (30*index) for index,word in enumerate(words))
        if value.bit_length() > max_int_bits:
            raise PythonLayoutError("long exceeds the configured bit budget")
        return ScalarValue(address,"int",-value if sign == 2 else value)
    if kind == data.module.address(FLOAT_TYPE):
        value, = struct.unpack_from("<d",head,16)
        if not math.isfinite(value):
            raise PythonLayoutError("nonfinite Python float is not a usable scalar")
        return ScalarValue(address,"float",value)
    if kind == data.module.address(STR_TYPE):
        return ScalarValue(address,"str",data.ascii(address,max_length=max_ascii_length))
    raise PythonLayoutError("unsupported scalar type; no conversion code is executed")
