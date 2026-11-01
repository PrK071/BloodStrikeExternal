from pathlib import Path
import json
O=Path(__file__).parent
j=json.loads((O/'binding-modules-static.json').read_text()); pick={'Camera.__init__','Camera.CreateController','Camera.InitController','Camera.Attach','Camera.engine_camera','Camera.position','Camera.ConfigAimPlacer','Camera.LoadFromData','Camera.SetPlacer','ClientEnv.InitHudCamera','ClientEnv.AddModelAppearCamera'}
r=[dict(index=x['index'],decoded_sha256=x['decoded_sha256'],codes=[c for c in x['codes'] if c['qualname'] in pick]) for x in j];r=[x for x in r if x['codes']]
(O/'binding-selected.json').write_text(json.dumps(r,indent=2))
v=[]
for m in j:
 errors=[]
 for c in m['codes']:
  bounds={x['offset'] for x in c['instructions']}
  for x in c['instructions']:
   if 'target' in x and x['target'] not in bounds:errors.append([c['qualname'],x['offset'],x['target']])
 v.append(dict(index=m['index'],codes=len(m['codes']),jump_errors=errors))
(O/'binding-validation.json').write_text(json.dumps(v,indent=2));print(v)
