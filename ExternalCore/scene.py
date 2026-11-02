# Python | ExternalCore/scene.py | Python 3.12+ | projected ESP markers and explicit per-frame classification.
"""No guessed bones, health fields or gameplay categories.

The default coordinate gate accepts only equal observed anchor origins. This is
a conditional local-frame model, not proof of global scene/rebase semantics.
Classification defaults to unknown; an ActorComponent never implies opponent.
"""
from dataclasses import dataclass
from enum import Enum
import math

from .camera_capture import WorldCapture
from .screenpoint import ScreenPoint, project_screenpoint


class Category(str, Enum):
    UNKNOWN = "unknown"
    PLAYER = "player"
    OPPONENT = "opponent"
    ALLY = "ally"
    NEUTRAL = "neutral"
    WEAPON = "weapon"


@dataclass(frozen=True, slots=True)
class ObservationId:
    node: int
    key: int
    component: int
    actor: int
    parent: int


@dataclass(frozen=True, slots=True)
class StateFact:
    name: str
    kind: str
    value: int | float
    descriptor: int
    index: int
    storage: int


@dataclass(frozen=True, slots=True)
class PlayerFacts:
    area: int
    host: int
    values: tuple[StateFact,...] = ()
    interpreter_id: int | None = None
    local_source: str = "unresolved"
    diagnostics: tuple[str,...] = ()
    relation: bool | None = None
    relation_rule: str | None = None
    predicate_function: int | None = None
    life_state_name: str | None = None
    life_state_source: str | None = None


@dataclass(frozen=True, slots=True)
class Classification:
    category: Category = Category.UNKNOWN
    alive: bool | None = None
    visible: bool | None = None
    local: bool | None = None
    evidence: str = ""
    facts: PlayerFacts | None = None

    def __post_init__(self):
        if not isinstance(self.category, Category):
            raise TypeError("category must be a Category enum")
        if any(type(x) not in (bool, type(None)) for x in (self.alive, self.visible, self.local)):
            raise TypeError("local/alive/visible must have explicit boolean/unknown values")
        if not isinstance(self.evidence, str) or len(self.evidence) > 512:
            raise ValueError("invalid classification evidence reference")
        if self.facts is not None and not isinstance(self.facts,PlayerFacts):
            raise TypeError("facts must be PlayerFacts or None")


@dataclass(frozen=True, slots=True)
class ProjectedActor:
    observation: ObservationId
    point: ScreenPoint
    classification: Classification


@dataclass(frozen=True, slots=True)
class RejectedActor:
    observation: ObservationId
    reason: str


@dataclass(frozen=True, slots=True)
class Scene:
    width: int
    height: int
    captured_ns: int
    actors: tuple[ProjectedActor, ...]
    rejected: tuple[RejectedActor, ...]
    coordinate_contract: str = "conditional_same_observed_anchor_origin"
    final_viewport_validated: bool = False


def observation_id(record):
    return ObservationId(record.node, record.key, record.component, record.actor, record.parent)


def build_scene(capture: WorldCapture, classifications=None, *, target_local_y=0.0) -> Scene:
    """Project eligible positions. Classification mapping must belong to this capture.

    ObservationId identifies bytes in this observation, not a lifetime generation.
    There is no category cache or sticky target surviving another frame.
    """
    if not 1 <= capture.camera.camera.width <= 8192 or not 1 <= capture.camera.camera.height <= 8192:
        raise ValueError("viewport exceeds the supported overlay dimensions [1,8192]")
    if not math.isfinite(target_local_y) or not 0<=target_local_y<=3:
        raise ValueError('target_local_y must be finite and between 0 and 3 model units')
    classifications = {} if classifications is None else classifications
    actors, rejected = [], []
    current_ids = {observation_id(record) for record in capture.registry.records}
    if set(classifications) - current_ids:
        raise ValueError("classification refers to an object absent from this observation")
    for record in capture.registry.records:
        identity = observation_id(record)
        if not record.in_world or record.position is None:
            rejected.append(RejectedActor(identity, record.position_status))
            continue
        if record.position.anchor_used != capture.camera.position.anchor_used:
            rejected.append(RejectedActor(identity, "different_anchor_origin_unresolved"))
            continue
        classification = classifications.get(identity, Classification())
        if not isinstance(classification, Classification):
            raise TypeError("classification values must be Classification objects")
        try:
            position=record.position.local_translation
            if classification.category is Category.OPPONENT and target_local_y:
                position=tuple(origin+target_local_y*axis for origin,axis in
                               zip(position,record.position.transform[3:6]))
            point = project_screenpoint(capture.camera.camera, position)
        except ValueError as exc:
            rejected.append(RejectedActor(identity, f"projection_invalid: {exc}"))
            continue
        actors.append(ProjectedActor(identity, point, classification))
    # Oldest possible byte in this acquisition window, not completion time.
    return Scene(capture.camera.camera.width, capture.camera.camera.height, capture.started_ns,
                 tuple(actors), tuple(rejected))


def draw_commands(scene: Scene, *, radius=4, aim_radius=180.0):
    """Render projected origins and labels; no invented head/height/bone boxes."""
    if any(type(v) is not int or not 1 <= v <= 8192 for v in (scene.width, scene.height)):
        raise ValueError("viewport exceeds native overlay dimensions")
    if type(radius) is not int or not 1 <= radius <= 64:
        raise ValueError("marker radius must be in [1,64]")
    if not math.isfinite(aim_radius) or not 0 <= aim_radius <= 4096:
        raise ValueError("invalid aim radius")
    cx, cy = scene.width // 2, scene.height // 2
    commands = [dict(kind="circle", x=cx, y=cy, radius=round(aim_radius), color=[90, 90, 90], width=1)]
    colors = {Category.UNKNOWN: [170, 170, 170], Category.PLAYER: [240, 160, 60], Category.OPPONENT: [255, 70, 70],
              Category.ALLY: [70, 160, 255], Category.NEUTRAL: [220, 200, 80], Category.WEAPON: [170, 110, 210]}
    for actor in scene.actors:
        if not actor.point.inside_viewport:
            continue
        x, y = round(actor.point.x), round(actor.point.y)
        color = colors[actor.classification.category]
        if actor.classification.local is True:color=[80,255,160]
        details=""
        if actor.classification.facts:
            hp=next((fact.value for fact in actor.classification.facts.values
                     if fact.name=="server_hp" and fact.kind=="float"),None)
            if hp is not None:details+=f" hp={hp:g}"
        if actor.classification.local is True:details+=" local"
        commands.append(dict(kind="circle", x=x, y=y, radius=radius, color=color, width=1))
        commands.append(dict(kind="text", x=x+7, y=y+3, color=color,
                             text=f"{actor.classification.category.value} #{actor.observation.key:08x}{details}"))
    return tuple(commands)
