exec((__import__('pathlib').Path(__file__).parent/'01-types.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x2a1d910]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:135]))
(O/'type-getattro-implementation.json').write_text(json.dumps(out,indent=2))

