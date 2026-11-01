exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x275db0]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print('\n',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:65]))
(O/'screenpoint-helper.json').write_text(json.dumps(out,indent=2))

