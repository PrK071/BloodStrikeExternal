from pathlib import Path
import sys,json,re,struct
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis');sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'))
assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
O=Path(__file__).parent
terms=[b'PyInterpreterState_Head',b'PyInterpreterState_Main',b'PyImport_GetModuleDict',b'sys.modules',b'interpreters.head',b'_PyRuntime',b'gclient.genv']
hits=[]
for term in terms:
 p=0
 while (p:=pe.d.find(term,p))>=0:
  hits.append(dict(term=term.decode(),rva=hex(pe.rva(p)),file_offset=hex(p),context=repr(pe.d[max(0,p-40):p+100])));p+=1
targets={int(h['rva'],16) for h in hits}; refs=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',data,re.S):
  r=s['rva']+m.start();t=r+7+struct.unpack_from('<i',m.group(),3)[0]
  # Permit references to beginning of containing diagnostic string.
  matched=[h for h in hits if 0<=int(h['rva'],16)-t<160 and b'\0' not in pe.d[pe.offset(t):pe.offset(int(h['rva'],16))]] if pe.offset(t) else []
  if not matched:continue
  f=pe.function(r)
  if not f:continue
  ins=next((i for i in pe.decode(f[0]) if i.ip-pe.base==r),None)
  if ins and ins.is_ip_rel_memory_operand and ins.ip_rel_memory_address-pe.base==t:
   refs.append(dict(target=hex(t),instruction=hex(r),function=hex(f[0]),terms=[h['term'] for h in matched],rows=[pe.row(i) for i in pe.decode(f[0])]))
(O/'runtime-seeds.json').write_text(json.dumps(dict(sha256=pe.sha,hits=hits,refs=refs),indent=2))
print('hits',[(h['term'],h['rva']) for h in hits]);print('refs',[(r['terms'],r['function']) for r in refs])
