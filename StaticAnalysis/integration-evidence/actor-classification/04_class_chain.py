import json
D=json.load(open(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\integration-evidence\python-format\selected-models-static.json'))
for m in D:
 if m['index']==143510:
  print(m.keys())
  for c in m['codes']:
   if c['qualname'] in ['<module>','AvatarModel']:
    print(c['qualname'],c['names'],c['consts'])
    print([(i['offset'],i['opname'],i.get('arg'),i.get('name'),i.get('const')) for i in c['instructions'][:50]])
