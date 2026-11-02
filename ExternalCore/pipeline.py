# Python | ExternalCore/pipeline.py | Python 3.12+ | acquisition -> scene -> ESP -> aim planning.
"""Independent of GUI/input I/O; callable against a recording or Win32 reader."""
from dataclasses import dataclass, replace
import time

from .aim import AimDecision, AimProfile, plan_aim
from .camera_capture import WorldCapture, capture_world
from .scene import Scene, build_scene, draw_commands,observation_id


@dataclass(frozen=True, slots=True)
class PipelineFrame:
    capture: WorldCapture
    scene: Scene
    commands: tuple[dict, ...]
    aim: AimDecision
    render_status: str
    metadata_started_ns: int = 0


def process_frame(reader, module, *, profile=None, classifier=None, active=False,
                  dt_ms=16.0, now_ns=None, max_nodes=10000,require_render_input=False,
                  allow_motion=False,target_local_y=0.0,locked_target=None,
                  refresh_geometry=False) -> PipelineFrame:
    """Classifications are produced for this exact capture, never reused by address."""
    profile = AimProfile() if profile is None else profile
    capture = capture_world(reader, module, max_nodes=max_nodes,require_render_input=require_render_input,
                            allow_motion=allow_motion)
    if classifier is None:
        from .python_owner import classify_player_models
        classifications = classify_player_models(reader, module, capture)
    else:
        classifications = classifier(capture)
    metadata_started=capture.started_ns
    if refresh_geometry:
        original_ids={observation_id(record) for record in capture.registry.records}
        if set(classifications)-original_ids:raise ValueError('classification absent from metadata observation')
        capture=capture_world(reader,module,max_nodes=max_nodes,require_render_input=require_render_input,
                              allow_motion=allow_motion)
        current_ids={observation_id(record) for record in capture.registry.records}
        classifications={key:value for key,value in classifications.items() if key in current_ids}
    scene = build_scene(capture, classifications,target_local_y=target_local_y)
    now_ns = time.perf_counter_ns() if now_ns is None else now_ns
    aim_scene=replace(scene,captured_ns=min(metadata_started,scene.captured_ns)) if refresh_geometry else scene
    aim = plan_aim(aim_scene, profile, now_ns=now_ns, dt_ms=dt_ms, active=active,locked_target=locked_target)
    fresh = 0 <= now_ns-scene.captured_ns <= profile.max_age_ms*1_000_000
    drawable = scene if fresh else replace(scene, actors=())
    commands = draw_commands(drawable, aim_radius=profile.radius_px)
    if not fresh:
        commands += (dict(kind="text",x=12,y=12,text="STALE FRAME",color=[255,90,50]),)
    return PipelineFrame(capture, scene, commands, aim, "fresh" if fresh else "stale_or_future_capture",metadata_started)
