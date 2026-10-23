from pathlib import Path
import json,hashlib
ROOT=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal');OUT=ROOT/'StaticAnalysis'/'integration-evidence'/'entity-position'
paths=[ROOT/'ExternalCore'/'entity_position.py',ROOT/'tests'/'test_entity_position.py',OUT/'verified-instructions.json',OUT/'cfg-and-types.json',OUT/'ENTITY-POSITION.md']
record={'implementation':'READY','offline_test_cases':8,'offline_status':'PASS','dynamic_tests':0,'game_or_process_opened':False,'sample_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(OUT/'delivery.json').write_text(json.dumps(record,indent=2));print(record['files'])
