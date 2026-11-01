exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent
seeds=json.loads((O/'seeds.json').read_text());targets={int(x['rva'],16) for x in seeds['names'] if x['text'] in ['GetMainCameraViewProjection','GetMainViewportPresentSequence','MainCameraName','IWorld.MainCameraName','cIsMainViewport','AddAffiliatedViewport']}
refs=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',data,re.S):
  r=s['rva']+m.start();t=r+7+struct.unpack_from('<i',m.group(),3)[0]
  if t not in targets:continue
  f=pe.function(r)
  if not f:continue
  rows=[pe.row(i) for i in pe.decode(f[0])]
  if any(x['rva']==hex(r) and x.get('rip_target_rva')==hex(t) for x in rows):refs.append(dict(target=hex(t),instruction=hex(r),region=[hex(x) for x in f],rows=rows));print('ref',hex(t),hex(f[0]),hex(r))
functions={}
for r in [0xa8a270,0xa8a440,0xa89630,0xa899e0,0xd09e50,0x1d21bf0]:
 rows=[pe.row(i) for i in pe.decode(r)];functions[hex(r)]=rows
 print('fn',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:110]))
blocks=[]
for r in sorted(pe.relocations):
 v=pe.unpack('<Q',r)[0]-pe.base
 if v in targets:blocks.append(dict(pointer_rva=hex(r),target=hex(v),qwords=[hex(v) for v in pe.unpack('<20Q',r-64)]))
(O/'selector-follow.json').write_text(json.dumps(dict(refs=refs,functions=functions,blocks=blocks),indent=2))
