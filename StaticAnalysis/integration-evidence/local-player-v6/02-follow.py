exec((__import__('pathlib').Path(__file__).parent/'01-runtime-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent
out={}
for r in [0x2add0e0,0x2addac0,0x2abdb90,0x2abe0d0,0x2abdc90]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows
 print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:100]))
(O/'runtime-follow.json').write_text(json.dumps(out,indent=2))
