# Python | ExternalCore/predicate.py | Python 3.12+ | passive identity checks for pinned CPython 3.14 predicates.
"""Compare code and semantic operands as data; never execute a target function.

A matched body is not proof of active dispatch or of operand getter semantics.
Evidence: integration-evidence/predicate-code-v6. Unknown layouts fail closed.
"""
from dataclasses import dataclass
import hashlib
import json
import struct

from .predicate_spec import BASE_IS_ENEMY
from .python_owner import DataReader, PythonLayoutError, TUPLE_TYPE, FALSE, TRUE
from .registry import _pointer

FUNCTION_TYPE = 0x7A135A0
CODE_TYPE = 0x7A28410
BYTES_TYPE = 0x7A16100
_CACHES = bytes.fromhex(BASE_IS_ENEMY["caches_hex"])
_DEOPT = bytes.fromhex(BASE_IS_ENEMY["deopt_hex"])
_VALID = frozenset(BASE_IS_ENEMY["valid_opcodes"])
_EXTENDED_ARG = 69


def canonical_wordcode(raw: bytes) -> tuple[tuple[int,int,int],...]:
    """Normalize ordinary specializations; caches are payload, not opcodes."""
    if not isinstance(raw,bytes) or not 0 < len(raw) <= 65536 or len(raw) % 2:
        raise PythonLayoutError("bounded, nonempty even wordcode is required")
    result, cursor, extension, prefixes = [], 0, 0, 0
    while cursor < len(raw):
        opcode, byte = raw[cursor:cursor+2]
        if opcode not in _VALID or opcode == 0 or opcode >= 234:
            raise PythonLayoutError("unknown/cache/instrumented/executor opcode is unsupported")
        base = _DEOPT[opcode]
        if base not in _VALID or base == 0 or base >= 234:
            raise PythonLayoutError("invalid deoptimization target")
        argument = (extension << 8) | byte
        following = cursor + 2 * (1 + _CACHES[base])
        if following > len(raw):
            raise PythonLayoutError("inline cache exceeds code length")
        result.append((cursor,base,argument))
        if base == _EXTENDED_ARG:
            prefixes += 1
            if prefixes > 3:
                raise PythonLayoutError("extended argument exceeds uint32")
            extension = argument
        else:
            extension, prefixes = 0, 0
        cursor = following
    if prefixes:
        raise PythonLayoutError("dangling extended argument")
    return tuple(result)


def canonical_hash(instructions) -> str:
    return hashlib.sha256(json.dumps(instructions,separators=(",",":")).encode("ascii")).hexdigest()


def tuple_objects(data: DataReader, address: int, *, maximum=64) -> tuple[int,...]:
    """Unlike an MRO, a semantic tuple may be empty or contain repeated objects."""
    if type(maximum) is not int or not 0 <= maximum <= 4096:
        raise ValueError("invalid tuple item budget")
    head = data.read(_pointer(address,"semantic tuple"),32,mask_ranges=((0,8),(24,32)))
    if struct.unpack_from("<Q",head,8)[0] != data.module.address(TUPLE_TYPE):
        raise PythonLayoutError("semantic operand is not an exact pinned tuple")
    count, = struct.unpack_from("<q",head,16)
    if not 0 <= count <= maximum:
        raise PythonLayoutError("tuple exceeds item budget")
    items = struct.unpack(f"<{count}Q",data.read(address+32,count*8))
    for item in items:
        _pointer(item,"tuple item")
    return items


def bytes_value(data: DataReader, address: int, *, maximum=65536) -> bytes:
    if type(maximum) is not int or not 0 <= maximum <= 65536:
        raise ValueError("invalid byte-string budget")
    head = data.read(_pointer(address,"bytes"),32,mask_ranges=((0,8),(24,32)))
    if struct.unpack_from("<Q",head,8)[0] != data.module.address(BYTES_TYPE):
        raise PythonLayoutError("operand is not an exact pinned bytes object")
    count, = struct.unpack_from("<q",head,16)
    if not 0 <= count <= maximum:
        raise PythonLayoutError("bytes operand exceeds length budget")
    raw = data.read(address+32,count+1)
    if raw[-1]:
        raise PythonLayoutError("bytes operand has no terminating zero")
    return raw[:-1]


