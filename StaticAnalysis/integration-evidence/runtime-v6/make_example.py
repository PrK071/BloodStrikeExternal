# Python | runtime-v6/make_example.py | Python 3.12+ | reproducible synthetic recordings and real project CLI, no game access.
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from ExternalCore.snapshot import FORMAT,write_json
from state_fixture import StateFixture
from test_predicate import PredicateFixture


def record(fixture,path):
    write_json(path,dict(format=FORMAT,provenance='synthetic_V6_ABI_fixture_not_game_capture',
        module=asdict(fixture.module),segments=[dict(address=s.address,hex=s.data.hex()) for s in fixture.segments]))


def main():
    folder=ROOT/'reports/examples-v6';folder.mkdir(parents=True,exist_ok=True)
    fixture=StateFixture().runtime().properties()
    record(fixture,folder/'state-memory.json')
    predicate=PredicateFixture().predicate()
    record(predicate,folder/'predicate-memory.json')
    write_json(folder/'addresses.json',dict(function=hex(predicate.function),
        provenance='address inside synthetic recording, not a game offset'))
    commands=[['scene',str(folder/'state-memory.json'),'--output',str(folder/'state-frame.json'),
               '--svg',str(folder/'state-frame.svg')],
              ['predicate',str(folder/'predicate-memory.json'),'--function',hex(predicate.function),
               '--output',str(folder/'predicate-body.json')]]
    for command in commands:
        completed=subprocess.run([sys.executable,'-m','ExternalCore',*command],cwd=ROOT,
            capture_output=True,text=True,timeout=20)
        if completed.returncode:raise RuntimeError(completed.stderr)
    state=json.loads((folder/'state-frame.json').read_text(encoding='utf-8'))
    body=json.loads((folder/'predicate-body.json').read_text(encoding='utf-8'))
    classification=state['frame']['scene']['actors'][0]['classification']
    if not (classification['category']=='player' and classification['local'] is True and
            classification['alive'] is None and body['body']['active_dispatch_verified'] is False):
        raise ValueError('synthetic CLI verification failed')
    write_json(folder/'verification.json',dict(status='PASS',scene_cli='PASS',predicate_cli='PASS',
        provenance=state['provenance'],protected_game_access=False,target_code_executed=False,
        system_input_events_sent=False,gameplay_validated=False,commands=commands))
    print(json.dumps(dict(status='PASS',folder=str(folder),function=hex(predicate.function))))


if __name__=='__main__':main()
