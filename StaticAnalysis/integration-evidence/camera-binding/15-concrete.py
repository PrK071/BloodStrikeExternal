exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x964160,0x964240,0x9642e0,0x93dde0,0x96e400,0x2631f0,0x485230]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print('\n',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:65]))
(O/'projection-concrete-functions.json').write_text(json.dumps(out,indent=2))

