exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
from audit_v2 import Decoder
O=Path(__file__).parent;out={}
for r,n in [(0xdb73e0,0x12),(0xdb74f0,0x90),(0x2da2f0,0x11),(0x293eb0,0x19),(0x275320,0x80)]:
 off=pe.offset(r,n);rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];out[hex(r)]=rows
 print('FN',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows))
(O/'camera-accessors.json').write_text(json.dumps(out,indent=2))
