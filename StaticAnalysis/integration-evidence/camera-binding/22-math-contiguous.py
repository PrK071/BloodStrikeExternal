exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
from audit_v2 import Decoder
O=Path(__file__).parent;out={}
for r,n in [(0x42952f0,0xe0),(0x426b930,0x380)]:
 off=pe.offset(r,n);rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];out[hex(r)]=rows
 print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows) if r==0x42952f0 else 'saved '+str(len(rows)))
(O/'math-contiguous.json').write_text(json.dumps(out,indent=2))
