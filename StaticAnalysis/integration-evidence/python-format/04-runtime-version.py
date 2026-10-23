exec((__import__('pathlib').Path(__file__).parent/'01-pe-version.py').read_text().split('res=[]')[0])
import struct
from pathlib import Path
out=Path(__file__).parent;res=[];functions={}
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',b,re.S):
  r=s['rva']+m.start();t=r+6+struct.unpack_from('<i',b,m.start()+2)[0]
  if t!=0x58bee18:continue
  f=pe.function(r)
  if f:
   rr=[pe.row(i) for i in pe.decode(f[0])];functions[hex(f[0])]=rr;res.append({'function':hex(f[0]),'candidate_rva':hex(r)})
(out/'runtime-version-function.json').write_text(json.dumps({'refs':res,'functions':functions},indent=2));print(json.dumps({'refs':res,'functions':functions},indent=2))

