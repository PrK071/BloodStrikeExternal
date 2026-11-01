# Python | tests/test_memory_registry.py | Python 3.12+ unittest | malformed and changing address spaces.
import struct
import unittest

from ExternalCore.build import BuildMismatchError, ModuleIdentity
from ExternalCore.memory import MemoryReadError, Segment, SnapshotMemory, check_range, read_exact
from ExternalCore.registry import RegistryReadError, collect_registry
from ExternalCore.rtti import RttiResolutionError, resolve_nonvirtual_base
from registry_fixture import fixture_memory, fixture_segments, patch


class MemoryTests(unittest.TestCase):
    def test_adjacent_segments_and_input_immutability(self):
        original = bytearray(b"abc")
        reader = SnapshotMemory([Segment(0x100, original), Segment(0x103, b"def")])
        original[:] = b"xyz"
        self.assertEqual(reader.read(0x101, 4), b"bcde")
        self.assertEqual(reader.read(0, 0), b"")
        with self.assertRaises(MemoryReadError):
            reader.read(0x105, 2)

    def test_gaps_overlaps_bounds_and_short_reads(self):
        reader = SnapshotMemory([Segment(1, b"a"), Segment(3, b"b")])
        with self.assertRaises(MemoryReadError):
            reader.read(1, 3)
        with self.assertRaises(ValueError):
            SnapshotMemory([Segment(1, b"ab"), Segment(2, b"c")])
        for address, size in [(-1, 1), (0, -1), (2**64 - 1, 2), (0, 16 * 1024 * 1024 + 1)]:
            with self.subTest(address=address, size=size), self.assertRaises(ValueError):
                check_range(address, size)
        with self.assertRaises(TypeError):
            check_range(True, 2)
        class ShortReader:
            def read(self, address, size):
                return b"a"
        with self.assertRaises(MemoryReadError):
            read_exact(ShortReader(), 0x10000, 8)

    def test_wrong_build_is_rejected_before_reading(self):
        with self.assertRaises(BuildMismatchError):
            ModuleIdentity(0x180000000, 0x94E9000, "0" * 64)


