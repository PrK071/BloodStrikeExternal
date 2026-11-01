exec((__import__('pathlib').Path(__file__).parent/'01-runtime-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent
selected=[];r,n=pe.dirs[0];d=pe.unpack('<IIHHIIIIIII',r)
requested=['PyInterpreterState_Head','PyInterpreterState_Main','PyImport_GetModuleDict','PyModule_GetDict','_PyRuntime','PyModule_Type']
for i in range(d[7]):
 sr=pe.unpack('<I',d[9]+i*4)[0];name=pe.string(sr)
 if name in requested:
  ordinal=pe.unpack('<H',d[10]+i*2)[0];target=pe.unpack('<I',d[8]+ordinal*4)[0]
  selected.append(dict(name=name,rva=hex(target)))
root=0x925f000;type_rva=0x7a1b1f0;name_rva=pe.unpack('<Q',type_rva+24)[0]-pe.base
assert pe.d[pe.offset(root):pe.offset(root)+8]==b'xdebugpy'
assert pe.unpack('<Q',root+8)[0]==0x30e00f0
assert pe.unpack('<Q',root+0x28)[0]==0x328
assert pe.unpack('<Q',root+0x40)[0]==0x1c68
assert pe.unpack('<Q',root+0x60)[0]==0x1de8
assert pe.string(name_rva)=='module'
out=dict(sample_sha256=pe.sha,execution='static file reads only; target never loaded/executed; no process opened',
 root=dict(runtime_rva=hex(root),section=pe.section(root),runtime_debug_cookie='xdebugpy',version='0x030e00f0',free_threaded=False,
           head_slot_rva='0x925f328',head_slot_image_qword=hex(pe.unpack('<Q',root+0x328)[0]),
           initialization_corroboration='runtime-root.json: function 0x2af9e50 passes address RVA0x925f000 to 0x2addac0'),
 route=[dict(operation='read_pointer',address='module_base + 0x925f328',result='interpreter list head'),
        dict(operation='iterate_bounded_list',next_offset='0x1c68',id_offset='0x1c70',id_type='int64',selection='prefer id==0; if looking across interpreters preserve interpreter identity and reject duplicate matches'),
        dict(operation='read_pointer',address='interpreter + 0x1de8',result='sys.modules dictionary',validation='exact PyDict_Type as established in python-owner-v5/layout-contract.json'),
        dict(operation='lookup_dictionary_key',key='gclient.genv',result='module object',validation='object.ob_type +0x08 equals module_base+0x7a1b1f0 for exact module type; source permits subclasses but exact type is conservative'),
        dict(operation='read_pointer',address='module_object + 0x10',result='module.__dict__',validation='non-null and exact PyDict_Type'),
        dict(operation='lookup_dictionary_key',key='player',alternate='main_player',result='Python local-player owner; assignments/lifetime established separately by existing model bytecode evidence')],
 module_type=dict(rva=hex(type_rva),name_rva=hex(name_rva),name=pe.string(name_rva),basicsize=hex(pe.unpack('<Q',type_rva+32)[0]),
                  header_bytes=pe.d[pe.offset(type_rva):pe.offset(type_rva)+56].hex(' '),md_dict_offset='0x10',getter_rva='0x2a94850'),
 export_search=dict(requested=requested,exported_name_count=d[7],matches=selected),
 confidence='Exact native runtime/module route supported by file-resident self-describing offsets and disassembly; module and player presence not observed at runtime',
 limitations=['sys.modules and player are runtime mutable pointers; image head slot is zero and cannot reveal live objects',
 'No game execution, process attachment or process memory read was performed',
 'Acquisition cannot take the native interpreter mutex; repeated equal reads still cannot prove atomicity, liveness or absence of ABA',
 'A module may be absent during startup/teardown, aliased under another name, or present in another interpreter',
 'The route reaches a Python object only; mapping that owner to native actor/local flags still needs separately verified owner layout and observation',
 'Dictionary/Unicode decoding must reuse the pinned CPython3.14 contracts, not assume Python3.12 host layouts'])
(O/'local-player-route.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
