# Python / tools/probe_skeleton.py / Python 3.12+ Windows x64 / observed actor skeleton layout
import json
import math
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ExternalCore.build import ModuleIdentity,verify_sample
from ExternalCore.pipeline import process_frame
from ExternalCore.scene import Category
from ExternalCore.snapshot import write_json
from ExternalCore.win32_memory import WindowsProcessMemory,find_module
from ExternalCore.skeleton import read_pose

pid=int(sys.argv[1]);sample=verify_sample(sys.argv[2]);output=Path(sys.argv[3])
report=dict(status='RUNNING')
write_json(output,report)
try:
    with WindowsProcessMemory(pid) as reader:
        mapped=find_module(pid,sample['path']);module=ModuleIdentity(mapped.base,mapped.size,sample['sha256'])
        frame=process_frame(reader,module,allow_motion=True)
        opponents={actor.observation.key for actor in frame.scene.actors if actor.classification.category is Category.OPPONENT}
        record=next(record for record in frame.capture.registry.records if record.key in opponents)
        pointer=lambda address:struct.unpack('<Q',reader.read(address,8))[0]
        skeleton=pointer(record.component+0xE8)
        resource=pointer(record.actor+0xD8)
        begin,end=struct.unpack('<2Q',reader.read(resource+0x10,16))
        if end<begin or (end-begin)%0xA0 or not 1<=(end-begin)//0xA0<=2048:raise ValueError('unsupported bone vector bounds')
        raw=reader.read(begin,end-begin);bones=[]
        for index,offset in enumerate(range(0,len(raw),0xA0)):
            cell=raw[offset:offset+0xA0]
            size,capacity=struct.unpack_from('<2Q',cell,16)
            name=None
            if size<=128 and size<=capacity and capacity<=4096:
                try:
                    value=cell[:size] if capacity<16 else reader.read(struct.unpack_from('<Q',cell)[0],size)
                    name=value.decode('ascii')
                except (OSError,UnicodeError):pass
            bones.append(dict(index=index,name=name,header=cell[:48].hex(),
                matrix=struct.unpack_from('<12f',cell,0x30),parent=struct.unpack_from('<h',cell,0x94)[0]))
        report.update(status='OBSERVED',actor=record.actor,component=record.component,
            skeleton_alias=skeleton==record.actor,resource=resource,begin=begin,
            bones=bones,root_position=record.position, camera=frame.capture.camera.camera)
        verified_points,verified_parents=read_pose(reader,record)
        report['reader_validation']=dict(bones=len(verified_points),roots=verified_parents.count(-1),
            bounded_parent_hierarchy=True)
except Exception as exc:report.update(status='ERROR',error=str(exc))
write_json(output,report)
