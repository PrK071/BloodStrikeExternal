# Python | test_audit_controls.py | Python 3.12+ | Static verifier controls; target binary remains read-only.
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from audit_v2 import RawPE,legacy_audit,save


def main():
    root=Path(__file__).resolve().parent
    binary=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe')
    old=root/'results';out=root/'audit-v2'
    def read(name):return json.loads((old/name).read_text())
    spec=importlib.util.spec_from_file_location('verifier_under_test',root/'verify_evidence.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    fn=next(x for x in read('function-evidence.json') if x['start_rva']=='0x3259770')
    fn=copy.deepcopy(fn);fn['instructions']=fn['instructions'][:3]
    fixture={'summary.json':read('summary.json'),'function-evidence.json':[fn],
             'code-xrefs.json':read('code-xrefs.json')[:1],'core-vtables.json':read('core-vtables.json')[:1],
             'rtti-types.json':read('rtti-types.json')[:1]}
    controls=[]
    with tempfile.TemporaryDirectory(prefix='.audit-controls-',dir=root) as temp:
        directory=Path(temp).resolve()
        # The standard library cleans up this exact, verified workspace-local fixture directory.
        assert directory.parent==root and directory.name.startswith('.audit-controls-')
        def reset():
            for n,v in fixture.items():save(directory/n,v)
            save(directory/'verification.json',{'status':'PASS','note':'stale success control'})
        def run(expected_failure=False,pinned=None):
            argv=['verify_evidence.py','--binary',str(binary),'--results',str(directory)]
            failed=False
            with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
                with patch.object(verifier,'PINNED_SHA256',pinned or verifier.PINNED_SHA256):
                    try:verifier.main()
                    except ValueError:failed=True
            assert failed==expected_failure
            status=json.loads((directory/'verification.json').read_text())['status']
            assert status==('FAIL' if expected_failure else 'PASS')
            return status
        reset();status=run();controls.append({'case':'valid fixture and nine curated packets','result':status})
        reset();bad=copy.deepcopy(fixture['function-evidence.json'])
        raw=bytearray.fromhex(bad[0]['instructions'][0]['bytes']);raw[0]^=1
        bad[0]['instructions'][0]['bytes']=raw.hex(' ');save(directory/'function-evidence.json',bad)
        status=run(True);controls.append({'case':'tampered instruction claim replaces stale PASS with FAIL','result':'PASS_CONTROL','observed_status':status})
        pe=RawPE(binary);audit=legacy_audit(pe,directory)
        assert audit['decoder_mismatches'];controls.append({'case':'independent decoder rejects tampered instruction claim','result':'PASS_CONTROL'})
        reset();status=run(True,pinned='0'*64)
        controls.append({'case':'late curated hash rejection replaces stale PASS with FAIL','result':'PASS_CONTROL','observed_status':status})
    result={'status':'PASS','controls':controls,'game_file_modified':False,'runtime_game_access':False,
            'scope':'small artifact fixtures; not an execution of the game or a claim of gameplay validation'}
    save(out/'verification-controls.json',result);print(json.dumps(result))


if __name__=='__main__':main()
