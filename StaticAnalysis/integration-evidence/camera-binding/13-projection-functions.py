exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x943d40,0x944a20,0x945e10,0x93be00,0x941240,0x93dd30,0x93df50,0x947740]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print('\n',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:65]))
(O/'projection-wrapper-functions.json').write_text(json.dumps(out,indent=2))

