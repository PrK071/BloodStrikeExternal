exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
import struct,re
O=Path(__file__).parent;refs=[];p=0
while (p:=pe.d.find(struct.pack('<Q',pe.base+0x70124a0),p))>=0:
 refs.append(pe.rva(p)+8);p+=1
print('vtables',list(map(hex,refs)));out=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',data,re.S):
  r=s['rva']+m.start();t=r+7+struct.unpack_from('<i',m.group(),3)[0]
  if t not in refs:continue
  f=pe.function(r)
  if not f:continue
  ins=next((i for i in pe.decode(f[0]) if i.ip-pe.base==r),None)
  if ins and ins.is_ip_rel_memory_operand and ins.ip_rel_memory_address-pe.base==t:
   rows=[pe.row(i) for i in pe.decode(f[0])];out.append(dict(vtable=hex(t),function=hex(f[0]),rows=rows));print('factory candidate',hex(f[0]));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:90]))
(O/'entity-vtable-xrefs.json').write_text(json.dumps(out,indent=2))
