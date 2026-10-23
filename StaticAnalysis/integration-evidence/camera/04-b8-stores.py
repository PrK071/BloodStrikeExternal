exec((__import__('pathlib').Path(__file__).parent/'01-callers.py').read_text().split('res=[]')[0])
res=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 b=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x48\x49\x4c\x4d]\x89[\x80-\xbf]\xb8\x00\x00\x00',b):
  r=s['rva']+m.start();f=pe.function(r)
  if not f:continue
  rr=rows(f[0]);i=next((i for i,x in enumerate(rr) if int(x['rva'],16)==r),None)
  if i is not None and '0B8h]' in rr[i]['text']:
   res.append({'function':hex(f[0]),'store':rr[i],'around':rr[max(0,i-10):i+5]})
save('b8-pointer-stores.json',res)
print('TOTAL',len(res))
for x in res:
 around=' '.join(z['text'] for z in x['around'])
 if any(t in around for t in ['+30h]','+8]','+0DC0h]','+0DD0h]']):print(x['function'],x['store']['rva'],'\n'+'\n'.join(z['rva']+' '+z['text'] for z in x['around']))
