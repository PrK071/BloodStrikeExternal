# Python | tests/test_pipeline.py | Python 3.12+ unittest | typed camera, scene and aim contracts.
from dataclasses import replace
import math
import unittest

from ExternalCore.aim import AimProfile, plan_aim, select_target
from ExternalCore.camera_capture import capture_world
from ExternalCore.memory import SnapshotMemory
from ExternalCore.pipeline import process_frame
from ExternalCore.registry import RegistryReadError
from ExternalCore.scene import (Category, Classification, ObservationId, ProjectedActor,
                                 Scene, build_scene, draw_commands, observation_id)
from ExternalCore.screenpoint import ScreenPoint
from registry_fixture import fixture_memory, fixture_segments, patch


def opponent(capture):
    return {observation_id(record): Classification(Category.OPPONENT, True, True, False,
                "owned_synthetic_fixture_category_not_game_evidence") for record in capture.registry.records}


class CameraPipelineTests(unittest.TestCase):
    def test_model_space_target_probe_is_transformed_before_projection(self):
        reader,module,_=fixture_memory()
        frame=process_frame(reader,module,classifier=opponent,target_local_y=1.0)
        self.assertEqual(frame.scene.actors[0].point.x,1027.5)
        self.assertEqual(frame.scene.actors[0].point.y,621.0)
        upper=process_frame(reader,module,classifier=opponent,target_local_y=1.65)
        self.assertAlmostEqual(upper.scene.actors[0].point.y,585.9,places=3)
        with self.assertRaisesRegex(ValueError,'model units'):
            process_frame(reader,module,classifier=opponent,target_local_y=3.1)

    def test_typed_chain_to_projection_and_unknown_category(self):
        reader, module, a = fixture_memory()
        frame = process_frame(reader, module, active=True)
        self.assertEqual(frame.capture.camera.camera_address, a["camera"])
        self.assertEqual(frame.capture.camera.player, a["player"])
        self.assertEqual(frame.scene.actors[0].point.x, 1027.5)
        self.assertEqual(frame.scene.actors[0].point.y, 675)
        self.assertEqual(frame.scene.actors[0].point.depth, 10)
        self.assertEqual(frame.scene.actors[0].classification.category, Category.UNKNOWN)
        self.assertEqual(frame.aim.reason, "no_classified_target")
        self.assertFalse(frame.scene.final_viewport_validated)

    def test_rtti_rejects_a_generic_player_before_reading_clientplayer_fields(self):
        segments, module, a = fixture_segments()
        changed = patch(segments, a["player_rtti_td"], "<I", 0x7DE5D78)
        changed = patch(changed, a["player_rtti_base_td"], "<I", 0x7DE5D78)
        with self.assertRaisesRegex(RegistryReadError, "expected one public target base"):
            capture_world(SnapshotMemory(changed), module, attempts=1)

    def test_inconsistent_complete_object_rtti_is_rejected(self):
        segments, module, a = fixture_segments()
        changed = patch(segments, a["player_rtti_td"], "<I", 0x7DE5D78)
        with self.assertRaisesRegex(RegistryReadError, "hierarchy disagree"):
            capture_world(SnapshotMemory(changed), module, attempts=1)

    def test_perspective_pipeline_rejects_orthographic_or_invalid_viewport(self):
        segments, module, a = fixture_segments()
        for address, fmt, value in [(a["camera"] + 0x418, "<B", 1),
                                    (a["camera"] + 0x408, "<H", 0)]:
            with self.subTest(address=address), self.assertRaises(RegistryReadError):
                capture_world(SnapshotMemory(patch(segments, address, fmt, value)), module, attempts=1)

    def test_degenerate_basis_and_oversized_scene_are_rejected(self):
        segments, module, a = fixture_segments()
        changed = patch(segments, a["camera"] + 0x41C, "<9f", 0,0,0,0,0,0,0,0,1)
        with self.assertRaisesRegex(RegistryReadError, "degenerate"):
            capture_world(SnapshotMemory(changed), module, attempts=1)
        changed = patch(segments, a["camera"] + 0x408, "<H", 9000)
        with self.assertRaisesRegex(ValueError, "overlay dimensions"):
            process_frame(SnapshotMemory(changed), module)

    def test_capture_age_starts_at_acquisition_not_completion_or_classification(self):
        reader, module, _ = fixture_memory()
        capture = capture_world(reader, module)
        old = replace(capture, started_ns=1_000_000_000, finished_ns=2_000_000_000)
        scene = build_scene(old, opponent(old))
        self.assertEqual(scene.captured_ns, 1_000_000_000)
        decision = plan_aim(scene, AimProfile(counts_per_pixel=(1,1)), now_ns=2_000_000_000,
                            dt_ms=16, active=True)
        self.assertEqual(decision.reason, "stale_or_future_capture")

    def test_camera_change_during_capture_retries_the_complete_scene(self):
        segments, module, a = fixture_segments()
        class Changing:
            def __init__(self):
                self.reader, self.changed = SnapshotMemory(segments), False
            def read(self, address, size):
                result = self.reader.read(address, size)
                if address == a["camera"] and size == 0x458 and not self.changed:
                    self.reader = SnapshotMemory(patch(segments, a["camera"] + 0x84, "<f", 14.75))
                    self.changed = True
                return result
        result = capture_world(Changing(), module)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.camera.camera.origin, (0, 0, 14.75))

    def test_motion_mode_accepts_advancing_camera_pose_but_rejects_rebase(self):
        segments,module,a=fixture_segments()
        class Moving:
            def __init__(self,rebase=False):self.count,self.rebase=0,rebase
            def read(self,address,size):
                if address==a['camera'] and size==0x458:self.count+=1
                changed=patch(segments,a['camera']+0x84,'<f',13.75+self.count)
                if self.rebase:changed=patch(changed,a['camera']+0x1AC,'<i',100+self.count)
                return SnapshotMemory(changed).read(address,size)
        frame=capture_world(Moving(),module,allow_motion=True,attempts=1)
        self.assertEqual(frame.camera.camera.origin[2],15.75)
        self.assertIn('sequential_pose',frame.consistency)
        with self.assertRaises(RegistryReadError):
            capture_world(Moving(rebase=True),module,allow_motion=True,attempts=1)

    def test_different_observed_anchor_is_rejected_instead_of_guessed(self):
        segments, module, a = fixture_segments()
        changed = patch(segments, a["entity"] + 0x1AC, "<i", 101)
        frame = process_frame(SnapshotMemory(changed), module, active=True, classifier=opponent)
        self.assertEqual(frame.scene.actors, ())
        self.assertEqual(frame.scene.rejected[0].reason, "different_anchor_origin_unresolved")
        self.assertEqual((frame.aim.dx, frame.aim.dy), (0, 0))

    def test_classification_from_an_absent_observation_is_rejected(self):
        reader, module, _ = fixture_memory()
        capture = capture_world(reader, module)
        stale = replace(observation_id(capture.registry.records[0]), key=7)
        with self.assertRaisesRegex(ValueError, "absent"):
            build_scene(capture, {stale: Classification()})

    def test_full_synthetic_pipeline_produces_bounded_aim_and_esp_primitives(self):
        reader, module, _ = fixture_memory()
        result = process_frame(reader, module, classifier=opponent, active=True,
                               profile=AimProfile(tau_ms=0, counts_per_pixel=(1, 1)))
        self.assertEqual((result.aim.dx, result.aim.dy), (11, 22))
        self.assertEqual(result.aim.reason, "planned")
        self.assertLessEqual(math.hypot(result.aim.dx, result.aim.dy), 25)
        self.assertEqual(result.commands[1]["color"], [255, 70, 70])
        self.assertIn("opponent #12345678", result.commands[2]["text"])

    def test_stale_frames_hide_esp_markers_as_well_as_stopping_aim(self):
        reader,module,_ = fixture_memory()
        frame = process_frame(reader,module,classifier=opponent,active=True,now_ns=10**30,
                               profile=AimProfile(counts_per_pixel=(1,1)))
        self.assertEqual(frame.render_status,"stale_or_future_capture")
        self.assertEqual(frame.aim.reason,"stale_or_future_capture")
        self.assertEqual(len(frame.commands),2)
        self.assertEqual(frame.commands[1]["text"],"STALE FRAME")


