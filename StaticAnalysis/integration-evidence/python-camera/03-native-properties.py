exec((__import__('pathlib').Path(__file__).parent/'02-native-names.py').read_text().split('res=[]')[0])
import struct
out=Path(__file__).parent;res=[]
for target in [0x55f6510,0x55fae18,0x55fc9d8,0x55eeb60,0x55f1548,0x56001e0]:
 p=0
 while (p:=pe.d.find(struct.pack('<Q',pe.base+target),p))>=0:
  rr=pe.rva(p);start=p-32;vals=struct.unpack_from('<16Q',pe.d,start);res.append({'target':pe.string(target),'pointer_rva':hex(rr),'block_rva':hex(pe.rva(start)),'bytes':pe.d[start:start+128].hex(' '),'qwords':[{'rva':hex(pe.rva(start+i*8)),'value':hex(v),'string':pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None} for i,v in enumerate(vals)]});p+=1
(out/'native-property-blocks.json').write_text(json.dumps(res,indent=2))
for x in res:
 print(x['target'],x['pointer_rva']);print([(v['rva'],v['string'] or v['value']) for v in x['qwords']])
