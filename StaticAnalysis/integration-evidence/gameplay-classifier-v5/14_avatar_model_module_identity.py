"""Static import/class-body evidence for AvatarModel.__module__ namespace."""
from pathlib import Path
import hashlib, json, runpy

ROOT = Path(__file__).resolve().parents[3]
EV = ROOT / 'StaticAnalysis' / 'integration-evidence'
OUT = Path(__file__).with_name('14-avatar-model-module-identity.json')
INDEX = json.loads((EV / 'assets' / 'script-candidate-index.json').read_text(encoding='utf8'))
decode = runpy.run_path(str(EV / 'assets' / 'index_script_candidates.py'))['decode_payload']
Reader = runpy.run_path(str(EV / 'python-format' / '03-static-marshal.py'))['Reader']
instructions = runpy.run_path(str(EV / 'python-format' / '05-opcodes-selected.py'))['instructions']
INSTALL = Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
TARGET_SHA256 = 'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
MODULES = [61925, 143510]


def load_module(index):
    row = next(item for item in INDEX['results'] if item['index'] == index)
    path = INSTALL / ('Resources' + ('' if row['package'] == 0 else str(row['package'])) + '.mpk')
    with path.open('rb') as stream:
        stream.seek(row['offset'])
        packed = stream.read(row['size'])
    assert len(packed) == row['size']
    assert hashlib.sha256(packed).hexdigest() == row['compressed_sha256']
    decoded = decode(packed, 8_388_608)
    assert hashlib.sha256(decoded).hexdigest() == row['decoded_sha256']
    reader = Reader(decoded)
    reader.obj()
    assert reader.p == len(decoded)
    return row, reader


def decode_ops(code):
    return instructions([
        {'opcode': code['code'][offset], 'arg_byte': code['code'][offset + 1]}
        for offset in range(0, len(code['code']), 2)
    ])


def row(op, code):
    arg = op['arg']
    resolved = None
    if op['opname'] in {'IMPORT_NAME', 'IMPORT_FROM', 'LOAD_NAME', 'STORE_NAME'}:
        if arg < len(code['names']):
            resolved = code['names'][arg]
    elif op['opname'] in {'LOAD_ATTR', 'LOAD_METHOD', 'LOAD_GLOBAL'}:
        name_index = arg >> 1
        if name_index < len(code['names']):
            resolved = code['names'][name_index]
    elif op['opname'] == 'LOAD_CONST' and arg < len(code['consts']):
        value = code['consts'][arg]
        resolved = value.get('name') if isinstance(value, dict) else (value if isinstance(value, str) else None)
    return {'offset': op['offset'], 'op': op['opname'], 'arg': arg, 'resolved': resolved}


records = []
for index in MODULES:
    entry, reader = load_module(index)
    result = {'index': index, 'filename_candidates': entry['filename_candidates'],
              'decoded_sha256': entry['decoded_sha256'], 'parsed_to_eof': True}
    module_code = next(code for code in reader.codes if code['qualname'] == '<module>')
    module_ops = decode_ops(module_code)
    if index == 61925:
        import_hits = []
        for position, op in enumerate(module_ops):
            if op['opname'] != 'IMPORT_NAME':
                continue
            name = module_code['names'][op['arg']] if op['arg'] < len(module_code['names']) else None
            if name and 'avatar_model' in name:
                import_hits.append([row(item, module_code) for item in module_ops[position:position + 6]])
        result['avatar_model_import_sequences'] = import_hits
    else:
        class_code = next(code for code in reader.codes if code['qualname'] == 'AvatarModel')
        class_ops = decode_ops(class_code)
        class_body_refs = []
        for op in module_ops:
            if op['opname'] == 'LOAD_CONST' and op['arg'] < len(module_code['consts']):
                value = module_code['consts'][op['arg']]
                if isinstance(value, dict) and value.get('name') == 'AvatarModel':
                    class_body_refs.append({
                        'module_bytecode_offset': op['offset'],
                        'opcode': op['opname'], 'co_consts_index': op['arg'],
                        'constref': {'marshal_offset': value.get('marshal_offset'),
                                     'name': value.get('name')},
                    })
        result['avatar_model_class_body'] = {
            'qualname': class_code['qualname'], 'source_filename': class_code.get('filename'),
            'code_sha256': hashlib.sha256(class_code['code']).hexdigest(),
            'module_code_ref': class_body_refs,
            'initial_namespace_instructions': [row(op, class_code) for op in class_ops[:14]],
        }
        result['module_name_references'] = [row(op, module_code) for op in module_ops
                                            if op['opname'] in {'LOAD_NAME', 'STORE_NAME'}
                                            and op['arg'] < len(module_code['names'])
                                            and module_code['names'][op['arg']] == '__name__']
    records.append(result)

out = {
    'target_sha256': TARGET_SHA256,
    'scope': 'Only previously identified MPK streams 61925 and 143510; compressed/decoded hashes verified; static marshal parse to EOF; no imports or payload execution.',
    'interpretation': 'The consumer import operand is the evidence for the namespace bound to the imported AvatarModel class. co_filename is recorded only as source metadata, not treated as the import namespace. The AvatarModel class body seeds __module__ from the executing module __name__; the runtime importer binding itself is not executed.',
    'modules': records,
}
OUT.write_text(json.dumps(out, indent=2, ensure_ascii=True) + '\n', encoding='utf8')
print(json.dumps(out, indent=2, ensure_ascii=True))
