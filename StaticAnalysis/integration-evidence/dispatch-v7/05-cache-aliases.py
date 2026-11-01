exec((__import__('pathlib').Path(__file__).parent/'01-types.py').read_text().split('O=')[0])
from iced_x86 import Decoder
O=Path(__file__).parent;r=0x1439290;n=0x140;off=pe.offset(r,n);rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];(O/'entity-area-setter-contiguous.json').write_text(json.dumps(rows,indent=2));print('\n'.join(x['rva']+' '+x['text'] for x in rows))
