exec((__import__('pathlib').Path(__file__).parent/'01-types.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
name=b'__getattribute__';p=0
while (p:=pe.d.find(name+b'\0',p))>=0:
 r=pe.rva(p);q=0
 while (q:=pe.d.find(struct.pack('<Q',pe.base+r),q))>=0:
  ref=pe.rva(q)
  if pe.offset(ref,0x38) is not None:
   v=pe.unpack('<7Q',ref)
   if v[1]&0xffffffff==0x90:
    row=dict(record_rva=hex(ref),name_rva=hex(r),qwords=[hex(x) for x in v],bytes=pe.d[q:q+0x38].hex(' '));out.append(row);print(row)
  q+=1
 p+=1
(O/'getattribute-wrapperbase.json').write_text(json.dumps(out,indent=2))
