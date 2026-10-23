exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'render-source';d=json.load(open(out/'candidate-functions.json'));sel={}
for f,center in [('0x789fe0',0x78a181),('0xc46cea',0xc47f9c),('0x1abd4a0',0x1abda17)]:
 rows=d[f];sel[f]=rows;print('\nFUNCTION',f)
 for x in rows:
  if abs(int(x['rva'],16)-center)<160 or int(x['rva'],16)<int(f,16)+60:print(x['rva'],x['text'])
refs=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']];p=0
 while (p:=b.find(b'\xe8',p))>=0:
  r=s['rva']+p
  if p+5<=len(b) and r+5+struct.unpack_from('<i',b,p+1)[0]==0x766370:
   f=pe.function(r)
   if f:
    rows=[pe.row(i) for i in pe.decode(f[0])];row=next((x for x in rows if int(x['rva'],16)==r),None)
    if row:refs.append({'function':hex(f[0]),'call':row});sel[hex(f[0])]=rows
  p+=1
(out/'selected-producer-consumer-functions.json').write_text(json.dumps(sel,indent=2));(out/'dispatcher-callers.json').write_text(json.dumps(refs,indent=2));print('CALLERS',json.dumps(refs))
