from pathlib import Path
import sys,json,re,struct
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis');sys.path.insert(0,str(ROOT));from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
O=Path(__file__).parent;res=[]
for m in re.finditer(rb'[ -~]{4,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if s in ['Messiah.ICamera.GetOrigin']:
  target=pe.rva(m.start());p=0;blocks=[]
  while (p:=pe.d.find(struct.pack('<Q',pe.base+target),p))>=0:
   st=p-48;vs=struct.unpack_from('<20Q',pe.d,st);blocks.append(dict(pointer_rva=hex(pe.rva(p)),qwords=[dict(rva=hex(pe.rva(st+i*8)),value=hex(v),string=pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None) for i,v in enumerate(vs)]));p+=1
  res.append(dict(string=s,rva=hex(target),blocks=blocks))
(O/'native-origin-blocks.json').write_text(json.dumps(res,indent=2));print([(x['string'],[(b['pointer_rva'],[(q['rva'],q['value']) for q in b['qwords'][10:]]) for b in x['blocks']]) for x in res])



