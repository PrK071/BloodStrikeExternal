# Python | tests/test_python_owner.py | Python 3.12+ unittest | guarded, synthetic CPython 3.14 data reads.
import unittest
import struct

from ExternalCore.aim import AimProfile
from ExternalCore.memory import Segment, SnapshotMemory
from ExternalCore.pipeline import process_frame
from ExternalCore.python_owner import DataReader, PythonLayoutError
from ExternalCore.scene import Category
from python_owner_fixture import python_fixture
from registry_fixture import patch


class PythonOwnerTests(unittest.TestCase):
    def test_bidirectional_wrapper_dict_owner_tag_and_avatar_mro(self):
        segments,module,a = python_fixture()
        result = process_frame(SnapshotMemory(segments),module,active=True,profile=AimProfile(counts_per_pixel=(1,1)))
        actor = result.scene.actors[0]
        self.assertEqual(actor.classification.category,Category.PLAYER)
        self.assertIsNone(actor.classification.local)
        self.assertIsNone(actor.classification.alive)
        self.assertEqual(result.aim.reason,"no_classified_target")
        self.assertIn("stored_primary_links_no_team_or_life_proof",actor.classification.evidence)
        self.assertEqual(result.capture.registry.records[0].parent,a["entity"])

    def test_avatar_subclass_is_supported_by_mro_but_weapon_owner_is_not_a_body(self):
        for weapon,subclass,expected in [(False,True,Category.PLAYER),(True,False,Category.UNKNOWN)]:
            with self.subTest(weapon=weapon,subclass=subclass):
                segments,module,_ = python_fixture(weapon=weapon,subclass=subclass)
                result = process_frame(SnapshotMemory(segments),module)
                self.assertEqual(result.scene.actors[0].classification.category,expected)

    def test_false_class_tag_and_expired_wrapper_do_not_classify(self):
        segments,module,a = python_fixture()
        for changed in [patch(segments,a["owner_value_slot"],"<Q",module.base+0x7A12990),
                        patch(segments,a["wrapper"]+0x18,"<Q",0)]:
            with self.subTest():
                frame = process_frame(SnapshotMemory(changed),module)
                self.assertEqual(frame.scene.actors[0].classification.category,Category.UNKNOWN)

    def test_general_key_entries_use_the_verified_24_byte_layout(self):
        segments,module,a = python_fixture()
        memory = SnapshotMemory(segments)
        old = memory.read(a["wrapper_keys"],72)
        raw = bytearray(88)
        raw[:40] = old[:40]
        raw[10] = 0
        for index in range(2):
            key,value = struct.unpack_from("<QQ",old,40+16*index)
            struct.pack_into("<qQQ",raw,40+24*index,index,key,value)
        address = 0x200040000
        changed = patch(segments,a["wrapper_dict"]+32,"<Q",address)+[Segment(address,bytes(raw))]
        frame = process_frame(SnapshotMemory(changed),module)
        self.assertEqual(frame.scene.actors[0].classification.category,Category.PLAYER)

    def test_split_dictionary_and_managed_wrapper_are_explicitly_unsupported(self):
        segments,module,a = python_fixture()
        for changed in [patch(segments,a["wrapper_dict"]+40,"<Q",a["owner"]),
                        patch(segments,module.base+0x79A0060+0xA8,"<I",0x1010)]:
            with self.subTest():
                result = process_frame(SnapshotMemory(changed),module)
                self.assertEqual(result.scene.actors[0].classification.category,Category.UNKNOWN)
                self.assertIn("unsupported",result.scene.actors[0].classification.evidence)

    def test_inconsistent_dictionary_indices_and_read_budget_are_rejected(self):
        segments,module,a = python_fixture()
        changed = patch(segments,a["wrapper_keys"]+32,"<b",7)
        with self.assertRaisesRegex(PythonLayoutError,"index is outside"):
            DataReader(SnapshotMemory(changed),module).dictionary(a["wrapper_dict"])
        with self.assertRaisesRegex(PythonLayoutError,"budget"):
            DataReader(SnapshotMemory(segments),module,max_bytes=1).dictionary(a["wrapper_dict"])

    def test_metadata_change_between_passes_removes_the_positive_result(self):
        segments,module,a = python_fixture()
        class Mutating:
            def __init__(self): self.reader,self.changed = SnapshotMemory(segments),False
            def read(self,address,size):
                raw = self.reader.read(address,size)
                if address == a["owner_entries"] and not self.changed:
                    self.reader = SnapshotMemory(patch(segments,a["owner_value_slot"],"<Q",module.base+0x7A12990))
                    self.changed = True
                return raw
        frame = process_frame(Mutating(),module)
        self.assertEqual(frame.scene.actors[0].classification.category,Category.UNKNOWN)
        self.assertIn("changed between reads",frame.scene.actors[0].classification.evidence)

    def test_refcount_changes_do_not_fake_an_attribute_or_identity_change(self):
        segments,module,_ = python_fixture()
        class Refcounts:
            def __init__(self): self.reader,self.sequence = SnapshotMemory(segments),0
            def read(self,address,size):
                raw = bytearray(self.reader.read(address,size))
                if size == 0x160:  # Type header; refcount is not an identity generation.
                    self.sequence += 1
                    struct.pack_into("<Q",raw,0,self.sequence)
                return bytes(raw)
        result = process_frame(Refcounts(),module)
        self.assertEqual(result.scene.actors[0].classification.category,Category.PLAYER)


if __name__ == "__main__": unittest.main()
