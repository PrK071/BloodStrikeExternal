from pathlib import Path
import runpy,json,hashlib
EV=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\integration-evidence');IDX=json.loads((EV/'assets/script-candidate-index.json').read_text());DEC=runpy.run_path(str(EV/'assets/index_script_candidates.py'))['decode_payload'];INST=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
TERMS=[b'StartAssistAimMelee',b'combat_states',b'CombatState',b'KNOCKED']
mods=[x for x in IDX['results'] if any(any(k in p.lower() for k in ('combat_avatar','combatavatarmembers','assist_aim')) for p in x.get('filename_candidates',[]))]
hits=[]
for r in mods:
 p=INST/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
 with p.open('rb') as f:f.seek(r['offset']);raw=f.read(r['size'])
 assert len(raw)==r['size'] and hashlib.sha256(raw).hexdigest()==r['compressed_sha256']
 data=DEC(raw,8388608); assert hashlib.sha256(data).hexdigest()==r['decoded_sha256']
 terms=[t.decode() for t in TERMS if t in data]
 if terms:hits.append({'index':r['index'],'paths':r['filename_candidates'],'compressed_sha256':r['compressed_sha256'],'decoded_sha256':r['decoded_sha256'],'terms':terms})
out={'index_sha256':IDX['index_sha256'],'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','scope':'bounded static string scan only among candidate filenames containing combat_avatar, combatavatarmembers, or assist_aim; decompressed stream hashes checked; no marshal parse or execution','candidate_count':len(mods),'terms':[t.decode() for t in TERMS],'hits':hits}
Path(__file__).with_name('02-bounded-aim-callsite-scan.json').write_text(json.dumps(out,indent=2)+'\n')
print('scanned',len(mods),'hits',len(hits));print(json.dumps(hits,indent=2))
