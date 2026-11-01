from pathlib import Path
import sys,json,struct,re
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis');sys.path.insert(0,str(ROOT));from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
O=Path(__file__).parent;out={}
for r in [0x7a135a0,0x7a21e50,0x796f3c0,0x796a420,0x796c240]:
 name=pe.unpack('<Q',r+0x18)[0]-pe.base
 fields={hex(k):hex(pe.unpack('<Q',r+k)[0]) for k in [8,0x18,0x20,0x28,0x60,0x68,0x70,0x90,0x98,0x110,0x118]}
 out[hex(r)]={'name':pe.string(name),'fields':fields};print(hex(r),out[hex(r)])
# Discover candidate static types by exact C tp_name string + shape; native linkage follows.
candidates=[]
for name in [b'method',b'staticmethod',b'classmethod',b'property',b'method_descriptor',b'getset_descriptor',b'member_descriptor']:
 p=0
 while (p:=pe.d.find(name+b'\0',p))>=0:
  if p and pe.d[p-1]:p+=1;continue
  nr=pe.rva(p);q=0
  while (q:=pe.d.find(struct.pack('<Q',pe.base+nr),q))>=0:
   tr=pe.rva(q)-0x18
   if pe.offset(tr,0x1a0) is not None and pe.unpack('<Q',tr+8)[0]==pe.base+0x7a15170:
    row={'name':name.decode(),'type_rva':hex(tr),'name_rva':hex(nr),'basicsize':hex(pe.unpack('<Q',tr+0x20)[0]),'get':hex(pe.unpack('<Q',tr+0x110)[0]-pe.base),'set':hex(pe.unpack('<Q',tr+0x118)[0]-pe.base)};candidates.append(row);print(row)
   q+=1
  p+=1
out['candidates']=candidates;(O/'type-shapes.json').write_text(json.dumps(out,indent=2))
