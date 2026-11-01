exec((__import__('pathlib').Path(__file__).parent.parent/'01-names.py').read_text().split('O=')[0])
from iced_x86 import Decoder
O=Path(__file__).parent;r=0x2a0a1c0;n=0x600;off=pe.offset(r,n);rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];(O/'generic-contiguous.json').write_text(json.dumps(rows,indent=2));print('\n'.join(x['rva']+' '+x['text'] for x in rows if int(x['rva'],16)<0x2a0a610))

