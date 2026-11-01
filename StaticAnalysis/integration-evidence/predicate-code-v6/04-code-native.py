exec((__import__('pathlib').Path(__file__).parent/'01-types.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
from audit_v2 import Decoder
for r,n in [(0x2b20c30,0x12d),(0x2babf10,0xc9)]:
 off=pe.offset(r,n)
 rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];out[hex(r)]=rows
 print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:180]))
(O/'native-code-bytes.json').write_text(json.dumps(out,indent=2))
