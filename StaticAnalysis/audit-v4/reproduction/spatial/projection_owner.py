exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
rows=json.load(open(out/'projection'/'ref-functions.json'))['0x314d4c0']
for x in rows[:65]:print(x['rva'],x['text'],x.get('rip_target_string') or '')
col=pe.unpack('<Q',0x4ebf848-8)[0]-pe.base;print('COL',hex(col),pe.unpack('<6I',col));td=pe.unpack('<I',col+12)[0];print('TYPE',hex(td),pe.string(td+16))
for slot in [0x28,0x70,0x208]:
 r=pe.unpack('<Q',0x4ebf848+slot)[0]-pe.base;print('SLOT',hex(slot),hex(r))
 for i in pe.decode(r):
  row=pe.row(i)
  if slot!=0x208:print(row['rva'],row['text'])
