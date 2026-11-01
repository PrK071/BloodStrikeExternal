exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
O=Path(__file__).parent
rs=[]
for r in [0x4f45130,0x4f45138,0x80d5980]:
 try:b=pe.d[pe.offset(r,16):pe.offset(r,16)+16];vs=struct.unpack('<QQ',b);rs.append(dict(rva=hex(r),bytes=b.hex(' '),qwords=[hex(v) for v in vs]));print(rs[-1])
 except Exception as e:print(hex(r),str(e))
(O/'native-cells.json').write_text(json.dumps(rs,indent=2))
for r in [0x2d845b0]:
 rows=[pe.row(i) for i in pe.decode(r)];(O/('fn-'+hex(r)+'.json')).write_text(json.dumps(rows,indent=2));print('\n'.join(x['text'] for x in rows))
