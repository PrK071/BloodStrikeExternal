exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
import struct
O=Path(__file__).parent;out=[];p=0
while (p:=pe.d.find(b'tuple\0',p))>=0:
 if p and pe.d[p-1]:p+=1;continue
 sr=pe.rva(p);q=0
 while (q:=pe.d.find(struct.pack('<Q',pe.base+sr),q))>=0:
  r=pe.rva(q);t=r-0x18
  if t>=0 and pe.offset(t,0x1b0) is not None:
   sz=pe.unpack('<Q',t+0x20)[0]
   if sz in [0x20,0x18,0x28]:
    vals=[dict(offset=hex(k),value=hex(pe.unpack('<Q',t+k)[0])) for k in range(0,0x1b0,8)];out.append(dict(type_rva=hex(t),name_rva=hex(sr),fields=vals));print(hex(t),hex(sz),'new',hex(pe.unpack('<Q',t+0x138)[0]-pe.base))
  q+=1
 p+=1
(O/'tuple-type-candidates.json').write_text(json.dumps(out,indent=2))

