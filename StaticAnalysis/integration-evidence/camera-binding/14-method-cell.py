exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
for r in [0x4f4f900,0x4f4fe88,0x4f4b568,0x4f4c860,0x4f4d8f8]:
 bs=pe.d[pe.offset(r,160):pe.offset(r,160)+160];vs=struct.unpack('<20Q',bs);row=dict(rva=hex(r),bytes=bs.hex(' '),qwords=[dict(rva=hex(r+i*8),value=hex(v),string=pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None) for i,v in enumerate(vs)]);out.append(row);print(row)
(O/'projection-member-cells.json').write_text(json.dumps(out,indent=2))
