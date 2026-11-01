# Python | ExternalCore/screenpoint.py | Python 3.12+ | audited ICamera screen-point arithmetic.
"""Model helper RVA 0x275db0, reached by GetScreenPointFromWorldPoint.

Evidence: StaticAnalysis/integration-evidence/camera-binding/. No camera is
discovered or selected here. Input must be a float3 in the same coordinate frame
as camera+0x7c; do not blindly feed anchor-corrected GetEntityPosition output.
Float32 operations are rounded at each step. math.tan is rounded to float32;
bit identity with the game's native tan implementation/FP modes is unproven.
"""
from dataclasses import dataclass
import math
import struct

CAMERA_BYTES = 0x458
DEG_TO_RAD = struct.unpack("<f", bytes.fromhex("35fa8e3c"))[0]
DEPTH_EPSILON = struct.unpack("<f", bytes.fromhex("bd378635"))[0]
TENTH = struct.unpack("<f", bytes.fromhex("cdcccc3d"))[0]


def _f32(value):
    try:
        result = struct.unpack("<f", struct.pack("<f", value))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError("value is not representable as a finite float32") from exc
    if not math.isfinite(result):
        raise ValueError("nonfinite screen-point input/intermediate")
    return result


def _quantize_tenth(value):
    scaled = _f32(value * 10.0)
    # Native roundf helper 426b1c0: ties away from zero, not Python bankers' rounding.
    magnitude = math.floor(abs(scaled))
    if abs(scaled) - magnitude >= 0.5:
        magnitude += 1
    rounded = math.copysign(float(magnitude), scaled)
    return _f32(_f32(rounded) * TENTH)


@dataclass(frozen=True, slots=True)
class CameraSnapshot:
    origin: tuple[float, float, float]
    basis: tuple[float, ...]
    width: int
    height: int
    field_of_view: float


@dataclass(frozen=True, slots=True)
class ScreenPoint:
    x: float
    y: float
    depth: float
    camera_z: float
    in_front: bool
    inside_viewport: bool


def decode_camera(snapshot: object) -> CameraSnapshot:
    try:
        view = memoryview(snapshot)
    except TypeError as exc:
        raise TypeError("camera snapshot must be bytes-like") from exc
    if not view.c_contiguous:
        raise ValueError("camera snapshot must be contiguous")
    raw = bytes(view.cast("B")[:CAMERA_BYTES])
    if len(raw) < CAMERA_BYTES:
        raise ValueError(f"camera snapshot requires {CAMERA_BYTES:#x} bytes")
    return CameraSnapshot(struct.unpack_from("<3f", raw, 0x7C),
                          struct.unpack_from("<9f", raw, 0x41C),
                          *struct.unpack_from("<2H", raw, 0x408),
                          struct.unpack_from("<f", raw, 0x454)[0])


def project_screenpoint(camera: CameraSnapshot, point) -> ScreenPoint:
    """Return the audited screen-point convention for finite perspective inputs.

    Positive native output depth corresponds to camera-space Z<0. Other points
    receive depth -1, but still have X/Y; consumers must check in_front. The
    native helper does not apply Near/Far or an orthographic branch. Viewport
    inclusion is an added consumer check, not a native clipping claim.
    """
    if len(point) != 3 or len(camera.origin) != 3 or len(camera.basis) != 9:
        raise ValueError("point/origin/basis must have 3/3/9 elements")
    if (type(camera.width) is not int or type(camera.height) is not int or
            not 1 <= camera.width <= 65535 or not 1 <= camera.height <= 65535):
        raise ValueError("viewport dimensions must be positive uint16 values")
    fov = _f32(camera.field_of_view)
    if not 0 < fov < 180:
        raise ValueError("perspective FieldOfView must be between 0 and 180 degrees")
    dx, dy, dz = (_f32(_f32(p) - _f32(o)) for p, o in zip(point, camera.origin))
    b = tuple(_f32(v) for v in camera.basis)
    # Preserve the actual MULSS/ADDSS ordering, including X's dy term first.
    x = _f32(_f32(_f32(dy * b[3]) + _f32(dx * b[0])) + _f32(dz * b[6]))
    y = _f32(_f32(_f32(dx * b[1]) + _f32(dy * b[4])) + _f32(dz * b[7]))
    z = _f32(_f32(_f32(dx * b[2]) + _f32(dy * b[5])) + _f32(dz * b[8]))
    inverse_depth = _f32(1.0 / max(abs(z), DEPTH_EPSILON))
    nx, ny = _f32(x * inverse_depth), _f32(y * inverse_depth)
    half_angle = _f32(_f32(fov * DEG_TO_RAD) * 0.5)
    tangent = _f32(math.tan(half_angle))
    if tangent == 0:
        raise ValueError("FieldOfView underflowed to a zero tangent")
    scale = _f32(1.0 / tangent)
    sx = _f32(_f32(_f32(_f32(camera.height * nx) * scale) + camera.width) * 0.5)
    sy = _f32(_f32(camera.height - _f32(_f32(camera.height * ny) * scale)) * 0.5)
    sx, sy = _quantize_tenth(sx), _quantize_tenth(sy)
    depth = _quantize_tenth(-z if z < 0 else -1.0)
    return ScreenPoint(sx, sy, depth, z, z < 0,
                       z < 0 and 0 <= sx < camera.width and 0 <= sy < camera.height)
