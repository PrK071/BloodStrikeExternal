exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
from audit_v2 import FlowControl
O=Path(__file__).parent;out={}
for r in [0x4843c0,0x486cf0,0x490740,0x276280]:
 rows=[pe.row(i) for i in pe.decode(r)];types=[]
 for x in rows:
  t=x.get('rip_target_rva')
  if not t or not x['text'].startswith('lea '):continue
  tr=int(t,16)
  try:
   col=pe.unpack('<Q',tr-8)[0]-pe.base
   sig,off,cd,td,chd,selfr=pe.unpack('<6I',col)
   name=pe.string(td+16)
   if sig==1 and selfr==col and name:
    types.append(dict(vtable=t,col=hex(col),type_descriptor=hex(td),name=name,slots=[dict(slot=hex(i*8),target=hex(pe.unpack('<Q',tr+i*8)[0]-pe.base)) for i in range(0x190//8)]))
  except (ValueError,TypeError):pass
 out[hex(r)]=dict(rows=rows,types=types);print(hex(r),[(x['vtable'],x['name']) for x in types]);print('\n'.join(x['rva']+' '+x['text'] for x in rows[:40]))
(O/'effective-camera-types.json').write_text(json.dumps(out,indent=2))
