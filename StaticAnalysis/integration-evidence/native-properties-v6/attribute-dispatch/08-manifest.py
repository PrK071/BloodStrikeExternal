from pathlib import Path
import json,hashlib
O=Path(__file__).parent
contract={'sample_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','operand_semantics_verified':False,'native_entity_type_rva':'0x796f3c0','native_entity_getattro':'0x1439f30','native_entity_setattro':'0x143a080','generic_getattro':'0x2a094d0','generic_withdict':'0x2a0a1c0','dunder_hook_source_pattern':'0x2a1dca0','lookup_order':['host generic descriptors/instance/class attributes','host bridge cached map generic descriptors/instance/class attributes','native replicated map lookup12f5f60'],'truth':{'helper_rva':'0x2a09600','nb_bool':'type+0x60 -> suite+0x48','mp_length':'type+0x70 -> suite+0','sq_length':'type+0x68 -> suite+0','default':'True only when applicable actual-type slots are absent','nonzero_unknown_slots':'unknown; never execute'},'limits':['No live effective slots or operands observed','NumericMap key/value alone is not host.attr equivalence','Custom descriptors/getattribute and map aliases remain validation requirements','No opponent filter claimed']}
(O/'dispatch-contract.json').write_text(json.dumps(contract,indent=2))
m={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='artifact-manifest.json'}
(O/'artifact-manifest.json').write_text(json.dumps(m,indent=2));print('dispatch evidence files',len(m))
