exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
from audit_v2 import references
O=Path(__file__).parent
rs=references(pe,{0x5bb9e18:'GetGameplay'});(O/'getgameplay-xrefs.json').write_text(json.dumps(rs,indent=2));print(json.dumps(rs,indent=2))
for f in {int(r['function_begin_rva'],16) for r in rs if 'function_begin_rva' in r}:
 rows=[pe.row(i) for i in pe.decode(f)];(O/('fn-'+hex(f)+'.json')).write_text(json.dumps(rows,indent=2));print(hex(f),rows[:12])
