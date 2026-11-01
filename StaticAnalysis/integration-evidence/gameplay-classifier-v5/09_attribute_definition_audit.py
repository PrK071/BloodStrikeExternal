from pathlib import Path
import json,runpy,hashlib
R=Path(__file__).resolve().parents[3]/'StaticAnalysis'/'integration-evidence'; outdir=Path(__file__).parent
idx=json.loads((R/'assets'/'script-candidate-index.json').read_text(encoding='utf8'))
literals=json.loads((outdir/'01-literal-owner-search.json').read_text(encoding='utf8'))
rows={r['index']:r for r in idx['results']}
pos=[r for r in literals['positive_streams'] if 'IsPlayerCombatAvatar' in r['hits']]
decode=runpy.run_path(str(R/'assets'/'index_script_candidates.py'))['decode_payload'];Reader=runpy.run_path(str(R/'python-format'/'03-static-marshal.py'))['Reader'];install=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
exact_defs=[];class_body_hits=[];tag_literal_modules=[];parsed=0
for hit in pos:
 r=rows[hit['index']];p=install/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
 with p.open('rb') as f:f.seek(r['offset']);raw=f.read(r['size'])
 assert hashlib.sha256(raw).hexdigest()==r['compressed_sha256']
 data=decode(raw,8388608);assert hashlib.sha256(data).hexdigest()==r['decoded_sha256']
 rd=Reader(data);rd.obj();assert rd.p==len(data);parsed+=1
 module=next(c for c in rd.codes if c['qualname']=='<module>')
 for c in rd.codes:
  if c['name']=='IsPlayerCombatAvatar' or c['qualname'].endswith('.IsPlayerCombatAvatar'):
   exact_defs.append({'index':r['index'],'path':r['filename_candidates'],'qualname':c['qualname'],'line':c['firstlineno']})
  if c['argcount']==0 and c['name']!='<module>' and 'IsPlayerCombatAvatar' in c['names']:
   class_body_hits.append({'index':r['index'],'path':r['filename_candidates'],'qualname':c['qualname'],'line':c['firstlineno']})
 if 'IsPlayerCombatAvatar' in [x for x in module['consts'] if isinstance(x,str)]:
  tag_literal_modules.append({'index':r['index'],'path':r['filename_candidates'],'decoded_sha256':r['decoded_sha256'],'string_constant':'IsPlayerCombatAvatar','code_names':module['names']})
report={'source_index_sha256':idx['index_sha256'],'literal_search_source':'01-literal-owner-search.json','literal_positive_count':len(pos),'positive_streams':[{'index':x['index'],'path':x['filename_candidates'],'decoded_sha256':x['decoded_sha256'],'hits':x['hits']} for x in pos],'marshal_parse_count':parsed,'marshal_parse_status':'all selected streams parsed to EOF; no payload execution','function_or_method_definition_matches':exact_defs,'class_body_co_names_matches':class_body_hits,'class_tag_string_constant_matches':tag_literal_modules}
(outdir/'03_attribute_definition_candidates.json').write_text(json.dumps(report,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
print(json.dumps({'literal_positives':len(pos),'parsed_to_eof':parsed,'function_defs':len(exact_defs),'class_body_co_names_matches':len(class_body_hits),'class_tag_string_modules':[(x['index'],x['path']) for x in tag_literal_modules]},indent=2,ensure_ascii=True))



