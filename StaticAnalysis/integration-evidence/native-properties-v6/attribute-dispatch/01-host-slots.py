exec((__import__('pathlib').Path(__file__).parent.parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x1439f30,0x143a080,0x2a09600,0x12f94a0]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:160]))
(O/'host-and-truth-slots.json').write_text(json.dumps(out,indent=2))
