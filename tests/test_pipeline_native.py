# Python | tests/test_pipeline_native.py | Python 3.12+ unittest / Windows | owned child -> projection -> GDI.
import os
import unittest

from ExternalCore.aim import AimProfile
from ExternalCore.pipeline import process_frame
from ExternalCore.scene import Category, Classification, observation_id
from ExternalCore.win32_overlay import GdiSurface
from owned_process import OwnedProcess


@unittest.skipUnless(os.name == "nt", "requires owned Windows child and GDI")
class NativePipelineTests(unittest.TestCase):
    def test_actual_native_reads_to_esp_pixels_and_aim_plan(self):
        def classifier(capture):
            return {observation_id(record): Classification(Category.OPPONENT, True, True, False,
                    "owned_synthetic_fixture_not_a_game_classifier") for record in capture.registry.records}
        with OwnedProcess() as child:
            frame = process_frame(child.reader, child.module, classifier=classifier, active=True,
                                   profile=AimProfile(tau_ms=0, counts_per_pixel=(1,1), max_age_ms=1000))
            self.assertEqual(frame.capture.camera.camera_address, child.metadata["addresses"]["camera"])
            self.assertEqual((frame.aim.dx,frame.aim.dy), (11,22))
            with GdiSurface(frame.scene.width, frame.scene.height) as surface:
                surface.draw(frame.commands)
                x,y = round(frame.scene.actors[0].point.x), round(frame.scene.actors[0].point.y)
                self.assertTrue(any(surface.pixel(px,py) == (255,70,70)
                    for px in range(x-5,x+6) for py in range(y-5,y+6)))
            # No input adapter is called: a planned movement is not an OS event.


if __name__ == "__main__": unittest.main()
