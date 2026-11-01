# Python | ExternalCore/rtti.py | Python 3.12+ | conservative MSVC x64 RTTI adjustment.
"""Resolve one unique public nonvirtual base; unsupported casts are rejected.

This reads RTTI data, never calls a virtual function or the native dynamic_cast.
It is intentionally narrower than C++ dynamic_cast (no virtual base/construction
displacement support). A successful result is not a lifetime guarantee.
"""
from dataclasses import dataclass
import struct

from .build import ModuleIdentity
from .memory import MemoryReader, read_exact

IENTITY_DESCRIPTOR_RVA = 0x7DE5D78  # GetEntityPosition conversion: RVA 2d85342.


class RttiResolutionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class BaseResolution:
    address: int
    complete_object: int
    dynamic_descriptor_rva: int
    base_descriptor_rva: int


def resolve_nonvirtual_base(reader: MemoryReader, module: ModuleIdentity, pointer: int,
                            target_descriptor_rva: int = IENTITY_DESCRIPTOR_RVA) -> BaseResolution:
    target = module.address(target_descriptor_rva, 16)
    vtable, = struct.unpack("<Q", read_exact(reader, pointer, 8))
    if not module.base + 8 <= vtable < module.base + module.size:
        raise RttiResolutionError("vtable is outside the pinned module")
    col, = struct.unpack("<Q", read_exact(reader, vtable - 8, 8))
    module.address(col - module.base, 24)
    sig, offset, cd_offset, td, chd, self_rva = struct.unpack("<6I", read_exact(reader, col, 24))
    if sig != 1 or module.base + self_rva != col or cd_offset:
        raise RttiResolutionError("unsupported COL signature/self/construction displacement")
    module.address(td, 16)
    hierarchy = module.address(chd, 16)
    signature, attributes, count, array_rva = struct.unpack("<4I", read_exact(reader, hierarchy, 16))
    if signature or not 1 <= count <= 256 or attributes & 4:
        raise RttiResolutionError("invalid, excessive or ambiguous class hierarchy")
    array = module.address(array_rva, count * 4)
    bases = struct.unpack(f"<{count}I", read_exact(reader, array, count * 4))
    matches = []
    for index, base_rva in enumerate(bases):
        descriptor = module.address(base_rva, 24)
        base_td, contained, mdisp, pdisp, vdisp, flags = struct.unpack(
            "<IIiiiI", read_exact(reader, descriptor, 24))
        module.address(base_td, 16)
        if index == 0 and (base_td != td or contained != count-1 or mdisp != 0 or pdisp != -1):
            raise RttiResolutionError("COL and complete-object hierarchy disagree")
        if module.base + base_td != target:
            continue
        if pdisp != -1 or flags & 0x1F or contained >= count:
            raise RttiResolutionError("target base is virtual, inaccessible or ambiguous")
        matches.append(mdisp)
    if len(matches) != 1:
        raise RttiResolutionError(f"expected one public target base, found {len(matches)}")
    complete = pointer - offset
    adjusted = complete + matches[0]
    if complete <= 0 or adjusted <= 0 or adjusted >= 1 << 64:
        raise RttiResolutionError("invalid adjusted address")
    return BaseResolution(adjusted, complete, td, target_descriptor_rva)
