from pathlib import Path
import sys,json,struct,re
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis');sys.path.insert(0,str(ROOT));from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
O=Path(__file__).parent;out=[]
for name in [b'area_map',b'area',b'prop',b'set_prop_desc',b'area_entity',b'area_object']:
 p=0
 while (p:=pe.d.find(name+b'\0',p))>=0:
  if p and pe.d[p-1]:p+=1;continue
  r=pe.rva(p);q=0;refs=[]
  while (q:=pe.d.find(struct.pack('<Q',pe.base+r),q))>=0:
   start=pe.rva(q)-8;rows=[]
   for k in range(0,48,8):
    v=pe.unpack('<Q',start+k)[0];rows.append(dict(rva=hex(start+k),value=hex(v),string=pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None))
   refs.append(rows);q+=1
  out.append(dict(name=name.decode(),string_rva=hex(r),refs=refs));print(name.decode(),hex(r),'refs',len(refs))
  if True:print(json.dumps(refs,indent=2))
  p+=1
(O/'native-area-names.json').write_text(json.dumps(out,indent=2))

