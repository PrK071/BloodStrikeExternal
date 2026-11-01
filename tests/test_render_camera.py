# Python | tests/test_render_camera.py | Python 3.12+ unittest | render input aliases, source copy and capture mutation.
import math
import unittest

from ExternalCore.camera_capture import capture_world
from ExternalCore.memory import Segment
from ExternalCore.registry import RegistryReadError
from ExternalCore.render_camera import render_camera_pass
from state_fixture import StateFixture


class RenderFixture(StateFixture):
    def render(self,kind='aurora'):
        self.client=self.alloc(0xF10,[(0,'<Q',[self.module.base+0x4E632F0])])
        self.viewport=self.alloc(0x748,[(0,'<Q',[self.module.base+0x52F0498]),
            (0x18,'<2H',[1920,1080]),(0x50,'<Q',[self.client+0x80]),(0x740,'<Q',[self.client])])
        self.set(self.client+0x18,'<Q',self.viewport)
        self.render_state=self.alloc(16,[(8,'<Q',[self.client])])
        self.segments.append(Segment(self.module.base+0x80F3840,self.render_state.to_bytes(8,'little')))
        vptr,offset={'aurora':(0x4EC0658,0x6B4),'perspective':(0x4EBF848,0x2D8),
                     'orthographic':(0x4EBFAA0,None)}[kind]
        self.set(self.client+0x80,'<Q',self.module.base+vptr)
        if offset is not None:self.set(self.client+0x80+offset,'<16f',*([1.,0,0,0,0,1.,0,0,0,0,1.,0,0,0,0,1.]))
        self.set(self.a['camera']+0x450,'<B',int(kind=='aurora'))
        self.set(self.a['camera']+0x418,'<B',int(kind=='orthographic'))
        self.set(self.client+0xEE0,'<48s',self.memory().read(self.a['camera']+0x41C,48))
        return self


class RenderCameraTests(unittest.TestCase):
    def test_typed_render_input_and_source_copy_are_part_of_world_capture(self):
        f=RenderFixture().render()
        capture=capture_world(f.memory(),f.module,require_render_input=True)
        camera=capture.render_camera
        self.assertEqual((camera.camera,camera.kind),(f.client+0x80,'aurora'))
        self.assertTrue(camera.source_copy_matched)
        self.assertFalse(camera.presented_pixels_validated)
        self.assertEqual((camera.width,camera.height),(1920,1080))
        self.assertEqual(camera.projection[0],1.)

    def test_perspective_storage_is_distinct_and_orthographic_is_not_guessed(self):
        for kind in ['perspective','orthographic']:
            f=RenderFixture().render(kind)
            value,trace=render_camera_pass(f.memory(),f.module,source_camera=f.a['camera'])
            self.assertEqual(value.kind,kind)
            if kind=='orthographic':self.assertIsNone(value.projection)
            else:self.assertEqual(len(value.projection),16)

    def test_alias_vptr_dimensions_mode_copy_and_projection_failures_reject_strict_capture(self):
        for fault in ['provider','camera','client_type','dimensions','mode','copy','nonfinite']:
            f=RenderFixture().render()
            if fault=='provider':f.set(f.viewport+0x740,'<Q',f.render_state)
            elif fault=='camera':f.set(f.viewport+0x50,'<Q',f.client+0x88)
            elif fault=='client_type':f.set(f.client,'<Q',f.module.base+0x4EC0658)
            elif fault=='dimensions':f.set(f.viewport+0x18,'<H',1280)
            elif fault=='mode':f.set(f.a['camera']+0x450,'<B',0)
            elif fault=='copy':f.set(f.client+0xEE0,'<f',2.)
            else:f.set(f.client+0x80+0x6B4,'<f',math.nan)
            with self.subTest(fault=fault),self.assertRaises(RegistryReadError):
                capture_world(f.memory(),f.module,attempts=1,require_render_input=True)

    def test_missing_render_input_is_explicit_and_strict_mode_requires_it(self):
        f=RenderFixture()
        capture=capture_world(f.memory(),f.module)
        self.assertIsNone(capture.render_camera)
        self.assertIn('MemoryReadError',capture.render_camera_error)
        with self.assertRaisesRegex(RegistryReadError,'required render input'):
            capture_world(f.memory(),f.module,attempts=1,require_render_input=True)

    def test_changed_render_pointer_between_passes_never_returns_partial_capture(self):
        f=RenderFixture().render()
        class ChangingReader:
            count=0
            def read(self,address,size):
                if address==f.viewport+0x50:
                    self.count+=1
                    if self.count==2:f.set(address,'<Q',f.client+0x88)
                return f.memory().read(address,size)
        with self.assertRaisesRegex(RegistryReadError,'render camera changed'):
            capture_world(ChangingReader(),f.module,attempts=1,require_render_input=True)


if __name__=='__main__':unittest.main()
