exec((__import__('pathlib').Path(__file__).parent/'01-types.py').read_text().split('O=')[0])
O=Path(__file__).parent
out=dict(target_sha256=pe.sha,abi='CPython3.14.0 GIL Windows AMD64 little-endian; no target execution',
 types=dict(function=dict(rva='0x7a135a0',name='function',tp_basicsize=0x98,tp_itemsize=0),code=dict(rva='0x7a28410',name='code',tp_basicsize=0xd0,tp_itemsize=2)),
 PyFunctionObject=dict(ob_type=8,func_globals=0x10,func_builtins=0x18,func_name=0x20,func_qualname=0x28,func_code=0x30,func_defaults=0x38,func_kwdefaults=0x40,func_closure=0x48,func_module=0x68,sizeof=0x98),
 PyCodeObject=dict(ob_type=8,ob_size=0x10,co_consts=0x18,co_names=0x20,co_exceptiontable=0x28,co_flags=0x30,co_argcount=0x34,co_posonlyargcount=0x38,co_kwonlyargcount=0x3c,co_stacksize=0x40,co_firstlineno=0x44,co_nlocalsplus=0x48,co_nlocals=0x50,co_ncellvars=0x54,co_nfreevars=0x58,co_localsplusnames=0x60,co_localspluskinds=0x68,co_filename=0x70,co_name=0x78,co_qualname=0x80,co_executors=0x98,_co_cached=0xa0,_co_monitoring=0xb0,co_code_adaptive=0xd0,sizeof_with_one_char_rounded=0xd8),
 bytecode=dict(length='signed int64 at code+0x10 multiplied by2, bounded before reading',start='code+0xd0',unit='little-endian [opcode_byte,arg_byte]',code_getter='0x2b23240 -> 0x2b20c30',base_code_unit_getter='0x2babf10',caches_rva='0x59bde60',deopt_rva='0x59bdf60',map_size=256,
  rule='map opcode through Deopt, preserve argument byte, assemble EXTENDED_ARG, skip Caches[base] words; cache payload bytes are mutable and excluded',
  reject=['opcode CACHE outside skipped cache payload','unknown opcode','opcode>=234 (MIN_INSTRUMENTED_OPCODE), including ENTER_EXECUTOR255','cache overrun or odd byte length','trailing EXTENDED_ARG or more than3 extensions','changed code pointer, length, signature/names/constants/closure/defaults during bracketed observation']),
 corroboration=dict(function_fields='native-getters.json + __module__ member atRVA0x7a13028',code_fields='member descriptors atRVA0x7a28080/0x7a280a8/0x7a280f8/0x7a28120; native debug offsets in native-getters.json',adaptive_length='native-code-bytes.json:2b20c81/2b20c85/2b20c8c',opcode_tables='opcode-tables.json: whole256-byte source maps exactly match native PE data; native-code-bytes.json code references both',
 source_only_fields='remaining function/common and code layout fields are source-derived for corroborated GIL3.14 AMD64 ABI; not individually confirmed by getter'),
 identity_limits=['function name/qualname/module are mutable labels, not identity',
 'canonical opcode fingerprint must be combined with exact co_names/constants/signature/locals/freevars/defaults/closure checks',
 'known code does not prove it is the active resolved method: validate actual instance/type/MRO/dictionary/descriptor precedence, and reject unsupported custom dispatch',
 'known IsEnemy body still invokes argument truthiness, attribute access and comparisons, whose behavior can depend on descriptors and operand types',
 'read-only repeated reads cannot establish lifetime, atomicity, absence of ABA or simultaneous module mutation'])
(O/'predicate-code-contract.json').write_text(json.dumps(out,indent=2));print('contract written')
