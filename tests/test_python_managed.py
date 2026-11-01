# Python | tests/test_python_managed.py | Python 3.12+ unittest | synthetic CPython 3.14 GIL data.
import struct
import unittest

from ExternalCore.build import ModuleIdentity
from ExternalCore.entity_position import SAMPLE_SHA256
from ExternalCore.memory import Segment, SnapshotMemory
from ExternalCore.python_managed import managed_instance_dict
from ExternalCore.python_owner import DataReader, PythonLayoutError


class ManagedFixture:
    """An isolated address space; no imported game fixture or target execution."""
    arena = 0x200010000
    model = 0x200090000

    def __init__(self, *, inline=True, names=("model", "other", "unused"),
                 pointers=None, capacity=5):
        self.raw = bytearray(65536)
        self.cursor = 0x100
        self.module = ModuleIdentity(0x180000000, 0x10000000, SAMPLE_SHA256)
        self.cls = self.alloc(0x380)
        self.head = bytearray(0x160)
        struct.pack_into("<2q", self.head, 0x20, 0x20, 0)
        struct.pack_into("<I", self.head, 0xA8, 0x214 if inline else 0x210)
        struct.pack_into("<q", self.head, 0x120, -1)
        self.keys = self.key_table(names, kind=2)
        self.pack(self.cls + 0x370, "<Q", self.keys)
        storage = self.alloc(32 + 0x20 + 8 + capacity * 8)
        self.obj = storage + 32
        self.pack(self.obj, "<QQ", 1, self.cls)
        self.values = self.obj + 0x20
        if pointers is None:
            pointers = [self.model] + [0] * (len(names) - 1)
        self.put_values(self.values, pointers, capacity, embedded=1, valid=1)

    def alloc(self, size):
        self.cursor = (self.cursor + 7) & ~7
        address = self.arena + self.cursor
        self.cursor += size
        return address

    def pack(self, address, fmt, *values):
        struct.pack_into(fmt, self.raw, address - self.arena, *values)

    def ascii(self, name):
        encoded = name.encode("ascii") + b"\0"
        obj = self.alloc(40 + len(encoded))
        self.pack(obj, "<QQq", 1, self.module.address(0x7A16E10), len(name))
        self.pack(obj + 32, "<I", 0x64)
        self.pack(obj + 40, f"<{len(encoded)}s", encoded)
        return obj

    def key_table(self, names, *, kind):
        entries = [(self.ascii(name), 0x2000BAD00) for name in names]
        obj = self.alloc(32 + 64 + 16 * len(entries))
        self.pack(obj, "<Q", 1)
        self.pack(obj + 8, "<3B", 6, 6, kind)
        self.pack(obj + 16, "<2q", 30 - len(entries), len(entries))
        self.pack(obj + 32, "<64s", bytes(range(len(entries))) + b"\xff" * (64 - len(entries)))
        for index, (key, ignored_value) in enumerate(entries):
            self.pack(obj + 96 + index * 16, "<QQ", key, ignored_value)
        return obj

    def put_values(self, obj, pointers, capacity, *, embedded, valid):
        self.pack(obj, "<4B", capacity, sum(bool(x) for x in pointers), embedded, valid)
        self.pack(obj + 8, f"<{capacity}Q", *(list(pointers) + [0] * (capacity - len(pointers))))

    def dictionary(self, keys, values, used):
        obj = self.alloc(48)
        self.pack(obj, "<QQqQQQ", 1, self.module.address(0x7A19900), used, 0, keys, values)
        self.pack(self.obj - 0x18, "<Q", obj)
        return obj

    def split(self, *, embedded=0, valid=0xA5):
        values = self.alloc(8 + 5 * 8)
        self.put_values(values, [self.model, 0, 0], 5, embedded=embedded, valid=valid)
        dictionary = self.dictionary(self.keys, values, 1)
        return dictionary, values

    def combined(self):
        keys = self.key_table(("model",), kind=1)
        self.pack(keys + 96 + 8, "<Q", self.model)
        return self.dictionary(keys, 0, 1)

    def reader(self, **kwargs):
        return DataReader(SnapshotMemory([Segment(self.arena, bytes(self.raw[:self.cursor]))]),
                          self.module, **kwargs)

    def attributes(self, **kwargs):
        return managed_instance_dict(self.reader(**kwargs), self.obj, bytes(self.head))


