exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
from audit_v2 import references
O=Path(__file__).parent
rs=references(pe,{0x80d5980:'GetGameplay_root_cell',0x8e455b8:'GetGameplay_result_type_cell',0x4f45130:'ViewMatrix_member_cell'});(O/'native-root-xrefs.json').write_text(json.dumps(rs,indent=2));print(json.dumps(rs,indent=2))
for r in [0x2d829a0]:
 rows=[pe.row(i) for i in pe.decode(r)];(O/('fn-'+hex(r)+'.json')).write_text(json.dumps(rows,indent=2));print(hex(r),rows[:30])
