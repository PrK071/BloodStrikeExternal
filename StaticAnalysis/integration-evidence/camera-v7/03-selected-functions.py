exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x314e7f0,0x31ba8d0,0x940a80,0x940aa0,0x940ac0,0x275720,0x4fa600]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=dict(region=[hex(x) for x in pe.function(r)] if pe.function(r) else None,rows=rows)
 print('FN',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:160]))
(O/'selected-functions.json').write_text(json.dumps(out,indent=2))
