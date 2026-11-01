from pathlib import Path
import runpy,json,hashlib
ROOT=Path(__file__).resolve().parents[3]; EV=ROOT/'StaticAnalysis'/'integration-evidence'
IDX=json.loads((EV/'assets'/'script-candidate-index.json').read_text(encoding='utf8'))
DECODE=runpy.run_path(str(EV/'assets'/'index_script_candidates.py'))['decode_payload']
Reader=runpy.run_path(str(EV/'python-format'/'03-static-marshal.py'))['Reader']
OPS=runpy.run_path(str(EV/'python-format'/'05-opcodes-selected.py'))['instructions']
INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
MODS=[107853,14066,86590,68262,76499,145546,2597,3779,78274,92227,132180,86897]
TERMS=()
WHITELIST={
107853:{'PlayerCombatAvatar.init_from_dict','PlayerCombatAvatar.master','PlayerCombatAvatar.destroy','PlayerCombatAvatar.CheckAimTargetWhenStartAds','PlayerCombatAvatar.CheckAimTargetWhenRealAds'},
14066:{'CombatAvatarMember.hp','CombatAvatarMember.combat_team','CombatAvatarMember','CombatAvatarMember._on_set_server_hp','PlayerCombatAvatarMember._on_set_combat_team_id','PlayerCombatAvatarMember._on_set_server_hp','PlayerCombatAvatarMember._on_set_maxhp','PlayerCombatAvatarMember'},
86590:{'PlayerCombatAvatarMember.CheckAimEnemyTimer'},68262:{'AssistAim.SelectTarget'},76499:{'GameLogicEnemyShowStateComp.TickEnemyDistanceForShow'},
145546:{'CGameLogicBase.IsTeammate','GameLogicBase.player'},2597:{'HudTeamInfoComp.OnCombatTeamMemberMaxHpChange'},3779:{'IGameLogicFreeForAll'},
78274:{'SquadFightCombatAvatarToplogo._IsEnemyFor1v1Logic'},92227:{'MobaFactionMapInfoMixin.IsEnemy','MobaFactionMapInfoMixin.IsTeammate'},
132180:{'CGameLogicPeekaboo.IsEnemy','CGameLogicPeekaboo.IsTeammate'},86897:{'GetPlayer'}}
def row(n):return next(x for x in IDX['results'] if x['index']==n)
def parse(n):
 r=row(n);p=INSTALL/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
 with p.open('rb') as f:f.seek(r['offset']);raw=f.read(r['size'])
 assert len(raw)==r['size'] and hashlib.sha256(raw).hexdigest()==r['compressed_sha256']
 data=DECODE(raw,8388608);assert hashlib.sha256(data).hexdigest()==r['decoded_sha256']
 rd=Reader(data);rd.obj();assert rd.p==len(data)
 selected=[]
 for c in rd.codes:
  q=c['qualname']; nm=c.get('names',[]); lc=c.get('localsplusnames',[]); strings=[x for x in c.get('consts',[]) if isinstance(x,str)]
  if q not in WHITELIST.get(n,set()):continue
  b=c['code'];ins=OPS([{'opcode':b[i],'arg_byte':b[i+1]} for i in range(0,len(b),2)])
  rows=[]
  for x in ins:
   a=x['arg'];v=None
   if x['opname'] in {'LOAD_ATTR','LOAD_METHOD','LOAD_GLOBAL'} and a>>1<len(nm):v=nm[a>>1]
   elif x['opname']=='STORE_ATTR' and a<len(nm):v=nm[a]
   elif 'FAST' in x['opname'] and a<len(lc):v=lc[a]
   elif 'NAME' in x['opname'] and a<len(nm):v=nm[a]
   elif x['opname']=='LOAD_CONST' and a<len(c.get('consts',[])):
    z=c['consts'][a];v=z if isinstance(z,(str,int,bool,type(None))) else z.get('qualname',z.get('name')) if isinstance(z,dict) else type(z).__name__
   rows.append({'offset':x['offset'],'op':x['opname'],'arg':a,**({'value':v} if v is not None else {})})
  selected.append({'qualname':q,'line':c.get('firstlineno'),'filename':c.get('filename'),'localsplusnames':lc,'names':nm,'string_consts':strings,'code_sha256':hashlib.sha256(b).hexdigest(),'instructions':rows})
 return {'index':n,'candidate_paths':r['filename_candidates'],'compressed_sha256':r['compressed_sha256'],'decoded_sha256':r['decoded_sha256'],'parsed_to_eof_bytes':rd.p,'code_objects':len(rd.codes),'selected':selected}
mods=[parse(n) for n in MODS]
out={'index_sha256':IDX['index_sha256'],'target_sha256':'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747','scope':'disk-only static MPK decode and marshal/opcode parse; no execution/process access','modules':mods}
Path(__file__).with_name('01-semantic-modules.json').write_text(json.dumps(out,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
print(json.dumps([{'index':m['index'],'path':m['candidate_paths'],'objects':m['code_objects'],'selected':[c['qualname'] for c in m['selected']]} for m in mods],indent=2))


