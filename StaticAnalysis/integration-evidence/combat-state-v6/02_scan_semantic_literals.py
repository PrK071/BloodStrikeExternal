from pathlib import Path
import runpy,json,hashlib
EV=Path('StaticAnalysis/integration-evidence'); IDX=json.loads((EV/'assets/script-candidate-index.json').read_text(encoding='utf8')); decode=runpy.run_path(str(EV/'assets/index_script_candidates.py'))['decode_payload']; install=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
terms=[b'IsEnemy',b'IsTeammate',b'IsSameTeam',b'combat_team_id',b'IsFreeForAll',b'FreeForAll',b'FFA',b'game_mode',b'match_mode',b'server_hp',b'maxhp',b'is_alive',b'IsAlive',b'GetPlayer',b'main_player']
hits=[]; counts={t.decode():0 for t in terms}
for r in IDX['results']:
 p=install/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
 with p.open('rb') as f:f.seek(r['offset']); raw=f.read(r['size'])
 if len(raw)!=r['size'] or hashlib.sha256(raw).hexdigest()!=r['compressed_sha256']:raise ValueError(f"bad compressed {r['index']}")
 d=decode(raw,8388608)
 if hashlib.sha256(d).hexdigest()!=r['decoded_sha256']:raise ValueError(f"bad decoded {r['index']}")
 found=[t.decode() for t in terms if t in d]
 for t in found: counts[t]+=1
 if found and any(t in found for t in ('IsEnemy','IsTeammate','IsSameTeam','FreeForAll','FFA','combat_team_id','server_hp','maxhp','main_player')): hits.append({'index':r['index'],'filename_candidates':r['filename_candidates'],'terms':found,'compressed_sha256':r['compressed_sha256'],'decoded_sha256':r['decoded_sha256']})
out={'index_sha256':IDX['index_sha256'],'scanned_streams':len(IDX['results']),'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','term_counts':counts,'matches':hits}
Path('StaticAnalysis/integration-evidence/combat-state-v6/02-literal-positive-indexes.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
print('stream count',len(IDX['results']),'retained positives',len(hits));print(json.dumps(counts,indent=2))
