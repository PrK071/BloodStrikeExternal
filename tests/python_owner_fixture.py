# Python | tests/python_owner_fixture.py | Python 3.12+ | synthetic 3.14 metadata, never executed as Python.
import struct

from ExternalCore.memory import Segment
from registry_fixture import fixture_segments, patch


def python_fixture(*, weapon=False, subclass=False):
    segments, module, a = fixture_segments()
    base, cursor = module.base, 0x200010000
    def alloc(size, fields=()):
        nonlocal cursor
        address = (cursor+7) & ~7
        buffer = bytearray(size)
        for offset, fmt, values in fields:
            struct.pack_into(fmt, buffer, offset, *values)
        segments.append(Segment(address, bytes(buffer)))
        cursor = address + size
        return address
    def ascii_string(value):
        encoded = value.encode("ascii") + b"\0"
        return alloc(40+len(encoded), [(0,"<QQ",[1,base+0x7A16E10]), (16,"<q",[len(value)]),
                                      (32,"<I",[0x64]), (40,f"<{len(encoded)}s",[encoded])])
    def dictionary(values):
        count = len(values)
        raw = bytearray(32+8+16*count)
        struct.pack_into("<q", raw,0,1)
        raw[8:11] = bytes([3,3,1])
        struct.pack_into("<2q",raw,16,5-count,count)
        raw[32:40] = b"\xff"*8
        for index,(key,value) in enumerate(values.items()):
            raw[32+index] = index
            struct.pack_into("<QQ",raw,40+16*index,ascii_string(key),value)
        keys = alloc(len(raw), [(0,f"<{len(raw)}s",[bytes(raw)])])
        obj = alloc(48, [(0,"<QQqQQQ",[1,base+0x7A19900,count,0,keys,0])])
        return obj, keys
    def mro(classes):
        return alloc(32+8*len(classes), [(0,"<QQqQ",[1,base+0x7A18CE0,len(classes),0xDEADBEEFDEADBEEF]),
                                        (32,f"<{len(classes)}Q",classes)])
    def python_type(name, attrs, address=None, bases=(), dict_offset=0, basicsize=48):
        head = bytearray(0x160)
        if address is None:
            address = alloc(len(head))
        type_dict, keys = dictionary(attrs)
        c_name = alloc(len(name)+1, [(0,f"<{len(name)+1}s",[name.encode()+b"\0"])])
        struct.pack_into("<QQ",head,0,1,base+0x7A15170)
        struct.pack_into("<Qq",head,24,c_name,basicsize)
        struct.pack_into("<I",head,0xA8,0x1000)
        struct.pack_into("<Q",head,0x108,type_dict)
        struct.pack_into("<q",head,0x120,dict_offset)
        struct.pack_into("<Q",head,0x158,mro([address,*bases]))
        if any(s.address == address for s in segments):
            segments[:] = patch(segments,address,f"<{len(head)}s",bytes(head))
        else:
            segments.append(Segment(address,bytes(head)))
        return address, type_dict, keys
    pyentity,_,_ = python_type("MObject.IEntity",{},base+0x79A0060,dict_offset=0x10)
    entity_type,_,_ = python_type("asiocore.entity",{},base+0x796F3C0,dict_offset=0x10,basicsize=40)
    area_type,_,_ = python_type("asiocore.area",{},base+0x796C240,dict_offset=0x10,basicsize=40)
    owner_cls,owner_dict,owner_keys = python_type("PlayerCombatAvatar",{"IsPlayerCombatAvatar":base+0x7A129B0},
        bases=(entity_type,),dict_offset=0x10,basicsize=40)
    host = alloc(40,[(0,"<QQ",[1,owner_cls])])
    native_area = alloc(0x1E0)
    area_bridge = alloc(16,[(0,"<Q",[native_area])])
    owner = alloc(40,[(0,"<QQ",[1,area_type]),(0x20,"<Q",[area_bridge])])
    host_bridge = alloc(24,[(0,"<Q",[host]),(0x10,"<Q",[owner])])
    segments=patch(segments,host+0x20,"<Q",host_bridge)
    segments=patch(segments,native_area+0x38,"<Q",host_bridge)
    module_name = "gclient.gameplay.logic_base.models.weapon_model" if weapon else "gclient.gameplay.logic_base.models.avatar_model"
    model_cls,_,_ = python_type("WeaponModel" if weapon else "AvatarModel",{"__module__":ascii_string(module_name)},dict_offset=0x10)
    if subclass:
        model_cls,_,_ = python_type("PlayerAvatarModel",{"__module__":ascii_string("fixture.subclass")},bases=(model_cls,),dict_offset=0x10)
    instance = alloc(48,[(0,"<QQ",[1,model_cls])])
    wrapper_dict,wrapper_keys = dictionary({"owner":owner,"instance":instance})
    control, association, wrapper = alloc(24),alloc(24),alloc(32)
    python = alloc(48,[(0,"<QQQ",[1,pyentity,wrapper_dict]), (0x20,"<Q",[wrapper])])
    host_dict,_=dictionary({"model":instance})
    model_dict,_=dictionary({"model":python})
    segments=patch(segments,host+0x10,"<Q",host_dict)
    segments=patch(segments,instance+0x10,"<Q",model_dict)
    segments = patch(segments,control+8,"<QQ",a["entity"],association)
    segments = patch(segments,association,"<QQQ",control,wrapper,python)
    segments = patch(segments,wrapper+8,"<Q",python)
    segments = patch(segments,wrapper+0x18,"<Q",a["entity"])
    segments = patch(segments,a["entity"]+0x18,"<Q",control)
    segments = patch(segments,a["component"]+0x40,"<Q",a["entity"])
    segments = patch(segments,a["entity"]+0x130,"<B",0x10)
    # The Parent for this fixture is the IEntity subobject itself, with its own RTTI.
    meta = base+0x9000
    raw = bytearray(0xA0)
    struct.pack_into("<Q",raw,0,meta+0x20)
    struct.pack_into("<6I",raw,0x20,1,0,0,0x7DE5D78,0x9040,0x9020)
    struct.pack_into("<4I",raw,0x40,0,0,1,0x9060)
    struct.pack_into("<I",raw,0x60,0x9080)
    struct.pack_into("<IIiiiI",raw,0x80,0x7DE5D78,0,0,-1,0,0x40)
    segments.append(Segment(meta,bytes(raw)))
    segments = patch(segments,a["entity"],"<Q",meta+8)
    a.update(python=python, wrapper=wrapper, control=control, owner=owner, instance=instance,
             owner_dict=owner_dict, owner_keys=owner_keys, owner_entries=owner_keys+40,
             owner_value_slot=owner_keys+48, wrapper_dict=wrapper_dict, wrapper_keys=wrapper_keys,
             host=host,native_area=native_area,area_bridge=area_bridge,host_bridge=host_bridge)
    return segments,module,a
