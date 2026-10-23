exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'render-source';res=[];p=0
while (p:=pe.d.find(struct.pack('<Q',pe.base+0x766370),p))>=0:
 res.append({'kind':'qword','rva':hex(pe.rva(p)),'around_bytes':pe.d[p-16:p+32].hex(' ')});p+=1
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']];p=0
 while (p:=b.find(b'\xe9',p))>=0:
  r=s['rva']+p
  if p+5<=len(b) and r+5+struct.unpack_from('<i',b,p+1)[0]==0x766370:res.append({'kind':'E9-candidate','rva':hex(r)})
  p+=1
(out/'dispatcher-indirect-address-candidates.json').write_text(json.dumps(res,indent=2));print(res)
d=json.load(open(out/'candidate-functions.json'))
for f in ['0x789fe0','0xc46cea']:
 rows=d[f];print('FN',f,'TAIL');print('\n'.join(x['rva']+' '+x['text'] for x in rows[-15:]))
