exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'render-source';refs=[];funcs={}
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for opcode in [b'\xe8',b'\xe9']:
  p=0
  while (p:=b.find(opcode,p))>=0:
   r=s['rva']+p
   if p+5<=len(b) and r+5+struct.unpack_from('<i',b,p+1)[0]==0x7dac30:
    f=pe.function(r)
    if f:
     rows=[pe.row(i) for i in pe.decode(f[0])];row=next((x for x in rows if int(x['rva'],16)==r),None)
     if row:refs.append({'function':hex(f[0]),'call':row});funcs[hex(f[0])]=rows
   p+=1
(out/'tailcaller-callers.json').write_text(json.dumps(refs,indent=2));(out/'tailcaller-caller-functions.json').write_text(json.dumps(funcs,indent=2));print(json.dumps(refs))
