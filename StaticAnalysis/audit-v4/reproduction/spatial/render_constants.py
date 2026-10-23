exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'render-source';res=[]
for r,n in [(0x4f0f400,64)]:
 o=pe.offset(r,n);res.append({'rva':hex(r),'file_offset':hex(o),'bytes':pe.d[o:o+n].hex(' '),'float32':list(struct.unpack_from('<16f',pe.d,o))})
(out/'initializer-constants.json').write_text(json.dumps(res,indent=2));print(res)
d=json.load(open(out/'candidate-functions.json'));near=[]
for f in ['0x1e547be','0x1e63bee','0x1e6a295']:
 rows=d[f];i=next(i for i,x in enumerate(rows) if '[rdi+0FA0h]' in x['text']);near.append({'function':f,'around':rows[max(0,i-5):i+10]});print(f,'\n'+'\n'.join(x['rva']+' '+x['text'] for x in rows[max(0,i-5):i+10]))
(out/'other-vector-writers.json').write_text(json.dumps(near,indent=2))
