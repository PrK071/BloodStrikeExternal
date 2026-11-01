exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x1554880,0x15527f0]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:145]))
for r in [0x796a420,0x796c240]:
 out[hex(r)]=dict(head=[hex(v) for v in pe.unpack('<6Q',r)])
(O/'mixed-value-dispatch.json').write_text(json.dumps(out,indent=2))

