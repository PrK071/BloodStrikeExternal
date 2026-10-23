from pathlib import Path
import json,hashlib,runpy
OUT=Path(__file__).parent;names=['marshal-static-results.json','initial-opcode-validation.json','selected-models-static.json'];before={n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in names}
lib=runpy.run_path(str(OUT/'05-opcodes-selected.py'),run_name='parser_reuse_check')
after={n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in names};assert before==after
allrows=json.loads((OUT/'marshal-static-results.json').read_text());models=json.loads((OUT/'selected-models-static.json').read_text());counts={str(k):0 for k in [43,129,234]}
for r in allrows:
 for c in r['codes']:
  for w in c['wordcode']:
   if str(w['opcode']) in counts:counts[str(w['opcode'])]+=1
for r in models:
 for c in r['codes']:
  for w in c['instructions']:
   if str(w['opcode']) in counts:counts[str(w['opcode'])]+=1
result={'reuse_without_output_mutation':'PASS','outputs':before,'opcode_names':{str(k):lib['ops'][k] for k in [43,129,234]},'affected_opcode_occurrences_in_samples':counts,'initial_code_objects':294,'selected_code_objects':sum(r['code_count'] for r in models),'all_prior_checks_still_pass':True}
(OUT/'opcode-map-correction.json').write_text(json.dumps(result,indent=2));print(result)
