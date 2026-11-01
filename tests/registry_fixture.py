# Python | tests/registry_fixture.py | Python 3.12+ | synthetic address space, not a game capture.
"""Independent fixture bytes with a nonzero source/target RTTI adjustment."""
import struct

from ExternalCore.build import ModuleIdentity
from ExternalCore.entity_position import SAMPLE_SHA256
from ExternalCore.memory import Segment, SnapshotMemory


def fixture_segments(base=0x180000000, arena=0x200000000):
    root, sentinel, node = arena, arena + 0x100, arena + 0x200
    component, actor, complete = arena + 0x1000, arena + 0x2000, arena + 0x3000
    parent, entity = complete + 0x20, complete + 0x80
    vtable, col, hierarchy, array = base + 0x4008, base + 0x5000, base + 0x6000, base + 0x6100
    segments = []

    def data(address, size, fields):
        buffer = bytearray(size)
        for offset, fmt, values in fields:
            struct.pack_into(fmt, buffer, offset, *values)
        segments.append(Segment(address, bytes(buffer)))

    data(base + 0x8B7CD90, 8, [(0, "<Q", [root])])
    data(root, 0x40, [(8, "<Q", [sentinel])])
    data(sentinel, 0x20, [(0, "<Q", [node])])
    data(node, 0x20, [(0, "<Q", [sentinel]), (0x10, "<I", [0x12345678]),
                             (0x18, "<Q", [component])])
    data(component, 0x380, [(0x40, "<Q", [parent]), (0x378, "<Q", [actor])])
    data(actor, 0x10, [(0xC, "<I", [0x12345678])])
    data(complete, 0x400, [(0x20, "<Q", [vtable]), (0x20 + 0x130, "<B", [0x10]),
                          (0x80 + 0x58, "<12f", [1, 0, 0, 0, 1, 0, 0, 0, 1, 1.25, -2.5, 3.75]),
                          (0x80 + 0x1AC, "<3i", [100, -200, 300])])
    data(vtable - 8, 16, [(0, "<Q", [col])])
    data(col, 24, [(0, "<6I", [1, 0x20, 0, 0x7000, 0x6000, 0x5000])])
    data(hierarchy, 16, [(0, "<4I", [0, 0, 2, 0x6100])])
    data(array, 8, [(0, "<2I", [0x6200, 0x6220])])
    data(base + 0x6200, 24, [(0, "<IIiiiI", [0x7000, 1, 0, -1, 0, 0x40])])
    data(base + 0x6220, 24, [(0, "<IIiiiI", [0x7DE5D78, 0, 0x80, -1, 0, 0x40])])
    # Separate typed camera chain, used by world/scene integration tests.
    engine_root, gameplay, player, camera = arena + 0x400, arena + 0x600, arena + 0x4000, arena + 0x5000
    def rtti(meta, target, entity_base=False):
        count = 2 if entity_base else 1
        data(meta, 16, [(0, "<Q", [meta + 0x20])])
        data(meta + 0x20, 24, [(0, "<6I", [1, 0, 0, target, meta + 0x40 - base, meta + 0x20 - base])])
        data(meta + 0x40, 16, [(0, "<4I", [0, 0, count, meta + 0x60 - base])])
        refs = [meta + 0x80 - base] + ([meta + 0xA0 - base] if entity_base else [])
        data(meta + 0x60, count * 4, [(0, f"<{count}I", refs)])
        data(meta + 0x80, 24, [(0, "<IIiiiI", [target, count-1, 0, -1, 0, 0x40])])
        if entity_base:
            data(meta + 0xA0, 24, [(0, "<IIiiiI", [0x7DE5D78, 0, 0, -1, 0, 0x40])])
        return meta + 8
    gameplay_vptr = rtti(base + 0x8000, 0x7E35098)
    player_vptr = rtti(base + 0x8200, 0x7E57120)
    camera_vptr = rtti(base + 0x8400, 0x7DE5D50, True)
    data(base + 0x80D5980, 8, [(0, "<Q", [engine_root])])
    data(engine_root, 0x60, [(0x58, "<Q", [gameplay])])
    data(gameplay, 0x60, [(0, "<Q", [gameplay_vptr]), (0x58, "<Q", [player])])
    data(player, 0xD90, [(0, "<Q", [player_vptr]), (0xD88, "<Q", [camera])])
    data(camera, 0x458, [(0, "<Q", [camera_vptr]), (0x7C, "<3f", [0, 0, 13.75]),
                        (0x1AC, "<3i", [100, -200, 300]), (0x408, "<2H", [1920, 1080]),
                        (0x41C, "<9f", [1,0,0,0,1,0,0,0,1]), (0x454, "<f", [90])])
    addresses = dict(root=root, sentinel=sentinel, node=node, component=component, actor=actor,
                     complete=complete, parent=parent, entity=entity, vtable=vtable, col=col,
                     hierarchy=hierarchy, array=array, target_bcd=base + 0x6220,
                     position=entity + 0x7C, engine_root=engine_root, gameplay=gameplay,
                     player=player, camera=camera, player_rtti_td=base + 0x8220 + 12,
                     player_rtti_base_td=base + 0x8280)
    return segments, ModuleIdentity(base, 0x94E9000, SAMPLE_SHA256), addresses


def patch(segments, address, fmt, *values):
    size = struct.calcsize(fmt)
    result = []
    found = False
    for segment in segments:
        buffer = bytearray(segment.data)
        if segment.address <= address and address + size <= segment.address + len(buffer):
            struct.pack_into(fmt, buffer, address - segment.address, *values)
            found = True
        result.append(Segment(segment.address, bytes(buffer)))
    if not found:
        raise ValueError("patch address outside fixture")
    return result


def fixture_memory():
    segments, module, addresses = fixture_segments()
    return SnapshotMemory(segments), module, addresses