class RegistryTests(unittest.TestCase):
    def test_full_registry_to_adjusted_entity_to_double_position(self):
        reader, module, a = fixture_memory()
        frame = collect_registry(reader, module)
        self.assertEqual((frame.root, frame.sentinel), (a["root"], a["sentinel"]))
        self.assertEqual(len(frame.records), 1)
        record = frame.records[0]
        self.assertEqual(record.key, 0x12345678)
        self.assertEqual(record.parent, a["complete"] + 0x20)
        self.assertEqual(record.entity, a["complete"] + 0x80)
        self.assertEqual(record.position.position, (101.25, -202.5, 303.75))
        self.assertEqual(record.position_status, "decoded_unclassified")
        self.assertEqual(frame.gameplay_classification, "unclassified")
        self.assertIn("no_atomicity_or_lifetime_guarantee", frame.consistency)

    def test_null_root_and_empty_initialized_registry_are_distinct(self):
        segments, module, a = fixture_segments()
        null = SnapshotMemory(patch(segments, module.base + 0x8B7CD90, "<Q", 0))
        empty = SnapshotMemory(patch(segments, a["sentinel"], "<Q", a["sentinel"]))
        self.assertEqual(collect_registry(null, module).root, 0)
        self.assertEqual(collect_registry(empty, module).root, a["root"])
        self.assertEqual(collect_registry(empty, module).records, ())

    def test_no_parent_or_out_of_world_does_not_decode_position(self):
        segments, module, a = fixture_segments()
        for address, fmt, value, status in [
            (a["component"] + 0x40, "<Q", 0, "no_parent"),
            (a["parent"] + 0x130, "<B", 0, "out_of_world"),
        ]:
            with self.subTest(status=status):
                frame = collect_registry(SnapshotMemory(patch(segments, address, fmt, value)), module)
                self.assertEqual(frame.records[0].position_status, status)
                self.assertIsNone(frame.records[0].position)

    def test_cycle_serial_mismatch_null_payload_and_read_failure_never_return_partial_frame(self):
        segments, module, a = fixture_segments()
        corruptions = [(a["node"], "<Q", a["node"]),
                       (a["actor"] + 0xC, "<I", 17),
                       (a["node"] + 0x18, "<Q", 0),
                       (a["node"], "<Q", 0x70000000)]
        for address, fmt, value in corruptions:
            with self.subTest(address=address, value=value), self.assertRaises(RegistryReadError):
                collect_registry(SnapshotMemory(patch(segments, address, fmt, value)), module, attempts=1)

    def test_unknown_rtti_is_a_record_without_invented_position(self):
        segments, module, a = fixture_segments()
        changed = patch(segments, a["target_bcd"], "<I", 0x7000)
        record = collect_registry(SnapshotMemory(changed), module).records[0]
        self.assertTrue(record.position_status.startswith("unsupported_entity_rtti"))
        self.assertIsNone(record.entity)
        self.assertIsNone(record.position)

    def test_key_zero_is_not_rejected_as_a_null_pointer(self):
        segments, module, a = fixture_segments()
        changed = patch(patch(segments, a["node"] + 0x10, "<I", 0), a["actor"] + 0xC, "<I", 0)
        self.assertEqual(collect_registry(SnapshotMemory(changed), module).records[0].key, 0)

    def test_mutation_between_passes_retries_then_observes_new_position(self):
        segments, module, a = fixture_segments()
        class Changing:
            def __init__(self):
                self.reader = SnapshotMemory(segments)
                self.changed = False
            def read(self, address, size):
                result = self.reader.read(address, size)
                if address == a["entity"] and not self.changed:
                    self.reader = SnapshotMemory(patch(segments, a["position"], "<f", 7.5))
                    self.changed = True
                return result
        frame = collect_registry(Changing(), module)
        self.assertEqual(frame.attempts, 2)
        self.assertEqual(frame.records[0].position.position, (107.5, -202.5, 303.75))

    def test_persistent_mutation_has_a_bounded_failure(self):
        segments, module, a = fixture_segments()
        class Changing:
            def __init__(self):
                self.count = 0
            def read(self, address, size):
                self.count += address == a["entity"]
                return SnapshotMemory(patch(segments, a["position"], "<f", self.count)).read(address, size)
        reader = Changing()
        with self.assertRaisesRegex(RegistryReadError, "2 attempt"):
            collect_registry(reader, module, attempts=2)
        self.assertEqual(reader.count, 4)

    def test_node_budget_and_duplicate_key_are_bounded(self):
        segments, module, a = fixture_segments()
        extra_node = a["node"] + 0x100
        raw = bytearray(0x20)
        struct.pack_into("<Q", raw, 0, a["sentinel"])
        struct.pack_into("<I", raw, 0x10, 0x12345678)
        struct.pack_into("<Q", raw, 0x18, a["component"])
        changed = patch(segments, a["node"], "<Q", extra_node) + [Segment(extra_node, bytes(raw))]
        for budget, error in [(1, "budget"), (2, "duplicate")]:
            with self.subTest(budget=budget), self.assertRaisesRegex(RegistryReadError, error):
                collect_registry(SnapshotMemory(changed), module, max_nodes=budget, attempts=1)


class RttiTests(unittest.TestCase):
    def test_nonzero_complete_object_and_base_offsets_are_applied(self):
        reader, module, a = fixture_memory()
        result = resolve_nonvirtual_base(reader, module, a["parent"])
        self.assertEqual(result.complete_object, a["complete"])
        self.assertEqual(result.address, a["entity"])

    def test_virtual_ambiguous_private_and_construction_cases_are_rejected(self):
        segments, module, a = fixture_segments()
        changes = [(a["target_bcd"] + 12, "<i", 0),  # virtual PMD
                   (a["target_bcd"] + 20, "<I", 2), # ambiguous
                   (a["target_bcd"] + 20, "<I", 4), # private/protected
                   (a["col"] + 8, "<I", 8),         # construction displacement
                   (a["col"] + 20, "<I", 0),        # bad self RVA
                   (a["hierarchy"] + 8, "<I", 257)]
        for address, fmt, value in changes:
            with self.subTest(address=address, value=value), self.assertRaises(RttiResolutionError):
                resolve_nonvirtual_base(SnapshotMemory(patch(segments, address, fmt, value)), module, a["parent"])


if __name__ == "__main__":
    unittest.main()
