exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
rs=[(0x4f60590,0xa0),(0x4f601c0,16),(0x4f43b10,0xa0),(0x4f45130,16),(0x4f50350,0x48),(0x4f76d00,0x48)]
data=[]
for r,n in rs:
 o=pe.offset(r,n);data.append({'rva':hex(r),'file_offset':hex(o),'bytes':pe.d[o:o+n].hex(' '),'qwords':[{'rva':hex(r+i),'value':hex(v[0]),'target_rva':hex(v[0]-pe.base) if pe.base<=v[0]<pe.base+pe.size else None,'string':pe.string(v[0]-pe.base) if pe.base<=v[0]<pe.base+pe.size else None} for i,v in zip(range(0,n,8),struct.iter_unpack('<Q',pe.d[o:o+n]))]})
(out/'data-blocks.json').write_text(json.dumps(data,indent=2))
code={hex(r):[pe.row(i) for i in pe.decode(r)] for r in [0x954ad0,0x93f1a0,0x95e880,0x964090]}
(out/'selected-code.json').write_text(json.dumps(code,indent=2))
# Direct-call candidates validated by disassembling their containing unwind function.
refs=[]
for target in [0x95e880,0x964090]:
 for s in pe.sections:
  if not s['flags']&0x20000000:continue
  blob=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']];p=0
  while (p:=blob.find(b'\xe8',p))>=0:
   r=s['rva']+p
   if p+5<=len(blob) and r+5+struct.unpack_from('<i',blob,p+1)[0]==target:
    f=pe.function(r)
    if f:
     ins=next((i for i in pe.decode(f[0]) if i.ip-pe.base==r),None)
     if ins and ins.len==5:refs.append({'target':hex(target),'function':hex(f[0]),'instruction':pe.row(ins)})
   p+=1
(out/'direct-calls.json').write_text(json.dumps(refs,indent=2))
print(json.dumps(refs,indent=2))
