exec((__import__('pathlib').Path(__file__).parent/'01-callers.py').read_text().split('res=[]')[0])
res=[];ptr=[]
for target in [0x222ed0,0xc46ca0]:
 p=0
 while (p:=pe.d.find(struct.pack('<Q',pe.base+target),p))>=0:
  ptr.append({'target':hex(target),'rva':hex(pe.rva(p)),'bytes':pe.d[p-16:p+32].hex(' ')});p+=1
 for s in pe.sections:
  if not s['flags']&0x20000000:continue
  b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
  for opcode in [b'\xe8',b'\xe9']:
   p=0
   while (p:=b.find(opcode,p))>=0:
    r=s['rva']+p
    if p+5<=len(b) and r+5+struct.unpack_from('<i',b,p+1)[0]==target:
     f=pe.function(r)
     if f:
      rr=rows(f[0]);i=next((i for i,x in enumerate(rr) if int(x['rva'],16)==r),None)
      if i is not None:res.append({'target':hex(target),'function':hex(f[0]),'around':rr[max(0,i-20):i+8]})
    p+=1
save('entry-overlap-callers.json',res);save('entry-function-pointers.json',ptr);save('entry-overlap-functions.json',{hex(k):v for k,v in cache.items()});print(json.dumps(res));print('PTR',json.dumps(ptr))
