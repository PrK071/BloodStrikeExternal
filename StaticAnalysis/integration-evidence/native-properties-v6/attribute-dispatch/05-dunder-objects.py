exec((__import__('pathlib').Path(__file__).parent.parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
for name in [b'__getattr__',b'__getattribute__',b'__bool__',b'__len__']:
 p=0
 while (p:=pe.d.find(name+b'\0',p))>=0:
  start=p-40
  if start>=0:
   obj=pe.rva(start);head=pe.d[start:p];typ=struct.unpack_from('<Q',head,8)[0];length=struct.unpack_from('<q',head,16)[0];state=struct.unpack_from('<I',head,32)[0]
   if typ==pe.base+0x7a16e10 and length==len(name) and state&0x60==0x60:
    out.append(dict(name=name.decode(),rva=hex(obj),file_offset=hex(start),bytes=pe.d[start:p+len(name)+1].hex(' ')));print(name.decode(),hex(obj))
  p+=1
(O/'dunder-unicode-objects.json').write_text(json.dumps(out,indent=2))
