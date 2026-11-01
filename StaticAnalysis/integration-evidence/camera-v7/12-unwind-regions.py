exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent
def primary(f):
 seen=set()
 while f[2] not in seen:
  seen.add(f[2]);head=pe.unpack('<4B',f[2]);flags=head[0]>>3
  if not flags&4:return f
  chain=f[2]+((4+head[2]*2+3)&~3);f=pe.unpack('<III',chain)
 raise ValueError('unwind chain cycle')
targets=[0xdb7ac0,0xb82080,0xc46ca0,0x343ef0,0xdb8c90]
groups={primary(pe.function(r))[0]:dict(request=hex(r),primary=[hex(v) for v in primary(pe.function(r))],regions=[]) for r in targets}
for f in pe.functions:
 p=primary(f)
 if p[0] not in groups:continue
 groups[p[0]]['regions'].append(dict(range=[hex(v) for v in f],rows=[pe.row(i) for i in pe.decode(f[0])]))
(O/'unwind-groups.json').write_text(json.dumps(groups,indent=2))
for p,g in groups.items():print(g['request'],g['primary'],[r['range'] for r in g['regions']])
