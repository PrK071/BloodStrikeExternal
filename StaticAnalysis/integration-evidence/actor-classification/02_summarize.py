import json
p=r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\integration-evidence\actor-classification\resource-code-static.json'
d=json.load(open(p))
for m in d['modules']:
 print('\nMODULE',m['index'],m['codes'][0]['filename'])
 for c in m['codes']:
  names=c['names']; terms=['ActorComponent','Parent','PoseSenderModel','BaseModel','AvatarModel','IsATMGuardAI','IsPlayerCombatAvatar','CreateObject','CreateModel','AttachToParent','super','GetComponent','GetOwner','Player','NPC','weapon','WeaponModel']
  hits=[]
  for i,x in enumerate(c['instructions']):
   if x.get('resolved_name') in terms or (x.get('opname')=='LOAD_CONST' and isinstance(x.get('const'),str) and any(t.lower() in x['const'].lower() for t in terms)):
    a=max(0,i-4);b=min(len(c['instructions']),i+5)
    hits.append({'at':x['offset'],'hit':x.get('resolved_name',x.get('const')),'ctx':[(y['offset'],y['opname'],y.get('resolved_name'),y.get('const')) for y in c['instructions'][a:b]]})
  if hits or c['qualname'].endswith('.__init__') or c['qualname'].endswith('.Load'):
   print(json.dumps({'fn':c['qualname'],'line':c['firstlineno'],'hits':hits},ensure_ascii=False))
