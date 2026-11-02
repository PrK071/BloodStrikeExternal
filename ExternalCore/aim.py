# Python | ExternalCore/aim.py | Python 3.12+ | stateless screen-error targeting and relative motion planning.
"""Classification and count/pixel calibration are inputs, never discovered guesses.

The caller may request retention of a previous target; it is rechecked against
this frame's eligibility. These functions retain no state and perform no I/O.
"""
from dataclasses import dataclass
import math

from .scene import Category, ObservationId, ProjectedActor, Scene


@dataclass(frozen=True, slots=True)
class AimProfile:
    radius_px: float = 180.0
    tau_ms: float = 70.0
    max_step_counts: float = 25.0
    deadzone_px: float = 0.5
    max_age_ms: float = 100.0
    require_visible: bool = True
    counts_per_pixel: tuple[float, float] | None = None

    def __post_init__(self):
        for name, low, high in (("radius_px", 0, 4096), ("tau_ms", 0, 10000),
                                ("max_step_counts", 0, 32767), ("deadzone_px", 0, 4096),
                                ("max_age_ms", 0, 1000)):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"invalid {name}")
        if type(self.require_visible) is not bool:
            raise TypeError("require_visible must be bool")
        if self.counts_per_pixel is not None:
            if len(self.counts_per_pixel) != 2 or any(isinstance(v, bool) or not isinstance(v, (int,float)) or
                    not math.isfinite(v) or v <= 0 or v > 10000 for v in self.counts_per_pixel):
                raise ValueError("calibration must contain two finite positive count/pixel gains")


@dataclass(frozen=True, slots=True)
class AimDecision:
    target: ObservationId | None
    dx: int
    dy: int
    captured_ns: int
    reason: str

    def __post_init__(self):
        if type(self.captured_ns) is not int or self.captured_ns < 0:
            raise ValueError("capture timestamp must be a nonnegative integer")
        if any(type(v) is not int or not -32767 <= v <= 32767 for v in (self.dx, self.dy)):
            raise ValueError("movement must contain bounded integer counts")
        if self.target is not None and not isinstance(self.target, ObservationId):
            raise TypeError("target must be an observation ID or None")
        if self.reason == "planned" and self.target is None:
            raise ValueError("planned movement requires a selected observation")


def select_target(scene: Scene, profile: AimProfile, *, locked_target=None) -> ProjectedActor | None:
    cx, cy = scene.width / 2.0, scene.height / 2.0
    eligible = []
    for actor in scene.actors:
        state = actor.classification
        if (state.category is not Category.OPPONENT or state.alive is not True or state.local is not False or
                not state.evidence or (profile.require_visible and state.visible is not True) or
                not actor.point.inside_viewport):
            continue
        distance = (actor.point.x - cx)**2 + (actor.point.y - cy)**2
        if distance <= profile.radius_px**2:
            token = actor.observation
            # Deterministic ties without treating this tuple as a lifetime ID.
            eligible.append((distance, token.key, token.component, token.actor, token.node, actor))
    if locked_target is not None:
        retained=next((item[-1] for item in eligible if item[-1].observation==locked_target),None)
        if retained is not None:return retained
    return min(eligible, key=lambda item: item[:-1])[-1] if eligible else None


def plan_aim(scene: Scene, profile: AimProfile, *, now_ns: int, dt_ms: float, active: bool,
             locked_target=None) -> AimDecision:
    def idle(reason, target=None):
        return AimDecision(target, 0, 0, scene.captured_ns, reason)
    if type(active) is not bool or type(now_ns) is not int or now_ns < 0:
        raise TypeError("active/now_ns must be bool/int")
    if type(scene.captured_ns) is not int or scene.captured_ns < 0:
        raise ValueError("scene capture timestamp must be a nonnegative integer")
    if isinstance(dt_ms, bool) or not math.isfinite(dt_ms) or not 0 <= dt_ms <= 1000:
        raise ValueError("dt_ms must be finite and in [0,1000]")
    if not active:
        return idle("inactive")
    age_ns = now_ns - scene.captured_ns
    if age_ns < 0 or age_ns > profile.max_age_ms * 1_000_000:
        return idle("stale_or_future_capture")
    target = select_target(scene, profile,locked_target=locked_target)
    if target is None:
        return idle("no_classified_target")
    if profile.counts_per_pixel is None:
        return idle("input_calibration_missing", target.observation)
    ex, ey = target.point.x - scene.width/2, target.point.y - scene.height/2
    if math.hypot(ex, ey) <= profile.deadzone_px:
        return idle("inside_deadzone", target.observation)
    alpha = 1.0 if profile.tau_ms == 0 else -math.expm1(-dt_ms / profile.tau_ms)
    dx = ex * profile.counts_per_pixel[0] * alpha
    dy = ey * profile.counts_per_pixel[1] * alpha
    length = math.hypot(dx, dy)
    if length > profile.max_step_counts:
        factor = profile.max_step_counts / length
        dx, dy = dx * factor, dy * factor
    return AimDecision(target.observation, math.trunc(dx), math.trunc(dy), scene.captured_ns, "planned")
