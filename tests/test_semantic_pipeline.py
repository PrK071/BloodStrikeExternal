# Python | tests/test_semantic_pipeline.py | Python 3.12+ unittest | verified relation/state/render inputs to aim planning.
import unittest

from ExternalCore.aim import AimProfile
from ExternalCore.pipeline import process_frame
from ExternalCore.scene import Category
from test_life_state import LifeFixture
from test_render_camera import RenderFixture


class SemanticFixture(LifeFixture,RenderFixture):
    def complete(self):
        self.setup_life().choose_other_local().render()
        self.set_state(0)
        return self


class SemanticPipelineTests(unittest.TestCase):
    def test_default_classifier_links_render_input_opponent_alive_and_explicit_aim_profile(self):
        f=SemanticFixture().complete()
        # Visibility is an explicit policy input. No line-of-sight fact is invented.
        profile=AimProfile(require_visible=False,counts_per_pixel=(1.,1.))
        frame=process_frame(f.memory(),f.module,profile=profile,active=True,require_render_input=True)
        state=frame.scene.actors[0].classification
        self.assertEqual(state.category,Category.OPPONENT)
        self.assertIs(state.local,False);self.assertIs(state.alive,True)
        self.assertIsNone(state.visible)
        self.assertTrue(frame.capture.render_camera.source_copy_matched)
        self.assertEqual(frame.aim.reason,'planned')
        self.assertIsNotNone(frame.aim.target)
        self.assertLessEqual(frame.aim.dx**2+frame.aim.dy**2,25**2)
        self.assertFalse(frame.scene.final_viewport_validated)

    def test_dying_or_changed_mode_body_stops_selection_without_sticky_target(self):
        for fault in ['dying','mode']:
            f=SemanticFixture().complete()
            if fault=='dying':f.set_state(1)
            else:f.set(f.code+0x34,'<i',2)
            frame=process_frame(f.memory(),f.module,active=True,require_render_input=True,
                profile=AimProfile(require_visible=False,counts_per_pixel=(1.,1.)))
            with self.subTest(fault=fault):
                self.assertIsNone(frame.aim.target)
                self.assertEqual((frame.aim.dx,frame.aim.dy),(0,0))


if __name__=='__main__':unittest.main()
