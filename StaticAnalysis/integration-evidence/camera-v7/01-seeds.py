from pathlib import Path
import sys,json,re,struct
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis');sys.path.insert(0,str(ROOT));from audit_v2 import RawPE
pe=RawPE(Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe'));assert pe.sha=='ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
O=Path(__file__).parent
names=[]
for m in re.finditer(rb'[\x20-\x7e]{4,}',pe.d):
 s=m.group()
 if any(t in s for t in [b'MainCamera',b'ActiveCamera',b'CurrentCamera',b'RenderCamera',b'MainViewport',b'DefaultViewport',b'GetViewport',b'SetViewport',b'Viewport.Camera',b'ViewportCamera',b'GetCamera',b'SetCamera',b'AffiliatedViewport']):
  names.append(dict(rva=hex(pe.rva(m.start())),file_offset=hex(m.start()),text=s.decode()))
found={};matches=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(b'\x88\x0d\x00\x00',data):
  r=s['rva']+m.start();f=pe.function(r)
  if not f:continue
  if f[0] not in found:found[f[0]]=[pe.row(i) for i in pe.decode(f[0])]
  rows=found[f[0]]
  hit=[x for x in rows if int(x['rva'],16)<=r<int(x['rva'],16)+x['length'] and '0D88h' in x['text']]
  if hit:matches.append(dict(instruction=hit[0],region=[hex(x) for x in f],rows=rows))
(O/'seeds.json').write_text(json.dumps(dict(sha256=pe.sha,names=names,camera_d88_refs=matches),indent=2))
print('names',len(names));print('\n'.join(x['rva']+' '+x['text'] for x in names if len(x['text'])<180));print('d88',[(x['region'][0],x['instruction']['text']) for x in matches])
