exec((__import__('pathlib').Path(__file__).parent/'01-types.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for t,off in [(0x7a15170,0x90),(0x7a135a0,0x110)]:
 ptr=pe.unpack('<Q',t+off)[0];r=ptr-pe.base;rows=[pe.row(i) for i in pe.decode(r)];out[hex(t)]={'slot_offset':hex(off),'slot_rva':hex(t+off),'slot_bytes':pe.d[pe.offset(t+off,8):pe.offset(t+off,8)+8].hex(' '),'function_rva':hex(r),'rows':rows};print(hex(t),hex(off),hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:60]))
(O/'type-getattro-and-function-get.json').write_text(json.dumps(out,indent=2))
