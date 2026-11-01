# Python | ExternalCore/python_managed.py | Python 3.12+ | bounded CPython 3.14 GIL snapshot reads.
"""Read stored managed attributes; never materialize dictionaries or run getters.

Evidence: StaticAnalysis/integration-evidence/native-properties-v6/managed-models.
The caller validates the object's type; unknown layouts raise PythonLayoutError.
"""
import struct

from .python_owner import DICT_TYPE, STR_TYPE, PythonLayoutError
from .registry import _pointer


_MANAGED = 0x10
_INLINE = 0x4
_HEAPTYPE = 0x200
_MAX_SHARED = 30


def _ptr(value, label):
    try:
        return _pointer(value, label)
    except ValueError as exc:
        raise PythonLayoutError(str(exc)) from exc


def _shared_keys(data, address, capacity):
    """Validate the shared schema, independently of this instance's live count."""
    _ptr(address, "shared dict keys")
    head = data.read(address, 32)
    log_size, log_bytes, kind = head[8:11]
    usable, count = struct.unpack_from("<2q", head, 16)
    if kind != 2 or not 0 <= log_size <= 10 or not log_size <= log_bytes <= log_size + 3:
        raise PythonLayoutError("unsupported shared key table")
    table_capacity = ((1 << log_size) * 2) // 3
    if not 0 <= count <= capacity or usable < 0 or count + usable > table_capacity:
        raise PythonLayoutError("invalid shared key counts")
    width = 1 << (log_bytes - log_size)
    indices = data.read(address + 32, 1 << log_bytes)
    referenced = []
    for (index,) in struct.iter_unpack("<" + {1: "b", 2: "h", 4: "i", 8: "q"}[width], indices):
        if index in (-1, -2):
            continue
        if not 0 <= index < count:
            raise PythonLayoutError("shared dict index is outside its entry array")
        referenced.append(index)
    if len(referenced) != count or set(referenced) != set(range(count)):
        raise PythonLayoutError("shared key index/schema mismatch")
    entries = data.read(address + 32 + (1 << log_bytes), count * 16)
    return [_ptr(struct.unpack_from("<Q", entries, i * 16)[0], "shared Unicode key")
            for i in range(count)]


def _values_header(data, address, *, inline):
    _ptr(address, "dict values")
    capacity, size, embedded, valid = data.read(address, 4)
    if not 1 <= capacity <= _MAX_SHARED or size > capacity or embedded not in (0, 1):
        raise PythonLayoutError("invalid managed values capacity/size/embedded flag")
    # Standalone split values leave 'valid' uninitialized in new_values().
    if (inline and embedded != 1) or (embedded == 1 and valid != 1):
        raise PythonLayoutError("invalid embedded managed values")
    return capacity, size


def _attributes(data, keys, values, *, capacity, size, used=None):
    key_objects = _shared_keys(data, keys, capacity)
    pointers = struct.unpack(f"<{capacity}Q", data.read(values + 8, capacity * 8))
    if any(pointers[len(key_objects):]):
        raise PythonLayoutError("managed value has no corresponding shared key")
    active = sum(bool(p) for p in pointers)
    if active != size or (used is not None and active != used):
        raise PythonLayoutError("managed values/live count mismatch")
    result = {}
    seen = set()
    for key, value in zip(key_objects, pointers):
        head = data.read(key, 40, mask_ranges=((0, 8), (24, 32)))
        if struct.unpack_from("<Q", head, 8)[0] != data.module.address(STR_TYPE):
            raise PythonLayoutError("shared key is not an exact pinned Unicode object")
        length, = struct.unpack_from("<q", head, 16)
        state, = struct.unpack_from("<I", head, 32)
        if length < 0:
            raise PythonLayoutError("negative shared Unicode length")
        if value:
            _ptr(value, "managed attribute value")
        # Other valid Unicode names cannot match the supported ASCII namespace.
        if length > 512 or state & 0x60 != 0x60 or (state >> 2) & 7 != 1:
            continue
        name = data.ascii(key)
        if name in seen:
            raise PythonLayoutError("duplicate shared attribute name")
        seen.add(name)
        if value:
            result[name] = value
    return result


def _materialized(data, dictionary):
    _ptr(dictionary, "managed dictionary")
    head = data.read(dictionary, 48, mask_ranges=((0, 8),))
    if struct.unpack_from("<Q", head, 8)[0] != data.module.address(DICT_TYPE):
        raise PythonLayoutError("managed storage is not an exact pinned dict")
    used, = struct.unpack_from("<q", head, 16)
    keys, values = struct.unpack_from("<2Q", head, 32)
    if not values:
        return data.dictionary(dictionary)
    capacity, size = _values_header(data, values, inline=False)
    if not 0 <= used <= capacity:
        raise PythonLayoutError("invalid split dictionary live count")
    return _attributes(data, keys, values, capacity=capacity, size=size, used=used)


def managed_instance_dict(data, obj, type_head) -> dict[str, int]:
    """Return supported stored ASCII attributes from an already validated type."""
    _ptr(obj, "managed Python instance")
    if len(type_head) < 0xAC:
        raise PythonLayoutError("truncated managed type metadata")
    flags, = struct.unpack_from("<I", type_head, 0xA8)
    if not flags & _MANAGED:
        raise PythonLayoutError("type has no managed instance dictionary")
    if flags & _INLINE:
        basicsize, itemsize = struct.unpack_from("<2q", type_head, 0x20)
        if not flags & _HEAPTYPE or itemsize or not 16 <= basicsize <= 8192 or basicsize % 8:
            raise PythonLayoutError("unsupported inline instance size/type")
        values = obj + basicsize
        valid = data.read(values + 3, 1)[0]
        if valid not in (0, 1):
            raise PythonLayoutError("invalid inline values validity flag")
        if valid:
            capacity, size = _values_header(data, values, inline=True)
            cls = _ptr(data.u64(obj + 8), "managed instance type")
            keys = data.u64(cls + 0x370)
            return _attributes(data, keys, values, capacity=capacity, size=size)
    # A plain, untagged pointer; do not consult a negative tp_dictoffset here.
    dictionary = data.u64(obj - 0x18)
    return _materialized(data, dictionary) if dictionary else {}
