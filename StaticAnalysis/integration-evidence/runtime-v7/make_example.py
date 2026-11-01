# Python | runtime-v7/make_example.py | Python 3.12+ | full synthetic semantic recording and actual project CLI.
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from ExternalCore.aim import AimProfile
from ExternalCore.pipeline import process_frame
from ExternalCore.snapshot import FORMAT,write_json
from test_semantic_pipeline import SemanticFixture


def main():
    folder=ROOT/'reports/examples-v7';folder.mkdir(parents=True,exist_ok=True)
    fixture=SemanticFixture().complete()
    provenance='synthetic_V7_semantic_ABI_fixture_not_game_capture'
    write_json(folder/'memory.json',dict(format=FORMAT,provenance=provenance,module=asdict(fixture.module),
        segments=[dict(address=s.address,hex=s.data.hex()) for s in fixture.segments]))
    command=[sys.executable,'-m','ExternalCore','scene',str(folder/'memory.json'),
        '--require-render-input','--output',str(folder/'scene.json'),'--svg',str(folder/'scene.svg')]
    completed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=20)
    if completed.returncode:raise RuntimeError(completed.stderr)
    profile=AimProfile(require_visible=False,counts_per_pixel=(1.,1.))
    frame=process_frame(fixture.memory(),fixture.module,profile=profile,active=True,require_render_input=True)
    if frame.aim.reason!='planned':raise ValueError('synthetic semantic pipeline did not plan a target')
    write_json(folder/'plan.json',dict(provenance=provenance,profile=profile,frame=frame,
        input_dispatched=False,gameplay_validated=False,publisher_certification=False))
    write_json(folder/'verification.json',dict(status='PASS',scene_cli='PASS',planned_aim='PASS',
        provenance=provenance,protected_game_access=False,system_input_events_sent=False,
        gameplay_validated=False,presented_pixels_validated=False))
    print(json.dumps(dict(status='PASS',folder=str(folder),aim=asdict(frame.aim))))


if __name__=='__main__':main()
