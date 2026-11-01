# Python | ExternalCore/registry.py | Python 3.12+ | pinned GetAllActors registry collector.
"""Walk the proven registry layout, without calling engine or Python functions.

Two identical passes are an observation window, NOT an atomic snapshot, lock,
ABA detector or proof of object lifetime. The actor serial is not a player ID.
"""
from dataclasses import dataclass
import struct
import time

from .build import ModuleIdentity
from .entity_position import SNAPSHOT_SIZE, EntityPositionSnapshot, decode_entity_position
from .memory import MemoryReader, MemoryReadError, read_exact
from .rtti import BaseResolution, RttiResolutionError, resolve_nonvirtual_base

ROOT_RVA = 0x8B7CD90  # Getter 19d45e0; V2/V3/V4 identity.
ROOT_SENTINEL = 0x8
NODE_SIZE = 0x20
NODE_KEY = 0x10  # Insert stores 254497; payload at 25449e.
NODE_COMPONENT = 0x18
COMPONENT_PARENT = 0x40
COMPONENT_ACTOR = 0x378
ACTOR_SERIAL = 0x0C
PARENT_STATE = 0x130
IN_WORLD = 0x10  # IEntity.IsInWorld; not a gameplay category.


class RegistryReadError(ValueError):
    pass


class InconsistentReadError(RegistryReadError):
    pass


@dataclass(frozen=True, slots=True)
class ActorRecord:
    node: int
    key: int
    component: int
    actor: int
    parent: int
    in_world: bool
    entity: int | None
    position: EntityPositionSnapshot | None
    position_status: str
    dynamic_descriptor_rva: int | None


@dataclass(frozen=True, slots=True)
class RegistryFrame:
    root: int
    sentinel: int
    records: tuple[ActorRecord, ...]
    started_ns: int
    finished_ns: int
    attempts: int
    consistency: str = "two_equal_passes_no_atomicity_or_lifetime_guarantee"
    gameplay_classification: str = "unclassified"


@dataclass(frozen=True, slots=True)
class _Pass:
    root: int
    sentinel: int
    records: tuple[ActorRecord, ...]
    observations: tuple[tuple[int, bytes], ...]


def _pointer(value: int, label: str) -> int:
    # Windows AMD64 user-mode pointers, eight-byte aligned in these layouts.
    if not 0x10000 <= value <= 0x7FFFFFFFFFF8 or value % 8:
        raise RegistryReadError(f"invalid {label} pointer: {value:#x}")
    return value


def _read_pass(reader: MemoryReader, module: ModuleIdentity, max_nodes: int) -> _Pass:
    observations = []

    class Observed:
        def read(self, address, size):
            data = read_exact(reader, address, size)
            observations.append((address, data))
            return data

    observed = Observed()

    def get(address, size):
        return observed.read(address, size)

    def u64(address):
        return struct.unpack("<Q", get(address, 8))[0]

    root = u64(module.address(ROOT_RVA, 8))
    if root == 0:
        return _Pass(0, 0, (), tuple(observations))
    _pointer(root, "registry")
    sentinel = _pointer(u64(root + ROOT_SENTINEL), "sentinel")
    node = u64(sentinel)
    seen = set()
    keys = set()
    records = []
    while node != sentinel:
        _pointer(node, "node")
        if node in seen:
            raise RegistryReadError("registry cycle does not terminate at its sentinel")
        if len(seen) >= max_nodes:
            raise RegistryReadError("registry exceeds the configured node budget")
        seen.add(node)
        raw_node = get(node, NODE_SIZE)
        following, = struct.unpack_from("<Q", raw_node)
        key, = struct.unpack_from("<I", raw_node, NODE_KEY)
        component, = struct.unpack_from("<Q", raw_node, NODE_COMPONENT)
        if key in keys:
            raise RegistryReadError("duplicate key observed in one registry traversal")
        keys.add(key)
        _pointer(component, "component")
        parent = u64(component + COMPONENT_PARENT)
        actor = _pointer(u64(component + COMPONENT_ACTOR), "actor")
        serial, = struct.unpack("<I", get(actor + ACTOR_SERIAL, 4))
        if serial != key:
            raise InconsistentReadError("node key differs from its associated actor serial")
        in_world = False
        entity = None
        position = None
        descriptor = None
        status = "no_parent"
        if parent:
            _pointer(parent, "Parent")
            in_world = bool(get(parent + PARENT_STATE, 1)[0] & IN_WORLD)
            status = "out_of_world"
            if in_world:
                try:
                    resolved: BaseResolution = resolve_nonvirtual_base(observed, module, parent)
                except (RttiResolutionError, ValueError) as exc:
                    status = f"unsupported_entity_rtti: {exc}"
                else:
                    entity = _pointer(resolved.address, "IEntity")
                    descriptor = resolved.dynamic_descriptor_rva
                    position = decode_entity_position(get(entity, SNAPSHOT_SIZE))
                    status = "decoded_unclassified"
        records.append(ActorRecord(node, key, component, actor, parent, in_world,
                                   entity, position, status, descriptor))
        node = following
    return _Pass(root, sentinel, tuple(records), tuple(observations))


def collect_registry(reader: MemoryReader, module: ModuleIdentity, *, max_nodes: int = 10000,
                     attempts: int = 3) -> RegistryFrame:
    """Return matching consecutive observations or fail without a partial frame.

    Every used RTTI/position byte is read again. This can reject changes but
    cannot exclude A->B->A, address recycling or concurrent changes after return.
    Unsupported Parent RTTI remains an explicit record without a position.
    """
    if type(max_nodes) is not int or not 1 <= max_nodes <= 100000:
        raise ValueError("max_nodes must be between 1 and 100000")
    if type(attempts) is not int or not 1 <= attempts <= 10:
        raise ValueError("attempts must be between 1 and 10")
    started = time.perf_counter_ns()
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            first = _read_pass(reader, module, max_nodes)
            second = _read_pass(reader, module, max_nodes)
            if first.observations != second.observations:
                raise InconsistentReadError("registry or object bytes changed between passes")
            return RegistryFrame(second.root, second.sentinel, second.records,
                                 started, time.perf_counter_ns(), attempt)
        except (MemoryReadError, RegistryReadError) as exc:
            last_error = exc
    raise RegistryReadError(f"no consistent complete traversal in {attempts} attempt(s): {last_error}") from last_error
