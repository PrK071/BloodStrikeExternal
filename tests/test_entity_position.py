# Python | tests/test_entity_position.py | Python 3.12+ unittest | offline synthetic IEntity snapshots.
"""Offline synthetic snapshots only; no game/process dependencies."""
import math
import struct
import unittest

from ExternalCore.entity_position import (
    ANCHOR_SENTINEL, SNAPSHOT_SIZE, EntityPositionSnapshot,
    SnapshotDecodeError, decode_entity_position,
)


def make_snapshot(translation=(0.0, 0.0, 0.0), anchor=(0x7FFFFFFF,) * 3, prefix=b""):
    data = bytearray(SNAPSHOT_SIZE)
    struct.pack_into("<12f", data, 0x58, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0,
                     7.0, 8.0, 9.0, *translation)
    struct.pack_into("<3i", data, 0x1AC, *anchor)
    return prefix + data


class EntityPositionTests(unittest.TestCase):
    def test_all_sentinels_select_zero_origin_and_widen_transform(self):
        result = decode_entity_position(make_snapshot((1.25, -2.5, 3.75)))
        self.assertIsInstance(result, EntityPositionSnapshot)
        self.assertFalse(result.anchor_applied)
        self.assertEqual(result.anchor_raw, (ANCHOR_SENTINEL,) * 3)
        self.assertEqual(result.anchor_used, (0, 0, 0))
        self.assertEqual(result.position, (1.25, -2.5, 3.75))
        self.assertEqual(result.transform, tuple(float(i) for i in range(1, 10)) + result.position)

    def test_negative_anchors_are_signed_and_added_in_double(self):
        result = decode_entity_position(make_snapshot((0.5, -0.25, 1.5), (-100, -2**31, 2**31 - 2)))
        self.assertEqual(result.position, (-99.5, -2147483648.25, 2147483647.5))
        self.assertTrue(result.anchor_applied)

    def test_float32_rounding_happens_before_widening(self):
        # 16777217 is rounded to 16777216 on storage as float32.
        result = decode_entity_position(make_snapshot((16777217.0, 0.1, -0.1), (1, 0, 0)))
        self.assertEqual(result.local_translation[0], 16777216.0)
        self.assertEqual(result.position[0], 16777217.0)
        # Adding in float32 would lose the +1 again; the native helper uses double.
        self.assertNotEqual(result.position[0], struct.unpack("<f", struct.pack("<f", 16777217.0))[0])
        self.assertEqual(result.local_translation[1], 0.10000000149011612)
        self.assertEqual(result.local_translation[2], -0.10000000149011612)

    def test_mixed_sentinels_apply_entire_anchor_triple(self):
        for axis in range(3):
            with self.subTest(non_sentinel_axis=axis):
                anchor = [ANCHOR_SENTINEL] * 3
                anchor[axis] = -7
                result = decode_entity_position(make_snapshot((0.5, 0.25, -0.5), tuple(anchor)))
                self.assertTrue(result.anchor_applied)
                self.assertEqual(result.anchor_used, tuple(anchor))
                expected = tuple(float(a) + b for a, b in zip(anchor, (0.5, 0.25, -0.5)))
                self.assertEqual(result.position, expected)
                # Sentinel coordinates in a mixed triple remain large signed ints.
                for other in set(range(3)) - {axis}:
                    self.assertGreater(result.position[other], 2e9)

    def test_exact_size_and_nonzero_entity_offset(self):
        result = decode_entity_position(make_snapshot((3, 4, 5), prefix=b"prefix"), entity_offset=6)
        self.assertEqual(result.position, (3.0, 4.0, 5.0))
        self.assertEqual(len(make_snapshot()), SNAPSHOT_SIZE)
        decode_entity_position(memoryview(make_snapshot()))

    def test_insufficient_buffer_has_clear_bounds(self):
        for size in (0, 0x88, SNAPSHOT_SIZE - 1):
            with self.subTest(size=size), self.assertRaisesRegex(SnapshotDecodeError, "requires 0x1b8"):
                decode_entity_position(bytes(size))
        with self.assertRaisesRegex(SnapshotDecodeError, "buffer end 0x1b9"):
            decode_entity_position(make_snapshot(), entity_offset=1)

    def test_offset_and_buffer_contract(self):
        for offset in (True, 1.0, "0"):
            with self.subTest(offset=offset), self.assertRaises(TypeError):
                decode_entity_position(make_snapshot(), entity_offset=offset)
        with self.assertRaisesRegex(SnapshotDecodeError, "non-negative"):
            decode_entity_position(make_snapshot(), entity_offset=-1)
        with self.assertRaisesRegex(TypeError, "buffer protocol"):
            decode_entity_position("not bytes")
        with self.assertRaisesRegex(TypeError, "contiguous"):
            decode_entity_position(memoryview(bytes(SNAPSHOT_SIZE * 2))[::2])

    def test_mutable_input_is_not_retained_and_nonfinite_values_are_preserved(self):
        data = bytearray(make_snapshot((math.inf, -math.inf, math.nan)))
        result = decode_entity_position(data)
        self.assertEqual(result.position[:2], (math.inf, -math.inf))
        self.assertTrue(math.isnan(result.position[2]))
        data[:] = bytes(len(data))
        self.assertEqual(result.local_translation[:2], (math.inf, -math.inf))


if __name__ == "__main__":
    unittest.main()

