"""Read only the reflected IEntity.Skeleton record and adjacent callbacks."""
from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'StaticAnalysis'))
from audit_v2 import RawPE, PINNED

BINARY = Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe')
pe = RawPE(BINARY)
if pe.sha != PINNED:
    raise SystemExit(f'PINNED_SHA_MISMATCH {pe.sha}')

record_rva = 0x4f779b0
record_size = 0xa0
offset = pe.offset(record_rva, record_size)
if offset is None:
    raise SystemExit('record RVA is not file-backed')
candidate_callbacks = {
    'first': 0x57bd70,
    'store_candidate': 0x58b130,
}
out = {
    'sha256': pe.sha,
    'record': {
        'rva': hex(record_rva), 'file_offset': hex(offset),
        'size': record_size,
        'bytes_hex': pe.d[offset:offset + record_size].hex(' '),
        'ascii_literals': ['IEntity.Skeleton', 'Parameter_2'],
        'adjacent_callback_candidates': {
            'rva_0x4f77a30': hex(0x57bd70),
            'rva_0x4f77a38': hex(0x57bd70),
            'rva_0x4f77a48': hex(0x58b130),
        },
    },
    'candidate_callback_bodies': {},
    'limitation': 'The record adjacency does not establish callback roles or prove that assigning IEntity.Skeleton sets ActorComponent.Parent.',
}
for label, rva in candidate_callbacks.items():
    out['candidate_callback_bodies'][label] = {
        'rva': hex(rva),
        'runtime_function': [hex(x) for x in pe.function(rva)] if pe.function(rva) else None,
        'instructions': [pe.row(ins) for ins in pe.decode(rva, 32)],
    }
(Path(__file__).with_name('12-ientity-skeleton-property-static.json')).write_text(
    json.dumps(out, indent=2, ensure_ascii=True) + '\n', encoding='utf8'
)
print(json.dumps({
    'sha256': pe.sha, 'record_rva': hex(record_rva),
    'callback_candidates': out['record']['adjacent_callback_candidates'],
    'limitation': out['limitation'],
}, indent=2))
