exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'projection';e={'rtti':{},'slots':[],'code':{}}
col=pe.unpack('<Q',0x4ebf840)[0]-pe.base;td=pe.unpack('<I',col+12)[0]
for r,n in [(0x4ebf840,16),(col,24),(td,64)]:e['rtti'][hex(r)]={'file_offset':hex(pe.offset(r,n)),'bytes':pe.d[pe.offset(r,n):pe.offset(r,n)+n].hex(' ')}
e['rtti']['name']=pe.string(td+16)
for slot in [0x28,0x70,0x208]:
 rr=0x4ebf848+slot;v=pe.unpack('<Q',rr)[0];r=v-pe.base;e['slots'].append({'slot':hex(slot),'rva':hex(rr),'bytes':struct.pack('<Q',v).hex(' '),'target':hex(r)});e['code'][hex(r)]=[pe.row(i) for i in pe.decode(r)]
(out/'perspective-rtti-and-slots.json').write_text(json.dumps(e,indent=2))
# Inventory exact viewport/projection-related qualified names: informational only.
import re
names=[]
for m in re.finditer(rb'[ -~]{4,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if len(s)<120 and (('Viewport' in s or 'ViewPort' in s or 'ScreenSize' in s or 'Resolution' in s or 'Projection' in s) and (s.startswith('ICamera') or s.startswith('Messiah.ICamera') or 'viewport' in s.lower())):names.append({'rva':hex(pe.rva(m.start())),'string':s})
(out/'viewport-name-inventory.json').write_text(json.dumps(names,indent=2));print(json.dumps(names[:25],indent=2))
