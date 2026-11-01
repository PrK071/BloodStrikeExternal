"""Focused static evidence for AvatarModel versus WeaponModel IEntity.instance."""
from pathlib import Path
import hashlib, json, runpy

ROOT = Path(__file__).resolve().parents[3]
EV = ROOT / 'StaticAnalysis' / 'integration-evidence'
OUT = Path(__file__).with_name('13-model-instance-discriminator.json')
INDEX = json.loads((EV / 'assets' / 'script-candidate-index.json').read_text(encoding='utf8'))
decode = runpy.run_path(str(EV / 'assets' / 'index_script_candidates.py'))['decode_payload']
Reader = runpy.run_path(str(EV / 'python-format' / '03-static-marshal.py'))['Reader']
instructions = runpy.run_path(str(EV / 'python-format' / '05-opcodes-selected.py'))['instructions']
INSTALL = Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
PINNED_EXE = 'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
MODULES = {
    61925: ['CombatAvatarMember.InitAvatarModel'],
    25281: ['<module>', 'WeaponModel.__init__', 'WeaponModel.Load', 'WeaponModel.AttachWeaponToAvatarHand', 'WeaponModel.AttachWeaponToAvatarLeftHand', 'WeaponModel.AttachWeaponToAvatarBack'],
    68957: ['SimpleModel.Load'],
    94890: ['<module>'],
    143510: ['<module>', 'AvatarModel.__init__', 'AvatarModel.Load'],
}


def decode_module(index):
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


def rows_for(code, lo=None, hi=None):
    ops = instructions([
        {'opcode': code['code'][offset], 'arg_byte': code['code'][offset + 1]}
        for offset in range(0, len(code['code']), 2)
    ])
    rows = []
    for op in ops:
        if lo is not None and op['offset'] < lo:
            continue
        if hi is not None and op['offset'] > hi:
            continue
        arg = op['arg']
        resolved = None
        if op['opname'] in {'LOAD_ATTR', 'LOAD_METHOD', 'LOAD_GLOBAL'}:
            name_index = arg >> 1
            if name_index < len(code['names']):
                resolved = code['names'][name_index]
        elif op['opname'] == 'LOAD_SUPER_ATTR':
            name_index = arg >> 2
            if name_index < len(code['names']):
                resolved = code['names'][name_index]
        elif op['opname'] == 'LOAD_FAST_BORROW_LOAD_FAST_BORROW':
            first, second = (arg >> 4), (arg & 0x0f)
            localsplus = code.get('localsplusnames', [])
            resolved = [localsplus[first] if first < len(localsplus) else None,
                        localsplus[second] if second < len(localsplus) else None]
        elif op['opname'] == 'STORE_ATTR' and arg < len(code['names']):
            resolved = code['names'][arg]
        elif op['opname'] == 'LOAD_CONST' and arg < len(code['consts']):
            value = code['consts'][arg]
            if isinstance(value, str):
                resolved = value
            elif isinstance(value, dict):
                resolved = value.get('name')
        rows.append({'offset': op['offset'], 'op': op['opname'], 'arg': arg, 'resolved': resolved})
    return rows


