exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x12f94a0,0x12f95f0,0x12f9520,0x12f9540,0x12f93d0,0x130a220,0x12f7b40,0x12f9510]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:75]))
for r in [0x796a420,0x796c240]:
 out[hex(r)]=dict(head=[hex(v) for v in pe.unpack('<6Q',r)])
(O/'area-map-slots.json').write_text(json.dumps(out,indent=2))
