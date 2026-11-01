exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x796a370,0x796a390]:
 v=pe.unpack('<5Q',r);out[hex(r)]=[hex(x) for x in v];print(hex(r),out[hex(r)])
for r in [0x12f9d30,0x2a094d0,0x154f220]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:90]))
(O/'map-mapping-and-descriptor.json').write_text(json.dumps(out,indent=2))
