# Python | predicate-code-v6/07_generate_core_spec.py | Python 3.12+ | generate immutable data constants, no target execution.
import json
from pathlib import Path


def main():
    folder=Path(__file__).parent
    baseline=json.loads((folder/'baseline-is-enemy.json').read_text())
    tables=json.loads((folder/'opcode-tables.json').read_text())
    valid=sorted({value for name,value in tables['ids'].items() if 0<=value<256 and name not in
                  {'HAVE_ARGUMENT','MIN_SPECIALIZED_OPCODE','MIN_INSTRUMENTED_OPCODE'}})
    result=dict(canonical_sha256=baseline['canonical_sha256'],byte_length=baseline['code_bytes'],
        code_hex=baseline['code_hex'],canonical=baseline['canonical'],metadata=baseline['required_semantic_fields'],
        filename=baseline['filename'],qualname=baseline['qualname'],valid_opcodes=valid,
        caches_hex=bytes(tables['_PyOpcode_Caches']['values']).hex(),
        deopt_hex=bytes(tables['_PyOpcode_Deopt']['values']).hex())
    source='# Python | ExternalCore/predicate_spec.py | Python 3.12+ | generated pinned predicate data.\n'
    source+='import json\n\nBASE_IS_ENEMY = json.loads('+repr(json.dumps(result,separators=(',',':')))+')\n'
    target=folder.parents[2]/'ExternalCore'/'predicate_spec.py'
    target.write_text(source,encoding='utf-8')
    print(target)


if __name__=='__main__':main()
