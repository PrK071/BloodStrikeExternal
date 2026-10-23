import json,hashlib
from pathlib import Path
OUT=Path(__file__).parent;rs=json.loads((OUT/'camera-modules-static.json').read_text());validation=[];extract=[]
wanted={'BasePlacer.__init__','BasePlacer.target','BasePlacer.GetAllPlacerTypes','EnginePlacer.IsValid','EnginePlacer.SetFocusTarget','EnginePlacer.RefreshConfig','EnginePlacer.CreateBlender','EnginePlacer.OnDeactive','EnginePlacer.BlenderInFinished','AimPlacer.__init__','AimPlacer.OnActive','AimPlacer.SetFocusTarget','AimPlacer.TurnView'}
for r in rs:
 for c in r['codes']:
  offsets={x['offset'] for x in c['instructions']};bad=[x for x in c['instructions'] if 'target' in x and x['target'] not in offsets]
  validation.append({'index':r['index'],'name':c['qualname'],'branch_targets_on_instruction_boundaries':not bad,'bad':bad})
  if c['qualname'] in wanted:extract.append({'index':r['index'],'qualname':c['qualname'],'marshal_offset':c['marshal_offset'],'locals':c['localsplusnames'],'instructions':c['instructions']})
allnames={n for r in rs for c in r['codes'] for n in c['names']};terms=['GetGameplay','Camera','MainCamera','ICamera','Transform','ViewMatrix','Project','ProjectInner','CameraMatrix','GetScreenSize','SetScreenSize','WorldPosition']
summary={'module_counts':{str(r['index']):r['code_count'] for r in rs},'branch_validation':validation,'exact_co_names_presence':{t:t in allnames for t in terms},'limits':'Exact co_names absence in these three modules only; dynamic getattr/configuration can introduce other attributes.'}
(OUT/'camera-validation.json').write_text(json.dumps(summary,indent=2));(OUT/'camera-selected-evidence.json').write_text(json.dumps(extract,indent=2));print('BAD_BRANCHES',sum(not x['branch_targets_on_instruction_boundaries'] for x in validation))
