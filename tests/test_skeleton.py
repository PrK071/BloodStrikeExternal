# Python / tests/test_skeleton.py / Python 3.12+ unittest / pose hierarchy bounds and projected bone edges
import struct
import unittest
from ExternalCore.memory import Segment,SnapshotMemory
from ExternalCore.registry import collect_registry
from ExternalCore.camera_capture import capture_world
from ExternalCore.skeleton import read_pose,skeleton_commands
from registry_fixture import fixture_segments,patch


class SkeletonTests(unittest.TestCase):
    def fixture(self,cycle=False):
        segments,module,a=fixture_segments()
        resource=0x200030000;begin=0x200040000
        segments=patch(segments,a['component']+0xE8,'<Q',a['actor'])
        raw=bytearray(3*0xA0)
        for index,(point,parent) in enumerate((((0,0,0),-1),((0,1,0),0),((0.5,1,0),1))):
            struct.pack_into('<12f',raw,index*0xA0+0x30,1,0,0,0,1,0,0,0,1,*point)
            struct.pack_into('<h',raw,index*0xA0+0x94,2 if cycle and index==1 else parent)
        segments.extend([Segment(a['actor']+0xD8,struct.pack('<Q',resource)),
            Segment(resource+0x10,struct.pack('<2Q',begin,begin+len(raw))),Segment(begin,bytes(raw))])
        return SnapshotMemory(segments),module

    def test_read_actual_layout_and_project_parent_edges(self):
        memory,module=self.fixture()
        capture=capture_world(memory,module)
        record=capture.registry.records[0]
        points,parents=read_pose(memory,record)
        self.assertEqual(parents,(-1,0,1))
        self.assertEqual(points[2],(0.5,1.0,0.0))
        commands=skeleton_commands(memory,record,capture.camera.camera)
        self.assertEqual(len(commands),2)
        self.assertTrue(all(command['kind']=='line' for command in commands))
        self.assertGreater(commands[0]['y1'],commands[0]['y2'])

    def test_cyclic_hierarchy_is_rejected(self):
        memory,module=self.fixture(cycle=True)
        record=collect_registry(memory,module).records[0]
        with self.assertRaisesRegex(ValueError,'cyclic'):
            read_pose(memory,record)
