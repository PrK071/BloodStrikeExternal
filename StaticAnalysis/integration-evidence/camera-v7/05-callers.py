exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;targets={0xa899e0,0xa89630,0xa8a270,0x1991160,0x5f5890,0xdb8c90};refs=[];functions={}
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(b'[\xe8\xe9]',data):
  p=m.start();r=s['rva']+p
  if p+5>len(data):continue
  t=r+5+struct.unpack_from('<i',data,p+1)[0]
  if t not in targets:continue
  f=pe.function(r)
  if not f:continue
  if f[0] not in functions:functions[f[0]]=[pe.row(i) for i in pe.decode(f[0])]
  rows=functions[f[0]]
  if any(x['rva']==hex(r) and x.get('branch_target_rva')==hex(t) for x in rows):refs.append(dict(target=hex(t),instruction=hex(r),region=[hex(x) for x in f]));print(hex(t),hex(r),hex(f[0]))
functions={hex(k):v for k,v in functions.items() if any(int(x['region'][0],16)==k for x in refs)}
(O/'direct-callers.json').write_text(json.dumps(dict(refs=refs,functions=functions),indent=2))
seeds=json.loads((O/'seeds.json').read_text());out={}
for fn in [0x2a58d0,0x2b21e0,0x2f1680,0x5f9e80,0x5fab00,0x5f5890]:
 rows=[pe.row(i) for i in pe.decode(fn)];out[hex(fn)]=rows;print('FN',hex(fn));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:100]))
(O/'render-candidate-functions.json').write_text(json.dumps(out,indent=2))
