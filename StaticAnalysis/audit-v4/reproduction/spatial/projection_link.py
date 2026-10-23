exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'projection';rows={}
for r in [0x314e7f0,0x3150100,0x1abd000,0x750070]:
 rows[hex(r)]=[pe.row(i) for i in pe.decode(r)]
 print('\nFUNCTION',hex(r))
 for x in rows[hex(r)]:print(x['rva'],x['text'],x.get('rip_target_string') or '')
(out/'linked-functions.json').write_text(json.dumps(rows,indent=2))
