# Python | ExternalCore/entity_position.py | Python 3.12+ | BloodStrike x64, pinned sample, snapshot decoder.
"""Decode an IEntity byte snapshot using the audited BloodStrike build's arithmetic.

Disk evidence: StaticAnalysis/integration-evidence/entity-position/.
Sample SHA256: ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747.
This module performs no process access, pointer discovery, type validation, camera
selection, or unit conversion. The caller must supply a coherent IEntity snapshot
for that build, after any necessary native pointer adjustment.
"""
from dataclasses import dataclass
import struct

SAMPLE_SHA256 = "ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747"
GET_ENTITY_POSITION_RVA = 0x8977B0
TRANSFORM_OFFSET = 0x58  # Float loads: RVAs 897828, 897835, 897839, 897866..897894.
TRANSLATION_OFFSET = 0x7C  # Float loads: RVAs 897820, 89783D, 897848.
ANCHOR_OFFSET = 0x1AC  # Comparisons/loads: RVAs 8977BC..89781C.
ANCHOR_SENTINEL = 0x7FFFFFFF
SNAPSHOT_SIZE = ANCHOR_OFFSET + 3 * 4

Vector3 = tuple[float, float, float]
Anchor3 = tuple[int, int, int]


class SnapshotDecodeError(ValueError):
    """The supplied buffer cannot contain the required IEntity fields."""


@dataclass(frozen=True, slots=True)
class EntityPositionSnapshot:
    """Audited arithmetic result; coordinate frame and units are unspecified.

    ``transform`` contains the first nine float32 elements widened to double,
    followed by ``position``. ``anchor_raw`` preserves the signed int32 values.
    Sentinel handling is collective: a mixed triple uses *all* its raw values.
    Python floats represent the output double values, including NaN/infinities;
    this decoder does not invent validity checks absent from the native helper.
    """
    position: Vector3
    local_translation: Vector3
    anchor_raw: Anchor3
    anchor_used: Anchor3
    anchor_applied: bool
    transform: tuple[float, ...]


def decode_entity_position(snapshot: object, *, entity_offset: int = 0) -> EntityPositionSnapshot:
    """Decode a contiguous bytes-like snapshot, with optional entity start offset.

    Requires bytes through entity+0x1B7, inclusively (0x1B8 bytes per entity).
    Bounds are checked before unpacking. A small private copy freezes the fields
    during decoding; coherent acquisition of the input remains the caller's job.
    Raises TypeError for a non-buffer/non-contiguous input or invalid offset type,
    and SnapshotDecodeError for a negative offset or insufficient byte range.
    """
    if not isinstance(entity_offset, int) or isinstance(entity_offset, bool):
        raise TypeError("entity_offset must be an integer byte offset")
    if entity_offset < 0:
        raise SnapshotDecodeError("entity_offset must be non-negative")
    try:
        view = memoryview(snapshot)
    except TypeError as exc:
        raise TypeError("snapshot must support the buffer protocol") from exc
    if not view.c_contiguous:
        raise TypeError("snapshot must be C-contiguous")
    raw = view.cast("B")
    required = entity_offset + SNAPSHOT_SIZE
    if raw.nbytes < required:
        raise SnapshotDecodeError(
            f"IEntity snapshot requires {SNAPSHOT_SIZE:#x} bytes at offset "
            f"{entity_offset:#x} (buffer end {required:#x}); got {raw.nbytes:#x} bytes"
        )
    data = bytes(raw[entity_offset:required])
    transform32 = struct.unpack_from("<12f", data, TRANSFORM_OFFSET)
    anchor = struct.unpack_from("<3i", data, ANCHOR_OFFSET)
    local = transform32[9:12]
    applied = anchor != (ANCHOR_SENTINEL,) * 3
    used = anchor if applied else (0, 0, 0)
    # Native CVTPS2PD/CVTSI2SD precede ADDSD: never add in float32 first.
    position = tuple(float(origin) + coordinate for origin, coordinate in zip(used, local))
    return EntityPositionSnapshot(
        position=position,
        local_translation=local,
        anchor_raw=anchor,
        anchor_used=used,
        anchor_applied=applied,
        transform=transform32[:9] + position,
    )
