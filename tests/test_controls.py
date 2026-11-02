# Python / tests/test_controls.py / Python 3.12+ unittest / live toggles and projected ESP geometry
import unittest
from ExternalCore.controls import LiveControls,render_controls
from ExternalCore.pipeline import process_frame
from registry_fixture import fixture_memory
from test_pipeline import opponent


class ControlTests(unittest.TestCase):
    def test_toggles_are_independent_and_snapshot_cannot_mutate_state(self):
        controls=LiveControls();snapshot=controls.snapshot();snapshot['aim']=False
        self.assertTrue(controls.snapshot()['aim'])
        controls.set('aim',False)
        self.assertFalse(controls.snapshot()['aim'])
        self.assertTrue(controls.snapshot()['esp'])
        with self.assertRaises(ValueError):controls.set('aim',1)

    def test_boxes_and_tracers_follow_current_projected_actor_and_disable(self):
        memory,module,_=fixture_memory()
        frame=process_frame(memory,module,classifier=opponent,target_local_y=1.55)
        controls=LiveControls()
        commands=render_controls(frame,controls.snapshot())
        self.assertEqual(sum(command['kind']=='line' for command in commands),5)
        controls.set('tracers',False)
        self.assertEqual(sum(command['kind']=='line' for command in render_controls(frame,controls.snapshot())),4)
        controls.set('boxes',False)
        self.assertFalse(any(command['kind']=='line' for command in render_controls(frame,controls.snapshot())))
        controls.set('esp',False)
        self.assertEqual(render_controls(frame,controls.snapshot()),())
