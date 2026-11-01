"""Static-only focused audit of owner/model STORE_ATTRs in known MPK streams."""
from pathlib import Path
import runpy, json, hashlib

ROOT = Path(__file__).resolve().parents[3]
EV = ROOT / 'StaticAnalysis' / 'integration-evidence'
OUT = Path(__file__).with_name('11-corrected-owner-store-attr-audit.json')
INDEX = json.loads((EV / 'assets' / 'script-candidate-index.json').read_text(encoding='utf8'))
decode = runpy.run_path(str(EV / 'assets' / 'index_script_candidates.py'))['decode_payload']
Reader = runpy.run_path(str(EV / 'python-format' / '03-static-marshal.py'))['Reader']
instructions = runpy.run_path(str(EV / 'python-format' / '05-opcodes-selected.py'))['instructions']
INSTALL = Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
TARGET_SHA256 = 'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
TARGETS = {
    17226: ['CreateDummy', 'CreateModel', 'LoadSkeletonAndGraph', 'BindSkeletonAndGraph'],
    68957: ['SimpleModel.Load'],
    122267: ['BaseModel.__init__'],
    143510: ['AvatarModel.Load', 'AvatarModel.ReloadSkeleton'],
}
INTERESTING = {
    'UserData', 'user_data', 'userdata', 'SetUserData', 'set_user_data',
    'owner', 'model', 'Skeleton', 'CreateObject', 'Parent', 'ActorParent',
}


def parse_module(index):
    row = next(item for item in INDEX['results'] if item['index'] == index)
    path = INSTALL / ('Resources' + ('' if row['package'] == 0 else str(row['package'])) + '.mpk')
    with path.open('rb') as stream:
        stream.seek(row['offset'])
        compressed = stream.read(row['size'])
    assert len(compressed) == row['size']
    assert hashlib.sha256(compressed).hexdigest() == row['compressed_sha256']
    decoded = decode(compressed, 8_388_608)
    assert hashlib.sha256(decoded).hexdigest() == row['decoded_sha256']
    reader = Reader(decoded)
    reader.obj()
    assert reader.p == len(decoded)
    return row, reader


records = []
for index, selected_qualnames in TARGETS.items():
    row, reader = parse_module(index)
    for code in reader.codes:
        if code['qualname'] not in selected_qualnames:
            continue
        ops = instructions([
            {'opcode': code['code'][offset], 'arg_byte': code['code'][offset + 1]}
            for offset in range(0, len(code['code']), 2)
        ])
        relevant = []
        for op in ops:
            arg = op['arg']
            resolved = None
            if op['opname'] in {'LOAD_ATTR', 'LOAD_METHOD', 'LOAD_GLOBAL'}:
                name_index = arg >> 1
                if name_index < len(code['names']):
                    resolved = code['names'][name_index]
            elif op['opname'] == 'STORE_ATTR' and arg < len(code['names']):
                # CPython 3.14 STORE_ATTR uses the direct co_names index.
                resolved = code['names'][arg]
            elif op['opname'] == 'LOAD_CONST' and arg < len(code['consts']):
                value = code['consts'][arg]
                if isinstance(value, str):
                    resolved = value
            if resolved in INTERESTING or op['opname'] == 'STORE_ATTR':
                relevant.append({
                    'offset': op['offset'], 'op': op['opname'],
                    'arg': arg, 'resolved': resolved,
                })
        records.append({
            'index': index, 'filename': code.get('filename'),
            'qualname': code['qualname'],
            'decoded_sha256': row['decoded_sha256'],
            'names': code['names'], 'relevant_instructions': relevant,
            'parsed_to_eof': True,
        })

result = {
    'target_sha256': TARGET_SHA256,
    'scope': 'Previously identified MPK indices 17226, 68957, 122267, 143510 only; compressed and decoded SHA-256 verified; marshal parse to EOF; no payload execution. STORE_ATTR uses direct co_names index; LOAD_ATTR/LOAD_METHOD/LOAD_GLOBAL use arg>>1.',
    'records': records,
}
OUT.write_text(json.dumps(result, indent=2, ensure_ascii=True) + '\n', encoding='utf8')
print(json.dumps([
    {'index': record['index'], 'qualname': record['qualname'],
     'decoded_sha256': record['decoded_sha256'],
     'relevant_instructions': record['relevant_instructions']}
    for record in records
], indent=2, ensure_ascii=True))
