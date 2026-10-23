exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'projection';table=[];code={}
for slot in [0,0x68,0x90,0xc0,0xc8,0xd0,0x128]:
 v=pe.unpack('<Q',0x4ebf848+slot)[0];r=v-pe.base;table.append({'slot':hex(slot),'rva':hex(0x4ebf848+slot),'pointer_bytes':struct.pack('<Q',v).hex(' '),'target':hex(r)});code[hex(r)]=[pe.row(i) for i in pe.decode(r)]
 print('SLOT',hex(slot),'TARGET',hex(r))
 for x in code[hex(r)]:
  if slot in [0x90,0x128]:print(x['rva'],x['text'])
(out/'temporary-vtable.json').write_text(json.dumps(table,indent=2));(out/'temporary-vtable-functions.json').write_text(json.dumps(code,indent=2))
