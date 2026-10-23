exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'projection';res=[]
for r in [0x4f584a0,0x4f5ea18]:
 p=0
 while (p:=pe.d.find(struct.pack('<Q',pe.base+r),p))>=0:
  rr=pe.rva(p);vs=struct.unpack_from('<16Q',pe.d,p-32);item={'string':pe.string(r),'pointer_rva':hex(rr),'block_rva':hex(pe.rva(p-32)),'bytes':pe.d[p-32:p+96].hex(' '),'qwords':[]}
  for j,v in enumerate(vs):item['qwords'].append({'rva':hex(pe.rva(p-32+j*8)),'value':hex(v),'string':pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None})
  res.append(item);p+=1
(out/'screen-method-data.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
