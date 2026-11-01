exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
for r in range(0x796f2c8,0x796f350,8):
 v=pe.unpack('<Q',r)[0];out.append(dict(rva=hex(r),value=hex(v),string=pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None))
print(json.dumps(out,indent=2));(O/'entity-area-getset-block.json').write_text(json.dumps(out,indent=2))
