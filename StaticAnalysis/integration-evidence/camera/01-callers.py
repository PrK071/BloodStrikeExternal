from pathlib import Path
import sys,json,struct,re
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis')
sys.path.insert(0,str(ROOT))
from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'))
assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
out=Path(__file__).parent
cache={}
def rows(r):
 if r not in cache:cache[r]=[pe.row(i) for i in pe.decode(r)]
 return cache[r]
def save(n,x): (out/n).write_text(json.dumps(x,indent=2),encoding='utf8')
res=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(b'[\xe8\xe9]....',b,re.S):
  r=s['rva']+m.start();t=r+5+struct.unpack_from('<i',b,m.start()+1)[0]
  if t not in [0x222ed0,0xc46ca0]:continue
  f=pe.function(r)
  if not f:continue
  rr=rows(f[0]);i=next((i for i,x in enumerate(rr) if int(x['rva'],16)==r and x.get('branch_target_rva')==hex(t)),None)
  if i is not None:res.append({'target':hex(t),'function':hex(f[0]),'around':rr[max(0,i-20):i+8]})
save('entry-callers.json',res);save('entry-caller-functions.json',{hex(k):v for k,v in cache.items()});print(json.dumps(res))
