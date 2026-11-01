exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;targets={0x80f3840};refs=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x48\x4c][\x8b\x8d\x89][\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',data,re.S):
  r=s['rva']+m.start();t=r+7+struct.unpack_from('<i',m.group(),3)[0]
  if t not in targets:continue
  f=pe.function(r)
  if not f:continue
  rows=[pe.row(i) for i in pe.decode(f[0])]
  if any(x['rva']==hex(r) and x.get('rip_target_rva')==hex(t) for x in rows):refs.append(dict(instruction=hex(r),region=[hex(x) for x in f],rows=rows));print(hex(f[0]),hex(r))
(O/'main-provider-root.json').write_text(json.dumps(dict(refs=refs),indent=2))
