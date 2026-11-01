# Python | tests/test_screenpoint.py | Python 3.12+ unittest | camera helper contract, no live camera.
import math
import struct
import unittest

from ExternalCore.screenpoint import (CameraSnapshot, _quantize_tenth, decode_camera,
                                       project_screenpoint)

IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


class ScreenPointTests(unittest.TestCase):
    def test_camera_fields_and_center_projection(self):
        raw = bytearray(0x458)
        struct.pack_into("<3f", raw, 0x7C, 100, -200, 300)
        struct.pack_into("<2H", raw, 0x408, 1920, 1080)
        struct.pack_into("<9f", raw, 0x41C, *IDENTITY)
        struct.pack_into("<f", raw, 0x454, 90)
        camera = decode_camera(raw)
        result = project_screenpoint(camera, (100, -200, 290))
        self.assertEqual((result.x, result.y, result.depth), (960, 540, 10))
        self.assertTrue(result.in_front)
        self.assertTrue(result.inside_viewport)

    def test_vertical_fov_and_non_square_viewport(self):
        camera = CameraSnapshot((0, 0, 0), IDENTITY, 1920, 1080, 90)
        # For a 90-degree vertical FOV, X/Z=1 is 540 pixels from the center.
        point = project_screenpoint(camera, (10, 10, -10))
        self.assertEqual((point.x, point.y), (1500, 0))
        self.assertTrue(point.inside_viewport)
        point = project_screenpoint(camera, (0, -10, -10))
        self.assertEqual(point.y, 1080)
        self.assertFalse(point.inside_viewport)

    def test_behind_and_zero_depth_do_not_become_targets(self):
        camera = CameraSnapshot((0, 0, 0), IDENTITY, 1920, 1080, 90)
        for position in ((0, 0, 1), (0, 0, 0)):
            result = project_screenpoint(camera, position)
            self.assertEqual((result.x, result.y, result.depth), (960, 540, -1))
            self.assertFalse(result.in_front)
            self.assertFalse(result.inside_viewport)

    def test_basis_orientation_and_world_origin_are_not_transposed(self):
        # Input X contributes to camera Y; input Y contributes to camera X.
        camera = CameraSnapshot((20, 30, 40), (0, 1, 0, 1, 0, 0, 0, 0, 1), 1000, 1000, 90)
        point = project_screenpoint(camera, (21, 32, 30))
        self.assertEqual((point.x, point.y, point.depth), (600, 450, 10))

    def test_quantization_is_half_away_and_float32_output(self):
        self.assertEqual(_quantize_tenth(0.05), struct.unpack("<f", bytes.fromhex("cdcccc3d"))[0])
        self.assertEqual(_quantize_tenth(-0.05), -struct.unpack("<f", bytes.fromhex("cdcccc3d"))[0])
        self.assertEqual(_quantize_tenth(1.25), struct.unpack("<f", bytes.fromhex("6766a63f"))[0])
        self.assertLess(math.copysign(1, _quantize_tenth(-0.0)), 0)

    def test_invalid_camera_and_nonfinite_inputs_fail_explicitly(self):
        with self.assertRaises(ValueError):
            decode_camera(bytes(0x457))
        for width, fov in ((0, 90), (1920, 0), (1920, 180), (1920, math.nan)):
            with self.subTest(width=width, fov=fov), self.assertRaises(ValueError):
                project_screenpoint(CameraSnapshot((0, 0, 0), IDENTITY, width, 1080, fov), (0, 0, -1))
        for point in ((math.nan, 0, -1), (0, 0, -math.inf), (1e100, 0, -1)):
            with self.subTest(point=point), self.assertRaises(ValueError):
                project_screenpoint(CameraSnapshot((0, 0, 0), IDENTITY, 1920, 1080, 90), point)


if __name__ == "__main__":
    unittest.main()
