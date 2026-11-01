from pathlib import Path
import runpy,json,hashlib
EV=Path('StaticAnalysis/integration-evidence'); IDX=json.loads((EV/'assets/script-candidate-index.json').read_text(encoding='utf8')); decode=runpy.run_path(str(EV/'assets/index_script_candidates.py'))['decode_payload']; install=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
terms=[b'IsEnemy',b'CanDamage',b'IsTeammate',b'IsFriend',b'IGameLogicBase',b'CGameLogicBase',b'EnemyFilter',b'modeCache',b'mode_cache',b'diagnostic',b'Diagnostic']
hits=[];counts={t.decode():0 for t in terms}
for r in IDX['results']:
 p=install/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
 with p.open('rb') as f:f.seek(r['offset']);raw=f.read(r['size'])
 assert len(raw)==r['size'] and hashlib.sha256(raw).hexdigest()==r['compressed_sha256']
 data=decode(raw,8388608);assert hashlib.sha256(data).hexdigest()==r['decoded_sha256']
 found=[t.decode() for t in terms if t in data]
 for t in found:counts[t]+=1
 if found:hits.append({'index':r['index'],'path':r['filename_candidates'],'terms':found,'compressed_sha256':r['compressed_sha256'],'decoded_sha256':r['decoded_sha256']})
Path(__file__).with_name('01-literal-scan.json').write_text(json.dumps({'index_sha256':IDX['index_sha256'],'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','stream_count':len(IDX['results']),'counts':counts,'hits':hits},indent=2)+'\n',encoding='utf8')
print(counts);print('hit streams',len(hits))
