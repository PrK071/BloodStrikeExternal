exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x5a2790]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:140]))
for r in [0x796a420,0x796c240]:
 out[hex(r)]=dict(head=[hex(v) for v in pe.unpack('<6Q',r)])
(O/'set-prop-index-callback.json').write_text(json.dumps(out,indent=2))

