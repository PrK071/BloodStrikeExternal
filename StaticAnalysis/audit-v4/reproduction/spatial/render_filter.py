import json
from pathlib import Path
p=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\audit-v4\spatial\render-source');d=json.loads((p/'candidate-functions.json').read_text());c=json.loads((p/'fa0-candidates.json').read_text());print('TOTAL',len(c))
for x in c:
 t=x['instruction']['text']
 if ('xmm' in t and '[' in t and 'rsp' not in t and 'rbp' not in t) or (0x1900000<int(x['function'],16)<0x1d00000):print(x['function'],x['instruction']['rva'],t)
print('REGISTRY GETTER')
for x in d['0x766370']:print(x['rva'],x['text'])
