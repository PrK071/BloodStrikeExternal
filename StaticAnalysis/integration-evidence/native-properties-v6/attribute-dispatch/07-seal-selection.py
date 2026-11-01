exec((__import__('pathlib').Path(__file__).parent.parent/'01-names.py').read_text().split('O=')[0])
from iced_x86 import Decoder
import hashlib
O=Path(__file__).parent;out={}
for r,n in [(0x2a1dca0,0x1ad)]:
 off=pe.offset(r,n);out[hex(r)]=[pe.row(i) for i in Decoder(64,pe.d[off:off+n],ip=pe.base+r)]
(O/'dunder-hook-contiguous.json').write_text(json.dumps(out,indent=2))
E=O.parent.parent
framework=json.loads((O.parent/'property-python-static.json').read_text());hosts=json.loads((O/'host-classes-static.json').read_text());selected=[];negative=[]
for m in framework+hosts:
 for c in m['codes']:
  if c['qualname'] in ['ClientEntity.__getattr__','ClientEntity.__setattr__','Property','PropertyMetaClass.__new__','CombatAvatar','PlayerCombatAvatar','CombatAvatarMember','PlayerCombatAvatarMember','Entity']:
   selected.append(dict(index=m['index'],decoded_sha256=m['decoded_sha256'],code=c))
 for term in ['faction','combat_state','__bool__','__len__','__getattribute__']:
  defs=[{'qualname':c['qualname'],'marshal_offset':c['marshal_offset']} for c in m['codes'] if c['name']==term]
  negative.append(dict(index=m['index'],term=term,matching_code_definitions=defs,scope='Only direct code names in these selected complete modules; no inherited native descriptors or monkeypatching covered.'))
(O/'python-dispatch-selected.json').write_text(json.dumps(selected,indent=2));(O/'bounded-definition-audit.json').write_text(json.dumps(negative,indent=2))
# Pin exact source evidence hashes without modifying or duplicating upstream artifacts.
refs=[]
for p in [O.parent/'entity-type-binding-xrefs.json',O.parent/'area-type-binding-xrefs.json',O.parent/'map-mapping-and-descriptor.json',O.parent/'typed-storage-getters.json',O.parent/'managed-models/native-exact-ranges.json',O.parent/'managed-models/object.c',O.parent/'managed-models/cpython-object.h']:
 refs.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(O/'upstream-sources.json').write_text(json.dumps(refs,indent=2));print('selectedcodes',len(selected),'direct definitions',[(x['index'],x['term'],len(x['matching_code_definitions'])) for x in negative if x['matching_code_definitions']])
for m in framework:
 for c in m['codes']:
  if c['qualname']=='Property':print('\n'.join(str(x) for x in c['instructions'][-17:]))
