exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
for f in pe.functions:
 if not 0xb80000<=f[0]<0xb90000:continue
 rows=[pe.row(i) for i in pe.decode(f[0])]
 for i,x in enumerate(rows):
  if not re.search(r'mov (r\w+),\[r\w+\+40h\]',x['text']):continue
  register=x['text'].split()[1].split(',')[0]
  following=[z for z in rows[i+1:i+12] if f'[{register}+50h]' in z['text']]
  if following:out.append(dict(region=[hex(v) for v in f],first=x,following=following,rows=rows));print(hex(f[0]),x['text'],[z['text'] for z in following])
(O/'pipeline-camera-uses.json').write_text(json.dumps(out,indent=2))
