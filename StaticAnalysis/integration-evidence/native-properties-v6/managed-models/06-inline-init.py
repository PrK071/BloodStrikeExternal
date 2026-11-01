exec((__import__('pathlib').Path(__file__).parent.parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x2ab59f0,0x2a93560]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:130]))
(O/'inline-initializer-and-materialize.json').write_text(json.dumps(out,indent=2))

