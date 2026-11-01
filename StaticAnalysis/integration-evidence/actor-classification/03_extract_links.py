import json
p=r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\integration-evidence\actor-classification\resource-code-static.json';D=json.load(open(p))
for m in D['modules']:
 for c in m['codes']:
  if c['qualname'] in ['PoseSenderModel.ApplyMotion']:
   print('POSE',[(x['offset'],x['opname'],x.get('resolved_name'),x.get('const')) for x in c['instructions']])
mods=json.load(open(r'C:\Users\luiz\Documents\BloodStrikeExternal\Documents\dummy')) if False else None
L=json.load(open(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\integration-evidence\gameplay\python-model-links\model-link-static.json'))
for r in L['records']:
 if r['qualname'] in ['SimpleModel.ReloadSkeleton','AvatarModel.Load']:
  print('\n',r['qualname'])
  # list all windows as quick selective evidence
  for w in r['actor_parent_component_windows']:
   if w['anchor_offset'] in ([0,50,118,380,442] if r['qualname']=='SimpleModel.ReloadSkeleton' else [670,830,886,1146,1348]): print(w['anchor_offset'],w['window'])
