exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
from iced_x86 import Decoder
O=Path(__file__).parent;r=0x12c37c0;n=0x200;off=pe.offset(r,n);rows=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)];(O/'prop-index-helper-contiguous.json').write_text(json.dumps(rows,indent=2));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:145]))