records = []
class_builds = []
for index, targets in MODULES.items():
    row, reader = decode_module(index)
    selected = []
    for code in reader.codes:
        if code['qualname'] not in targets:
            continue
        if code['qualname'] == '<module>':
            ops = instructions([
                {'opcode': code['code'][offset], 'arg_byte': code['code'][offset + 1]}
                for offset in range(0, len(code['code']), 2)
            ])
            for position, op in enumerate(ops):
                if op['opname'] != 'LOAD_BUILD_CLASS':
                    continue
                # Keep short windows around class declarations only.
                window = ops[max(0, position - 2):min(len(ops), position + 14)]
                names = []
                for item in window:
                    if item['opname'] == 'LOAD_NAME' and item['arg'] < len(code['names']):
                        names.append(code['names'][item['arg']])
                    elif item['opname'] == 'LOAD_CONST' and item['arg'] < len(code['consts']):
                        value = code['consts'][item['arg']]
                        if isinstance(value, dict):
                            names.append(value.get('name'))
                        elif isinstance(value, str):
                            names.append(value)
                if set(names) & {'WeaponModel', 'AvatarModel', 'PoseSenderModel'}:
                    class_builds.append({
                        'module_index': index, 'decoded_sha256': row['decoded_sha256'],
                        'candidate_class_names': names,
                        'instructions': [
                            {'offset': item['offset'], 'op': item['opname'], 'arg': item['arg']}
                            for item in window
                        ],
                    })
        if code['qualname'] == 'CombatAvatarMember.InitAvatarModel':
            selected.append({'qualname': code['qualname'], 'localsplusnames': code['localsplusnames'],
                             'names': code['names'], 'instructions': rows_for(code)})
        elif code['qualname'] == 'WeaponModel.__init__':
            selected.append({'qualname': code['qualname'], 'argcount': code['argcount'],
                             'localsplusnames': code['localsplusnames'], 'names': code['names'],
                             'instructions': rows_for(code, 0, 180)})
        elif code['qualname'] == 'WeaponModel.Load':
            selected.append({'qualname': code['qualname'], 'localsplusnames': code['localsplusnames'],
                             'names': code['names'], 'instructions': rows_for(code, 300, 480)})
        elif code['qualname'] == 'WeaponModel.AttachWeaponToAvatarHand':
            selected.append({'qualname': code['qualname'], 'localsplusnames': code['localsplusnames'],
                             'names': code['names'], 'instructions': rows_for(code, 0, 220)})
        elif code['qualname'] == 'WeaponModel.AttachWeaponToAvatarLeftHand':
            selected.append({'qualname': code['qualname'], 'localsplusnames': code['localsplusnames'],
                             'names': code['names'], 'instructions': rows_for(code, 0, 430)})
        elif code['qualname'] == 'WeaponModel.AttachWeaponToAvatarBack':
            selected.append({'qualname': code['qualname'], 'localsplusnames': code['localsplusnames'],
                             'names': code['names'],
                             'instructions': rows_for(code, 840, 980) + rows_for(code, 1200, 1325)})
        elif code['qualname'] == 'SimpleModel.Load':
            selected.append({'qualname': code['qualname'], 'localsplusnames': code['localsplusnames'],
                             'names': code['names'], 'instructions': rows_for(code, 1110, 1570)})
        elif code['qualname'] == 'AvatarModel.__init__':
            selected.append({'qualname': code['qualname'], 'argcount': code['argcount'],
                             'localsplusnames': code['localsplusnames'], 'names': code['names'],
                             'instructions': rows_for(code, 0, 42)})
        elif code['qualname'] == 'AvatarModel.Load':
            selected.append({'qualname': code['qualname'], 'localsplusnames': code['localsplusnames'],
                             'names': code['names'], 'instructions': rows_for(code, 0, 60) + rows_for(code, 1120, 1170)})
    records.append({'index': index, 'filename_candidates': row['filename_candidates'],
                    'decoded_sha256': row['decoded_sha256'], 'selected_code': selected,
                    'parsed_to_eof': True})

result = {
    'target_sha256': PINNED_EXE,
    'scope': 'Only previously identified MPK indices 61925, 25281, 68957, 94890, 143510; each compressed and decoded hash verified, static marshal parse to EOF, no Python payload execution.',
    'store_attr_resolution': 'CPython 3.14 STORE_ATTR uses direct co_names index; LOAD_ATTR/LOAD_METHOD/LOAD_GLOBAL use arg>>1.',
    'class_build_windows': class_builds,
    'modules': records,
    'classification_consequence': 'IEntity.owner alone is insufficient: a WeaponModel can forward its owner through SimpleModel and its IEntity wrapper stores .owner. The .instance object is the discriminating Python model object: AvatarModel is on the body path; WeaponModel is a distinct SimpleModel branch. This does not by itself exclude AvatarModel previews or prove an external reader can recover the wrapper attributes.',
}
OUT.write_text(json.dumps(result, indent=2, ensure_ascii=True) + '\n', encoding='utf8')
print(json.dumps({'output': str(OUT), 'module_count': len(records), 'class_build_windows': len(class_builds),
                  'selected_code_count': sum(len(m['selected_code']) for m in records),
                  'scope': result['scope']}, indent=2))
