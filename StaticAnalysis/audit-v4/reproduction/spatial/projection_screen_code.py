exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'projection';rows={}
for r in [0x955350,0x9553f0,0x955e40]:
 rows[hex(r)]=[pe.row(i) for i in pe.decode(r)]
 print('\nFUNCTION',hex(r))
 for x in rows[hex(r)]:print(x['rva'],x['text'])
(out/'screen-getter-wrappers.json').write_text(json.dumps(rows,indent=2))
