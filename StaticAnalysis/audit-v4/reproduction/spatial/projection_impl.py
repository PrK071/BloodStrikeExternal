exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'projection';rows={}
for r in [0x314c250]:
 rows[hex(r)]=[pe.row(i) for i in pe.decode(r)]
 for x in rows[hex(r)]:print(x['rva'],x['text'],x.get('rip_target_string') or '')
(out/'main-viewprojection-implementation.json').write_text(json.dumps(rows,indent=2))
