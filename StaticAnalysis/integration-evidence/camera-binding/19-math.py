exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
for r in [0x4e589c0,0x4e4eea0,0x4e58970,0x4e58978,0x4e58988,0x4e5899c,0x4e5897c]:
 b=pe.d[pe.offset(r,4):pe.offset(r,4)+4];out.append(dict(rva=hex(r),bytes=b.hex(),float=struct.unpack('<f',b)[0]))
for r in [0x426b930,0x426b1c0]:
 rows=[pe.row(i) for i in pe.decode(r,64)];out.append(dict(rva=hex(r),instructions=rows[:12]))
(O/'screenpoint-math.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
