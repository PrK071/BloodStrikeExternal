import runpy,json,hashlib,zlib,re
from pathlib import Path
OUT=Path(__file__).parent;lib=runpy.run_path(str(OUT/'03-static-marshal.py'));Reader=lib['Reader'];safe=lib['safe'];INSTALL=lib['INSTALL']
ops={int(n):name for name,n in re.findall(r'^#define\s+(\w+)\s+(\d+)\s*$',(OUT/'cpython314-Include_opcode_ids.h').read_text(),re.M) if name not in {'HAVE_ARGUMENT','MIN_SPECIALIZED_OPCODE','MIN_INSTRUMENTED_OPCODE'}}
meta=(OUT/'cpython314-Include_internal_pycore_opcode_metadata.h').read_text().split('const uint8_t _PyOpcode_Caches[256] = {')[1].split('};')[0]
caches={name:int(n) for name,n in re.findall(r'\[(\w+)\]\s*=\s*(\d+)',meta)}
def instructions(words):
 out=[];i=0;ext=0
 while i<len(words):
  w=words[i];op=w['opcode'];name=ops.get(op)
  if name is None:raise ValueError('unknown opcode '+str(op))
  arg=(ext<<8)|w['arg_byte'];count=caches.get(name,0)
  if i+count>=len(words):raise ValueError('cache bounds')
  cachewords=words[i+1:i+1+count]
  if any(w['opcode']!=0 or w['arg_byte']!=0 for w in cachewords):raise ValueError('nonzero baseline inline cache')
  out.append({'offset':i*2,'opcode':op,'opname':name,'arg':arg,'cache_words':count})
  ext=arg if name=='EXTENDED_ARG' else 0;i+=1+count
 if ext:raise ValueError('trailing EXTENDED_ARG')
 return out
def main():
 initial=json.loads((OUT/'marshal-static-results.json').read_text());summary=[]
 for row in initial:
  for c in row.get('codes',[]):
   try:ins=instructions(c['wordcode']);summary.append({'index':row['index'],'name':c['qualname'],'status':'CACHE_AND_OPCODE_PASS','instructions':len(ins)})
   except Exception as e:summary.append({'index':row['index'],'name':c['qualname'],'status':'REJECT','error':str(e)})
 (OUT/'initial-opcode-validation.json').write_text(json.dumps(summary,indent=2))
 proof=json.loads((OUT.parent/'assets'/'script-candidate-index.json').read_text());results=[]
 for row in proof['results']:
  if row['index'] not in [143510,25281,68957,17226]:continue
  p=INSTALL/('Resources'+('' if row['package']==0 else str(row['package']))+'.mpk')
  with p.open('rb') as f:f.seek(row['offset']);b=f.read(row['size'])
  assert hashlib.sha256(b).hexdigest()==row['compressed_sha256'];size=len(b);b=bytearray(b);prefix=min(128-((size-8)%37),size)
  for j in range(prefix):b[j]^=0x9a
  dec=zlib.decompressobj();data=dec.decompress(bytes(b[:size if prefix==size else size-8]),4194305);assert dec.eof and not dec.unused_data and len(data)<=4194304
  assert hashlib.sha256(data).hexdigest()==row['decoded_sha256'];r=Reader(data);root=r.obj();assert r.p==len(data)
  codes=[]
  for c in r.codes:
   cb=c['code'];assert len(cb)%2==0
   words=[{'opcode':cb[i],'arg_byte':cb[i+1]} for i in range(0,len(cb),2)];ins=instructions(words)
   cc={k:safe(v) for k,v in c.items() if k not in ['consts','linetable','exceptiontable']};cc['consts']=[safe(v) if not isinstance(v,dict) or v.get('kind')!='code' else {'code_ref_offset':v['marshal_offset'],'name':v['name']} for v in c['consts']];cc['instructions']=ins;codes.append(cc)
  results.append({'index':row['index'],'decoded_sha256':row['decoded_sha256'],'header8':data[:8].hex(' '),'consumed_bytes':r.p,'status':'PARSED_TO_EOF_AND_OPCODE_PASS','code_count':len(codes),'codes':codes})
 (OUT/'selected-models-static.json').write_text(json.dumps(results,indent=2));print('INITIAL CODES',len(summary),'REJECTS',sum(x['status']=='REJECT' for x in summary));print([(r['index'],r['code_count']) for r in results])

if __name__=='__main__':main()
