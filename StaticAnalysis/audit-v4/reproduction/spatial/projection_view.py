import json
p=r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\audit-v4\spatial\projection\ref-functions.json'
d=json.load(open(p))
for f,rows in d.items():
 print('\nFUNCTION',f)
 for n,x in enumerate(rows):
  r=int(x['rva'],16)
  if (0x1a8c3c0<=r<=0x1a8c4b0) or (0x314d8b0<=r<=0x314d9d0):print(x['rva'],x['bytes'],x['text'],x.get('rip_target_string') or '')
