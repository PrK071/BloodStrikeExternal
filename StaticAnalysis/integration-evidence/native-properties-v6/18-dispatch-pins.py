exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
from iced_x86 import Decoder
O=Path(__file__).parent;out={}
for r,n in [(0x1540440,0x40),(0x1554880,0xe9)]:
 off=pe.offset(r,n);rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];out[hex(r)]=rows
out['type_dispatch_table_1540480']=[hex(v) for v in pe.unpack('<6I',0x1540480)]
out['mixed_value_dispatch_table_155496c']=[hex(v) for v in pe.unpack('<6I',0x155496c)]
# Pin type storage and relevant initializer linking records, plus RTTI getter slots.
out['pins']={}
for r,n in [(0x796a420,0x30),(0x796c240,0x30),(0x796ba50,0x40),(0x555ba58,0xe0),(0x555bb50,0xe0),(0x555bd40,0xe0)]:
 off=pe.offset(r,n);out['pins'][hex(r)]={'file_offset':hex(off),'bytes':pe.d[off:off+n].hex(' ')}
(O/'numeric-dispatch-and-pins.json').write_text(json.dumps(out,indent=2));print(out['type_dispatch_table_1540480']);print(out['mixed_value_dispatch_table_155496c']);print('\n'.join(x['rva']+' '+x['text'] for x in out['0x1540440']))
