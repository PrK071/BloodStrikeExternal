exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'render-source';res=[];funcs={}
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']];p=0
 while (p:=b.find(b'\xe8',p))>=0:
  r=s['rva']+p
  if p+5<=len(b) and r+5+struct.unpack_from('<i',b,p+1)[0]==0x789fe0:
   f=pe.function(r)
   if f:
    rows=[pe.row(i) for i in pe.decode(f[0])];i=next((i for i,x in enumerate(rows) if int(x['rva'],16)==r),None)
    if i is not None:res.append({'function':hex(f[0]),'around':rows[max(0,i-12):i+13]});funcs[hex(f[0])]=rows
  p+=1
(out/'initializer-callers.json').write_text(json.dumps(res,indent=2));(out/'initializer-caller-functions.json').write_text(json.dumps(funcs,indent=2))
for x in res:
 print('\nFN',x['function']);print('\n'.join(r['rva']+' '+r['text'] for r in x['around']))
