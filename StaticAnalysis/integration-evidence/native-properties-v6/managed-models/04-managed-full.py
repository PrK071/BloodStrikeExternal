exec((__import__('pathlib').Path(__file__).parent.parent/'01-names.py').read_text().split('O=')[0])
from iced_x86 import Decoder
O=Path(__file__).parent;out={}
for r,n in [(0x2a8adf0,0x100),(0x2a8cd70,0x90)]:
 off=pe.offset(r,n);rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];out[hex(r)]=rows;print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows))
(O/'managed-inline-contiguous.json').write_text(json.dumps(out,indent=2))
