exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x130a140,0x1439230,0x1439290,0x5ada10]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:65]))
(O/'prop-and-area-accessors.json').write_text(json.dumps(out,indent=2))
for s in [b'set_prop_desc',b'area_map',b'asiocore']:
 p=pe.d.find(s);print(s,p,hex(pe.rva(p)) if p>=0 else None,pe.d[p-30:p+len(s)+30] if p>=0 else None)
