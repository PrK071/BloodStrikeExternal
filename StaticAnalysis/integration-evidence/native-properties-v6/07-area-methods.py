exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
from iced_x86 import Decoder
O=Path(__file__).parent;out=[]
for r in range(0x796b650,0x796bb50,32):
 v=pe.unpack('<4Q',r);out.append(dict(rva=hex(r),values=[hex(x) for x in v],name=pe.string(v[0]-pe.base) if pe.base<=v[0]<pe.base+pe.size else None))
(O/'area-method-table.json').write_text(json.dumps(out,indent=2))
r=0x130a140;n=0x30;off=pe.offset(r,n);rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];(O/'prop-accessor-contiguous.json').write_text(json.dumps(rows,indent=2));print('\n'.join(x['rva']+' '+x['text'] for x in rows))

