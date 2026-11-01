exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
import struct,re
O=Path(__file__).parent;out=[]
for r in [0x7a07d30]:
 for k in range(0,0x1b0,8):
  v=pe.unpack('<Q',r+k)[0];out.append(dict(offset=hex(k),rva=hex(r+k),value=hex(v),string=pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None))
print(json.dumps(out,indent=2));(O/'actor-static-type.json').write_text(json.dumps(out,indent=2))
# exact strings only, no whole program scan
out=[]
for name in [b'IEntity',b'Messiah.IEntity',b'PyIEntity']:
 p=0
 while (p:=pe.d.find(name+b'\0',p))>=0:
  if p==0 or pe.d[p-1]==0:
   r=pe.rva(p);refs=[];q=0
   while (q:=pe.d.find(struct.pack('<Q',pe.base+r),q))>=0:
    refs.append(hex(pe.rva(q)));q+=1
   out.append(dict(name=name.decode(),rva=hex(r),qword_refs=refs))
  p+=1
(O/'entity-type-names.json').write_text(json.dumps(out,indent=2));print(out)
