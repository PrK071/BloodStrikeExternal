exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
rows={}
for r in [0x95e880,0x964090,0x3efbc0,0x3efb70]:
 rows[hex(r)]=[pe.row(i) for i in pe.decode(r)]
 print('\nFUNCTION',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[hex(r)]))
(out/'getters-instructions.json').write_text(json.dumps(rows,indent=2))
for m in __import__('re').finditer(rb'[ -~]{5,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if ('Project' in s or 'CameraMatrix' in s) and ('Camera' in s or s in ['Project','ProjectInner']):print(hex(pe.rva(m.start())),s[:300])
