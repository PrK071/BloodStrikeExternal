# Python / tools/disassemble_skeleton.py / Python 3.12+ iced-x86 / pinned Blood Strike skeleton binding candidates
import json
import mmap
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'analysis-vendor'))
from iced_x86 import Decoder,Formatter,FormatterSyntax
from inspect_build import PortableExecutable
from ExternalCore.build import verify_sample

sample=verify_sample(sys.argv[1])
bindings=json.loads(Path(sys.argv[2]).read_text())['bindings']
names=('GetPoseBones','GetPoseBoneCount','GetBipedPoseBones','GetBoneWorldTransform','GetPoseBoneParentIds')
output=[];formatter=Formatter(FormatterSyntax.INTEL)
with open(sample['path'],'rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as data:
    pe=PortableExecutable(data)
    candidates={}
    for row in bindings:
        if row['name'].rsplit('.',1)[-1] not in names:continue
        reference=row['references'][-1]
        for slot in reference['slots']:
            if slot['relative_offset'] in (56,64):
                candidates[int(slot['target_rva'],16)]=row['name']+f" +{slot['relative_offset']:x}"
    for text in sys.argv[4:]:candidates[int(text,0)]='selected follow-up'
    for rva,label in sorted(candidates.items()):
        offset=pe.rva_to_offset(rva)
        if offset is None:continue
        instructions=[]
        for instruction in Decoder(64,data[offset:offset+512],ip=pe.image_base+rva):
            text=formatter.format(instruction)
            instructions.append(dict(rva=hex(instruction.ip-pe.image_base),text=text))
            if text.startswith('ret') or len(instructions)>=85:break
        output.append(dict(label=label,rva=hex(rva),instructions=instructions))
Path(sys.argv[3]).write_text(json.dumps(output,indent=2))
for row in output:
    print(row['label'],row['rva'])
    for instruction in row['instructions']:print(instruction['rva'],instruction['text'])
