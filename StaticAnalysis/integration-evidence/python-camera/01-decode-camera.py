from pathlib import Path
import runpy,json,hashlib,zlib
OUT=Path(__file__).parent;ROOT=OUT.parent;lib=runpy.run_path(str(ROOT/'python-format'/'05-opcodes-selected.py'),run_name='camera_decoder');Reader=lib['Reader'];safe=lib['safe'];instructions=lib['instructions'];INSTALL=lib['INSTALL']
proof=json.loads((ROOT/'assets'/'script-candidate-index.json').read_text());results=[]
for row in proof['results']:
 if row['index'] not in [50901,75597,78462]:continue
 p=INSTALL/('Resources'+('' if row['package']==0 else str(row['package']))+'.mpk')
 with p.open('rb') as f:f.seek(row['offset']);b=f.read(row['size'])
 assert hashlib.sha256(b).hexdigest()==row['compressed_sha256'];n=len(b);b=bytearray(b);prefix=min(128-((n-8)%37),n)
 for j in range(prefix):b[j]^=0x9a
 dec=zlib.decompressobj();data=dec.decompress(bytes(b[:n if prefix==n else n-8]),4194305);assert dec.eof and not dec.unused_data and len(data)<=4194304;assert hashlib.sha256(data).hexdigest()==row['decoded_sha256']
 r=Reader(data);root=r.obj();assert r.p==len(data);codes=[]
 for c in r.codes:
  cb=c['code'];assert len(cb)%2==0;ins=instructions([{'opcode':cb[i],'arg_byte':cb[i+1]} for i in range(0,len(cb),2)])
  cc={k:safe(v) for k,v in c.items() if k not in ['consts','linetable','exceptiontable']};cc['consts']=[safe(v) if not isinstance(v,dict) or v.get('kind')!='code' else {'code_ref_offset':v['marshal_offset'],'name':v['name']} for v in c['consts']]
  for x in ins:
   op=x['opname'];a=x['arg'];names=c['names'];locals=c['localsplusnames']
   if op in ['LOAD_NAME','STORE_NAME','DELETE_NAME','STORE_ATTR','DELETE_ATTR','IMPORT_NAME','IMPORT_FROM','STORE_GLOBAL','DELETE_GLOBAL']:x['symbol']=names[a]
   elif op in ['LOAD_GLOBAL','LOAD_ATTR']:x['symbol']=names[a>>1];x['name_flags']=a&1
   elif op=='LOAD_SUPER_ATTR':x['symbol']=names[a>>2];x['name_flags']=a&3
   elif op in ['LOAD_FAST_BORROW','LOAD_FAST','LOAD_FAST_CHECK','LOAD_FAST_AND_CLEAR','STORE_FAST','DELETE_FAST','MAKE_CELL','LOAD_DEREF','STORE_DEREF','LOAD_CLOSURE']:x['symbol']=locals[a]
   elif op in ['LOAD_FAST_BORROW_LOAD_FAST_BORROW','LOAD_FAST_LOAD_FAST','STORE_FAST_LOAD_FAST','STORE_FAST_STORE_FAST']:x['symbols']=[locals[a>>4],locals[a&15]]
   elif op=='LOAD_CONST':x['constant']=cc['consts'][a]
   elif op.startswith(('JUMP','POP_JUMP','FOR_ITER','SEND')):x['target']=x['offset']+2*(1+x['cache_words'])+(-2*a if 'BACKWARD' in op else 2*a)
  cc['instructions']=ins;codes.append(cc)
 results.append({'index':row['index'],'decoded_sha256':row['decoded_sha256'],'status':'EOF_OPCODE_CACHE_PASS','code_count':len(codes),'codes':codes})
(OUT/'camera-modules-static.json').write_text(json.dumps(results,indent=2));print([(r['index'],r['code_count'],r['codes'][-1]['filename']) for r in results])
with (OUT/'camera-disassembly.txt').open('w',encoding='utf8') as f:
 for r in results:
  for c in r['codes']:
   f.write(f"\nINDEX {r['index']} {c['qualname']} marshal={c['marshal_offset']} firstline={c['firstlineno']} locals={c['localsplusnames']}\n")
   for x in c['instructions']:f.write(f"{x['offset']:5} {x['opname']:30} {x['arg']:5} "+json.dumps({k:v for k,v in x.items() if k not in ['offset','opcode','opname','arg','cache_words']},ensure_ascii=True)+'\n')

