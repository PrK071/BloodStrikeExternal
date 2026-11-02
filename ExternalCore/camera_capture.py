# Python | ExternalCore/camera_capture.py | Python 3.12+ | typed acquisition of the candidate gameplay camera.
"""Source chain from GetGameplay/ClientPlayer.Camera; no engine calls.

RTTI checks reject unsupported concrete types instead of assuming that a generic
IComponent is ClientPlayer. This selects the Player.Camera property candidate;
equivalence with the final rendered viewport has not been observed in the game.
"""
from dataclasses import dataclass
import math
import struct
import time

from .build import ModuleIdentity
from .entity_position import EntityPositionSnapshot, decode_entity_position
from .memory import MemoryReadError, MemoryReader, read_exact
from .registry import RegistryFrame, RegistryReadError, collect_registry, _pointer
from .rtti import resolve_nonvirtual_base
from .screenpoint import CAMERA_BYTES, CameraSnapshot, decode_camera
from .render_camera import RenderCamera,render_camera_pass

ENGINE_ROOT_RVA = 0x80D5980  # Callback3271090: root, then root+58, call2d829a0.
GAMEPLAY_OFFSET = 0x58
PLAYER_OFFSET = 0x58        # IGameplay.Player: 58b020/92bec0/948bd0.
PLAYER_CAMERA_OFFSET = 0xD88  # ClientPlayer.Camera: d09ed0/d09ef0.
GAMEPLAY_TD = 0x7E35098     # COL6e7a3a0; baseline RTTI.
CLIENT_PLAYER_TD = 0x7E57120  # COL6ea2828.
ICAMERA_TD = 0x7DE5D50      # COL6e1e1b8; IEntity base displacement0.


@dataclass(frozen=True, slots=True)
class CameraCapture:
    engine_root: int
    gameplay: int
    player: int
    camera_address: int
    camera: CameraSnapshot
    position: EntityPositionSnapshot
    selection: str = "rtti_checked_Player.Camera_candidate_not_final_viewport_observation"


@dataclass(frozen=True, slots=True)
class WorldCapture:
    registry: RegistryFrame
    camera: CameraCapture
    started_ns: int
    finished_ns: int
    attempts: int
    consistency: str = "equal_camera_reads_around_two_registry_passes_no_atomicity_or_ABA_guarantee"
    render_camera: RenderCamera | None = None
    render_camera_error: str | None = None


def _camera_pass(reader: MemoryReader, module: ModuleIdentity):
    observations = []
    class Observed:
        def read(self, address, size):
            value = read_exact(reader, address, size)
            observations.append((address, value))
            return value
    observed = Observed()
    def pointer(address, name):
        value, = struct.unpack("<Q", observed.read(address, 8))
        return _pointer(value, name)
    root = pointer(module.address(ENGINE_ROOT_RVA, 8), "engine root")
    gameplay_pointer = pointer(root + GAMEPLAY_OFFSET, "gameplay")
    gameplay = resolve_nonvirtual_base(observed, module, gameplay_pointer, GAMEPLAY_TD).address
    player_pointer = pointer(gameplay + PLAYER_OFFSET, "Player")
    player = resolve_nonvirtual_base(observed, module, player_pointer, CLIENT_PLAYER_TD).address
    camera_pointer = pointer(player + PLAYER_CAMERA_OFFSET, "Camera")
    camera_address = resolve_nonvirtual_base(observed, module, camera_pointer, ICAMERA_TD).address
    entity = resolve_nonvirtual_base(observed, module, camera_address).address
    if entity != camera_address:
        raise ValueError("unsupported ICamera/IEntity subobject adjustment")
    raw = observed.read(camera_address, CAMERA_BYTES)
    if raw[0x418]:
        raise ValueError("orthographic camera is unsupported by the perspective pipeline")
    camera = decode_camera(raw)
    position = decode_entity_position(raw)
    if (not camera.width or not camera.height or not 0 < camera.field_of_view < 180 or
            not all(math.isfinite(x) for x in (*camera.origin, *camera.basis))):
        raise ValueError("invalid camera geometry")
    b = camera.basis
    lengths = [math.hypot(b[i], b[i+3], b[i+6]) for i in range(3)]
    determinant = b[0]*(b[4]*b[8]-b[5]*b[7]) - b[1]*(b[3]*b[8]-b[5]*b[6]) + b[2]*(b[3]*b[7]-b[4]*b[6])
    # Consumer validation: nearly dependent axes can collapse all points to center.
    if not all(lengths) or abs(determinant) / math.prod(lengths) < 1e-6:
        raise ValueError("degenerate camera basis")
    return CameraCapture(root, gameplay, player, camera_address, camera, position), tuple(observations)


def capture_world(reader: MemoryReader, module: ModuleIdentity, *, max_nodes=10000, attempts=3,
                  require_render_input=False, allow_motion=False) -> WorldCapture:
    """Bracket the registry capture with matching typed camera observations."""
    if type(attempts) is not int or not 1 <= attempts <= 10:
        raise ValueError("attempts must be between 1 and 10")
    if type(require_render_input) is not bool:raise TypeError('require_render_input must be bool')
    if type(allow_motion) is not bool:raise TypeError('allow_motion must be bool')
    def camera_trace(trace,source):
        if not allow_motion:return trace
        result=[]
        for address,raw in trace:
            if address==source and len(raw)==CAMERA_BYTES:
                compared=bytearray(raw)
                compared[0x58:0x88]=bytes(0x30)
                compared[0x41C:0x44C]=bytes(0x30)
                raw=bytes(compared)
            result.append((address,raw))
        return tuple(result)
    def render_pass(source):
        try:
            value,trace=render_camera_pass(reader,module,source_camera=source)
            if allow_motion:
                # Each pass already checked that source and render view copies
                # agree. Their pose may advance between independent passes.
                trace=tuple((address,bytes(len(raw)) if address in
                    (source+0x41C,value.client+0xEE0) and len(raw)==48 else raw)
                    for address,raw in trace)
            return value,trace,None
        except (MemoryReadError,ValueError) as exc:
            return None,(),f'{type(exc).__name__}: {exc}'
    start = time.perf_counter_ns()
    last = None
    for attempt in range(1, attempts + 1):
        try:
            first, before = _camera_pass(reader, module)
            render_first,render_before,error_before=render_pass(first.camera_address)
            registry = collect_registry(reader, module, max_nodes=max_nodes, attempts=1,
                                        allow_motion=allow_motion)
            second, after = _camera_pass(reader, module)
            render_second,render_after,error_after=render_pass(second.camera_address)
            if camera_trace(before,first.camera_address) != camera_trace(after,second.camera_address):
                raise RegistryReadError("camera changed during registry acquisition")
            if render_before!=render_after or error_before!=error_after:
                raise RegistryReadError('render camera changed during registry acquisition')
            if require_render_input and render_second is None:
                raise RegistryReadError(f'required render input is unresolved: {error_after}')
            return WorldCapture(registry, second, start, time.perf_counter_ns(), attempt,
                consistency=('matching_camera_registry_links_and_anchors_sequential_pose_samples'
                             if allow_motion else 'equal_camera_reads_around_two_registry_passes_no_atomicity_or_ABA_guarantee'),
                render_camera=render_second,render_camera_error=error_after)
        except (MemoryReadError, ValueError) as exc:
            last = exc
    raise RegistryReadError(f"no stable typed camera/registry in {attempts} attempt(s): {last}") from last
