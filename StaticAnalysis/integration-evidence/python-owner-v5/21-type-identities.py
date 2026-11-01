exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
for r in [0x7a19900,0x7a16e10,0x7a127f0]:
 out.append(dict(type_rva=hex(r),name=pe.string(pe.unpack('<Q',r+0x18)[0]-pe.base),name_rva=hex(pe.unpack('<Q',r+0x18)[0]-pe.base),basicsize=pe.unpack('<Q',r+0x20)[0],itemsize=pe.unpack('<Q',r+0x28)[0],flags=hex(pe.unpack('<Q',r+0xa8)[0])))
(O/'builtin-type-identities.json').write_text(json.dumps(out,indent=2));print(out)
