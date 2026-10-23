import sys,json,struct
from pathlib import Path
sys.path.insert(0,r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis')
from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'))
assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
out=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\audit-v4\spatial')
hits=[]
import re
for m in re.finditer(rb'[ -~]{4,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if ('IEntity.' in s or 'ICamera.' in s) and any(t.lower() in s.lower() for t in ['position','transform','project','matrix']):
  r=pe.rva(m.start());refs=[];pat=struct.pack('<Q',pe.base+r);pos=0
  while (pos:=pe.d.find(pat,pos))>=0:
   rr=pe.rva(pos);start=max(0,pos-32);refs.append({'rva':hex(rr),'around':[hex(x) for x in struct.unpack_from('<'+'Q'*12,pe.d,pos-32)]});pos+=1
  hits.append({'string':s,'rva':hex(r),'refs':refs})
(out/'strings-pointers.json').write_text(json.dumps(hits,indent=2))
print(json.dumps(hits,indent=2))
