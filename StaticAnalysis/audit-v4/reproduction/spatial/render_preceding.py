exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'render-source';idx=pe.starts.index(0xc46cea);fs=pe.functions[idx-2:idx+1];res={}
for f in fs:
 rows=[pe.row(i) for i in pe.decode(f[0])];res[hex(f[0])]=rows
 print('FN',hex(f[0]),hex(f[1]));print('\n'.join(x['rva']+' '+x['text'] for x in rows[-25:]))
rows=json.load(open(out/'candidate-functions.json'))['0xc46cea']
print('FOLLOWING ORIGIN')
for x in rows[:95]:print(x['rva'],x['text'])
(out/'producer-preceding-unwind.json').write_text(json.dumps(res,indent=2))
