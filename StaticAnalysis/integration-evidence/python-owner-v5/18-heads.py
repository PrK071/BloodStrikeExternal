exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
import struct
O=Path(__file__).parent;out={'export_directory':pe.dirs[0],'objects':[]}
for r in [0x7a12990,0x7a129b0,0x7a16e10,0x7a19900,0x79a0060]:
 off=pe.offset(r,0x30);v=pe.unpack('<6Q',r);out['objects'].append(dict(rva=hex(r),file_offset=hex(off),bytes=pe.d[off:off+0x30].hex(' '),qwords=list(map(hex,v))));print(hex(r),list(map(hex,v)))
(O/'singletons-and-heads.json').write_text(json.dumps(out,indent=2))