def projected(key, x, y, *, category=Category.OPPONENT, alive=True, visible=True, local=False, evidence="fixture"):
    return ProjectedActor(ObservationId(key*32, key, key*1024, key*4096, key*8192),
                          ScreenPoint(x, y, 10, -10, True, 0 <= x < 1000 and 0 <= y < 1000),
                          Classification(category, alive, visible, local, evidence))


class AimTests(unittest.TestCase):
    def test_direct_calibrated_profile_is_not_limited_to_old_slow_step(self):
        scene=self.scene(projected(1,700,500))
        decision=plan_aim(scene,AimProfile(radius_px=500,tau_ms=0,max_step_counts=300,
            counts_per_pixel=(1.47,1.48)),now_ns=scene.captured_ns,dt_ms=16,active=True)
        self.assertEqual((decision.dx,decision.dy),(294,0))

    def test_lock_retains_eligible_target_and_drops_missing_or_dead_target(self):
        near=projected(1,505,500)
        previous=projected(2,540,500)
        profile=AimProfile(radius_px=100)
        self.assertEqual(select_target(self.scene(near,previous),profile,
                         locked_target=previous.observation).observation,previous.observation)
        dead=projected(2,540,500,alive=False)
        self.assertEqual(select_target(self.scene(near,dead),profile,
                         locked_target=previous.observation).observation,near.observation)

    def scene(self, *actors):
        return Scene(1000, 1000, 1_000_000_000, actors, ())

    def test_nearest_opponent_in_radius_and_stable_tie_break(self):
        profile = AimProfile(radius_px=50)
        self.assertEqual(select_target(self.scene(projected(3, 520, 500), projected(1, 510, 530)), profile).observation.key, 3)
        self.assertEqual(select_target(self.scene(projected(2, 510, 500), projected(1, 490, 500)), profile).observation.key, 1)
        self.assertIsNone(select_target(self.scene(projected(1, 551, 500)), profile))

    def test_no_player_inference_from_unknown_or_other_categories(self):
        profile = AimProfile()
        for kwargs in [dict(category=Category.UNKNOWN), dict(category=Category.PLAYER), dict(category=Category.WEAPON),
                       dict(category=Category.ALLY), dict(alive=False), dict(alive=None),
                       dict(visible=None), dict(visible=False), dict(local=True), dict(evidence="")]:
            with self.subTest(kwargs=kwargs):
                self.assertIsNone(select_target(self.scene(projected(1, 510, 500, **kwargs)), profile))
        self.assertIsNotNone(select_target(self.scene(projected(1, 510, 500, visible=False)),
                                          AimProfile(require_visible=False)))

    def test_smoothing_count_calibration_and_time_are_explicit(self):
        scene = self.scene(projected(1, 510, 496))
        result = plan_aim(scene, AimProfile(tau_ms=100, counts_per_pixel=(2, 1)),
                          now_ns=scene.captured_ns, dt_ms=100*math.log(2), active=True)
        self.assertEqual((result.dx, result.dy), (10, -2))
        missing = plan_aim(scene, AimProfile(), now_ns=scene.captured_ns, dt_ms=16, active=True)
        self.assertEqual(missing.reason, "input_calibration_missing")

    def test_inactive_stale_future_deadzone_and_disappearance_stop_movement(self):
        scene = self.scene(projected(1, 510, 500))
        profile = AimProfile(tau_ms=0, counts_per_pixel=(1,1))
        for now, active, reason in [(scene.captured_ns, False, "inactive"),
                                   (scene.captured_ns-1, True, "stale_or_future_capture"),
                                   (scene.captured_ns+100_000_001, True, "stale_or_future_capture")]:
            with self.subTest(reason=reason):
                decision = plan_aim(scene, profile, now_ns=now, dt_ms=16, active=active)
                self.assertEqual((decision.dx, decision.dy, decision.reason), (0,0,reason))
        centered = self.scene(projected(1,500.1,500))
        self.assertEqual(plan_aim(centered, profile, now_ns=scene.captured_ns, dt_ms=16, active=True).reason, "inside_deadzone")
        self.assertEqual(plan_aim(self.scene(), profile, now_ns=scene.captured_ns, dt_ms=16, active=True).reason, "no_classified_target")

    def test_configuration_rejects_nan_infinity_and_invalid_booleans(self):
        for kwargs in [dict(radius_px=float("nan")), dict(tau_ms=-1), dict(max_age_ms=float("inf")),
                       dict(counts_per_pixel=(0,1)), dict(require_visible=1)]:
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, TypeError)):
                AimProfile(**kwargs)
        with self.assertRaises(TypeError):
            Classification(alive=1)


if __name__ == "__main__":
    unittest.main()
