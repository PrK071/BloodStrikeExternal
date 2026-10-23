import json
from pathlib import Path
out=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\audit-v4\spatial\render-source')
c=json.loads((out/'fa0-candidates.json').read_text());res=[]
for x in c:
 t=x['instruction']['text'];kind='other-or-immediate'
 if '[rsp' in t or '[rbp' in t:kind='stack-frame-or-unproven-rbp-base'
 elif '[' in t:kind='memory-candidate'
 if t.startswith(('movups [','movaps [','movntps [')) and 'rsp' not in t and 'rbp' not in t:kind='vector-store-prioritized'
 res.append({**x,'triage':kind})
(out/'candidate-triage.json').write_text(json.dumps(res,indent=2))
print({k:sum(x['triage']==k for x in res) for k in set(x['triage'] for x in res)})
