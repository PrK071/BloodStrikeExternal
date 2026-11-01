exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[];targets=[0x796f2f0]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',data,re.S):
  r=s['rva']+m.start();t=r+7+struct.unpack_from('<i',m.group(),3)[0]
  if t not in targets:continue
  f=pe.function(r)
  if not f:continue
  rows=[pe.row(i) for i in pe.decode(f[0])]
  if not any(x['rva']==hex(r) and x.get('rip_target_rva')==hex(t) for x in rows):continue
  out.append(dict(target=hex(t),function=hex(f[0]),rows=rows));print(hex(t),hex(f[0]));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:105]))
(O/'entity-type-binding-xrefs.json').write_text(json.dumps(out,indent=2))

