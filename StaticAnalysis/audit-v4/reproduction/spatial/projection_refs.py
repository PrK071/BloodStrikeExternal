exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'projection'
results=[]
for r in [0x5ba6f28,0x55aef10]:
 refs=[];p=0;pat=struct.pack('<Q',pe.base+r)
 while (p:=pe.d.find(pat,p))>=0:
  rr=pe.rva(p);refs.append({'rva':hex(rr),'file_offset':hex(p),'bytes':pe.d[p-32:p+96].hex(' '),'qwords':[{'rva':hex(pe.rva(p-32+i*8)),'value':hex(v),'string':pe.string(v-pe.base) if pe.base<=v<pe.base+pe.size else None} for i,v in enumerate(struct.unpack_from('<16Q',pe.d,p-32))]});p+=1
 results.append({'string':pe.string(r),'rva':hex(r),'data_refs':refs})
(out/'string-data-refs.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
