exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
from iced_x86 import Decoder
O=Path(__file__).parent;out={}
for r,n in [(0x2059800,0x18b),(0x79a0060,0x30),(0x57859a8,0x28)]:
 off=pe.offset(r,n)
 if n>0x30:
  rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];out[hex(r)]=rows;print('\n'.join(x['rva']+' '+x['text'] for x in rows))
 else:out[hex(r)]={'bytes':pe.d[off:off+n].hex(' ')}
(O/'entity-ready-contiguous.json').write_text(json.dumps(out,indent=2))
