import json
from pathlib import Path
p=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\audit-v4\spatial\render-source');d=json.loads((p/'candidate-functions.json').read_text())
for f in ['0xc46cea','0x789fe0','0x1abd4a0']:
 print('\n',f)
 for x in d[f]:
  t=x['text']
  if t.startswith(('mov r14,','mov r15,','mov rdi,','mov rsi,','lea r14,','lea r15,')) or ('rip_target_string' in x and x['rip_target_string']):print(x['rva'],t,x.get('rip_target_string') or '')
print('NONSTACK WRITES FA0')
for x in json.loads((p/'fa0-candidates.json').read_text()):
 t=x['instruction']['text']
 if t.startswith(('mov [','movups [','movaps [','movntps [','vmovups [')) and 'rsp' not in t and 'rbp' not in t:print(x['function'],x['instruction']['rva'],t)