@dataclass(frozen=True,slots=True)
class PredicateBody:
    function: int
    code: int
    canonical_sha256: str
    filename: str
    qualname: str
    active_dispatch_verified: bool = False
    operand_semantics_verified: bool = False


def base_is_enemy_body(data: DataReader, function: int) -> PredicateBody:
    """Verify all supported operands of the packaged base body, not its label.

    The caller must independently resolve active dispatch and operand semantics.
    Independent passes must compare both trace and result, as the classifier does.
    Adaptive bytes are masked in the trace because cache payloads may mutate;
    their normalized instructions remain part of the returned identity.
    """
    _pointer(function,"Python function")
    if data.u64(function+8) != data.module.address(FUNCTION_TYPE):
        raise PythonLayoutError("predicate is not an exact pinned function")
    code = data.pointer(function+0x30)
    if any(struct.unpack("<3Q",data.read(function+0x38,24))):
        raise PythonLayoutError("predicate has unsupported defaults, keyword defaults or closure")
    if data.u64(code+8) != data.module.address(CODE_TYPE):
        raise PythonLayoutError("predicate code is not an exact pinned code object")
    units, = struct.unpack("<q",data.read(code+0x10,8))
    if units != BASE_IS_ENEMY["byte_length"]//2:
        raise PythonLayoutError("predicate code length differs from the pinned baseline")
    if data.u64(code+0x98) or data.u64(code+0xB0):
        raise PythonLayoutError("predicate executor/monitoring metadata is unsupported")
    values = struct.unpack("<5i",data.read(code+0x30,20))
    metadata = BASE_IS_ENEMY["metadata"]
    expected = tuple(metadata[key] for key in ("flags","argcount","posonlyargcount","kwonlyargcount","stacksize"))
    if values != expected:
        raise PythonLayoutError("predicate signature/flags/stack metadata differs")
    if struct.unpack("<i",data.read(code+0x48,4))[0] != 3 or struct.unpack("<3i",data.read(code+0x50,12)) != (3,0,0):
        raise PythonLayoutError("predicate local/cell/free-variable layout differs")
    constants = tuple_objects(data,data.pointer(code+0x18))
    if constants != (data.module.address(FALSE),data.module.address(TRUE)):
        raise PythonLayoutError("predicate constants differ from exact False/True")
    names = tuple(data.ascii(item) for item in tuple_objects(data,data.pointer(code+0x20)))
    locals_ = tuple(data.ascii(item) for item in tuple_objects(data,data.pointer(code+0x60)))
    if names != tuple(metadata["names"]) or locals_ != tuple(metadata["localsplusnames"]):
        raise PythonLayoutError("predicate attribute/local operands differ")
    if bytes_value(data,data.pointer(code+0x68)) != bytes.fromhex(metadata["localspluskinds"]["hex"]):
        raise PythonLayoutError("predicate local-variable kinds differ")
    if bytes_value(data,data.pointer(code+0x28)) != bytes.fromhex(metadata["exceptiontable"]["hex"]):
        raise PythonLayoutError("predicate exception table differs")
    filename = data.ascii(data.pointer(code+0x70))
    name = data.ascii(data.pointer(code+0x78))
    qualname = data.ascii(data.pointer(code+0x80))
    if filename != BASE_IS_ENEMY["filename"] or name != "IsEnemy" or qualname != BASE_IS_ENEMY["qualname"]:
        raise PythonLayoutError("predicate code source context differs")
    raw = data.read(code+0xD0,units*2,mask_ranges=((0,units*2),))
    instructions = canonical_wordcode(raw)
    identity = canonical_hash(instructions)
    if identity != BASE_IS_ENEMY["canonical_sha256"] or instructions != tuple(map(tuple,BASE_IS_ENEMY["canonical"])):
        raise PythonLayoutError("predicate instructions differ from the pinned baseline")
    return PredicateBody(function,code,identity,filename,qualname)


def inspect_base_is_enemy(reader, module, function: int) -> PredicateBody:
    first, second = DataReader(reader,module), DataReader(reader,module)
    before = base_is_enemy_body(first,function)
    after = base_is_enemy_body(second,function)
    if before != after or first.trace != second.trace:
        raise PythonLayoutError("predicate metadata changed between independent reads")
    return after