class ManagedInstanceTests(unittest.TestCase):
    def test_inline_uses_type_size_and_shared_indices_with_null_unused_values(self):
        f = ManagedFixture(pointers=[0, ManagedFixture.model, 0])
        self.assertEqual(f.attributes(), {"other": f.model})
        # Move the entire inline area: no hard-coded instance-values offset.
        old = bytes(f.raw[f.values-f.arena:f.values-f.arena+48])
        f.pack(f.obj + 0x60, "<48s", old)
        f.cursor = max(f.cursor, f.obj-f.arena+0x60+48)
        struct.pack_into("<q", f.head, 0x20, 0x60)
        self.assertEqual(f.attributes(), {"other": f.model})

    def test_valid_inline_precedes_even_an_unreadable_materialized_dict(self):
        f = ManagedFixture()
        f.pack(f.obj - 0x18, "<Q", 1)
        data = f.reader()
        self.assertEqual(managed_instance_dict(data, f.obj, f.head), {"model": f.model})
        self.assertNotIn(f.obj - 0x18, [address for address, _ in data.trace])

    def test_plain_minus_18_pointer_combined_fallback_and_null(self):
        f = ManagedFixture(inline=False)
        self.assertEqual(f.attributes(), {})
        dictionary = f.combined()
        self.assertEqual(f.attributes(), {"model": f.model})
        # A tagged value must be rejected, not masked into a valid dict pointer.
        f.pack(f.obj - 0x18, "<Q", dictionary | 1)
        with self.assertRaises(PythonLayoutError):
            f.attributes()

    def test_invalidated_inline_falls_back_to_existing_dictionary(self):
        f = ManagedFixture()
        f.pack(f.values + 3, "<B", 0)
        f.combined()
        self.assertEqual(f.attributes(), {"model": f.model})
        f.pack(f.obj - 0x18, "<Q", 0)
        self.assertEqual(f.attributes(), {})

    def test_split_schema_count_exceeds_used_and_nonembedded_valid_is_uninitialized(self):
        f = ManagedFixture(inline=False)
        _, values = f.split(valid=0xA5)
        self.assertEqual(f.attributes(), {"model": f.model})
        f.pack(values + 3, "<B", 0)
        self.assertEqual(f.attributes(), {"model": f.model})

    def test_embedded_split_validity_and_live_counts_are_checked(self):
        f = ManagedFixture(inline=False)
        dictionary, values = f.split(embedded=1, valid=1)
        self.assertEqual(f.attributes(), {"model": f.model})
        for address, fmt, value in [(values+3, "<B", 0), (values+1, "<B", 2),
                                    (dictionary+16, "<q", 2)]:
            with self.subTest(address=address):
                original = bytes(f.raw)
                f.pack(address, fmt, value)
                with self.assertRaises(PythonLayoutError):
                    f.attributes()
                f.raw[:] = original

    def test_capacity_limit_shared_bounds_and_index_integrity(self):
        f = ManagedFixture(capacity=30)
        self.assertEqual(f.attributes(), {"model": f.model})
        patches = [(f.values, "<B", 31), (f.values, "<B", 0),
                   (f.values+1, "<B", 31), (f.values+2, "<B", 0),
                   (f.keys+24, "<q", 31), (f.keys+32, "<b", 9),
                   (f.keys+33, "<b", 0), (f.keys+10, "<B", 1),
                   (f.values+8+3*8, "<Q", f.model)]
        for address, fmt, value in patches:
            with self.subTest(address=address, value=value):
                original = bytes(f.raw)
                f.pack(address, fmt, value)
                with self.assertRaises(PythonLayoutError):
                    f.attributes()
                f.raw[:] = original

    def test_budget_errors_and_non_unicode_shared_keys_do_not_disappear(self):
        f = ManagedFixture()
        with self.assertRaisesRegex(PythonLayoutError, "budget"):
            f.attributes(max_bytes=1)
        first_key, = struct.unpack_from("<Q", f.raw, f.keys-f.arena+96)
        f.pack(first_key+8, "<Q", f.module.address(0x7A127F0))
        with self.assertRaisesRegex(PythonLayoutError, "Unicode"):
            f.attributes()


if __name__ == "__main__":
    unittest.main()
