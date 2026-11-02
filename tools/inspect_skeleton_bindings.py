# Python / tools/inspect_skeleton_bindings.py / Python 3.12+ / pinned Blood Strike PE reflection inventory
import json
import mmap
from pathlib import Path
import re
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspect_build import PortableExecutable
from ExternalCore.build import verify_sample

sample=verify_sample(sys.argv[1]);output=Path(sys.argv[2])
rows=[]
with open(sample['path'],'rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as data:
    pe=PortableExecutable(data)
    pattern=rb'(?:Messiah|CharacterImp)\.(?:ActorComponent|SkeletonComponent|ISkeletonComponent)\.[A-Za-z0-9_]+\x00'
    for match in re.finditer(pattern,data):
        name=match.group()[:-1].decode()
        method=name.rsplit('.',1)[-1]
        if not any(word in method.lower() for word in ('bone','hardpoint','pose','matrix','transform','skeleton')):continue
        rva=pe.offset_to_rva(match.start());marker=struct.pack('<Q',pe.image_base+rva)
        references=[];position=0
        while len(references)<24:
            found=data.find(marker,position)
            if found<0:break
            position=found+1
            slots=[]
            for offset in range(max(0,found-0x40),min(len(data)-8,found+0x78),8):
                value=struct.unpack_from('<Q',data,offset)[0]
                candidate=value-pe.image_base
                if 0<=candidate<pe.image_size:
                    slots.append(dict(relative_offset=offset-found,target_rva=hex(candidate)))
            references.append(dict(rva=hex(pe.offset_to_rva(found)),slots=slots))
        rows.append(dict(name=name,rva=hex(rva),references=references))
output.write_text(json.dumps(dict(sample=sample,bindings=rows,scope='ordinary offline PE byte inspection, not REA Evidence'),indent=2),encoding='utf-8')
print(json.dumps([dict(name=row['name'],rva=row['rva'],references=len(row['references'])) for row in rows],indent=2))
