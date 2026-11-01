exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
for vt in [0x555ba60,0x555bb58,0x555bc50]:
 col=pe.unpack('<Q',vt-8)[0]-pe.base;td=pe.unpack('<I',col+12)[0];name=pe.string(td+16);fn=pe.unpack('<Q',vt+0xc8)[0]-pe.base
 rows=[pe.row(i) for i in pe.decode(fn)];out.append(dict(vtable_rva=hex(vt),col_rva=hex(col),type_descriptor=hex(td),name=name,getter_slot_c8=hex(fn),rows=rows));print(hex(vt),name,hex(fn));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:80]))
(O/'typed-storage-getters.json').write_text(json.dumps(out,indent=2))
