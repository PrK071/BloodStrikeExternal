"""Parse disk bytecode as data; do not marshal.loads/import/execute target code."""
from pathlib import Path
import json,runpy,hashlib
O=Path(__file__).parent;EV=O.parent
tables=json.loads((O/'opcode-tables.json').read_text());ids=tables['ids'];deopt=tables['_PyOpcode_Deopt']['values'];caches=tables['_PyOpcode_Caches']['values']
valid={v for k,v in ids.items() if 0<=v<256 and k not in {'HAVE_ARGUMENT','MIN_SPECIALIZED_OPCODE','MIN_INSTRUMENTED_OPCODE'}}
def canonical(raw):
 if len(raw)%2 or not 0<len(raw)<=65536:raise ValueError('bounded nonempty wordcode required')
 out=[];i=0;ext=0;extensions=0
 while i<len(raw):
  op,byte=raw[i:i+2]
  if op not in valid or op==ids['CACHE'] or op>=ids['MIN_INSTRUMENTED_OPCODE'] or op==ids['ENTER_EXECUTOR']:
   raise ValueError('unknown/cache/instrumented/executor instruction unsupported')
  base=deopt[op]
  if base not in valid or base==ids['CACHE']:raise ValueError('invalid deopt target')
  arg=(ext<<8)|byte;count=caches[base]
  if i+2*(1+count)>len(raw):raise ValueError('cache words exceed code length')
  out.append([i,base,arg])
  if base==ids['EXTENDED_ARG']:
   extensions+=1
   if extensions>3:raise ValueError('extended argument overflow')
   ext=arg
  else:ext=0;extensions=0
  i+=2*(1+count)
 if extensions:raise ValueError('trailing EXTENDED_ARG')
 return out

def main():
 idx=json.loads((EV/'assets/script-candidate-index.json').read_text());r=next(x for x in idx['results'] if x['index']==108818)
 path=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')/('Resources'+('' if r['package']==0 else str(r['package']))+'.mpk')
 with path.open('rb') as f:f.seek(r['offset']);raw=f.read(r['size'])
 assert hashlib.sha256(raw).hexdigest()==r['compressed_sha256']
 decode=runpy.run_path(str(EV/'assets/index_script_candidates.py'))['decode_payload'];data=decode(raw,8388608)
 assert hashlib.sha256(data).hexdigest()==r['decoded_sha256']
 Reader=runpy.run_path(str(EV/'python-format/03-static-marshal.py'))['Reader'];rd=Reader(data);rd.obj();assert rd.p==len(data)
 c=next(c for c in rd.codes if c['qualname']=='IGameLogicBase.IsEnemy');code=c['code'];canonical_code=canonical(code)
 mutated=bytearray(code);specialized=[]
 for offset,base,arg in canonical_code:
  alternatives=[op for op in valid if deopt[op]==base and op!=base and op<ids['MIN_INSTRUMENTED_OPCODE']]
  if alternatives:
   mutated[offset]=min(alternatives);specialized.append(dict(offset=offset,base=base,specialized=min(alternatives)))
  for p in range(offset+2,offset+2*(1+caches[base])):mutated[p]=0xa5
 assert canonical(mutated)==canonical_code
 rejections=[]
 for opcode in [ids['ENTER_EXECUTOR'],ids['INSTRUMENTED_RESUME'],ids['CACHE']]:
  altered=bytearray(code);altered[0]=opcode
  try:canonical(altered)
  except ValueError:rejections.append(opcode)
  else:raise AssertionError('unsupported opcode accepted')
 encoded=json.dumps(canonical_code,separators=(',',':')).encode('ascii')
 out=dict(index=108818,compressed_sha256=r['compressed_sha256'],decoded_sha256=r['decoded_sha256'],filename=c['filename'],qualname=c['qualname'],
  code_bytes=len(code),code_units=len(code)//2,code_sha256=hashlib.sha256(code).hexdigest(),code_hex=code.hex(' '),
  canonical_format='UTF-8 JSON compact array [[byte_offset,base_opcode,combined_argument],...] with separators comma/colon and no final newline',
  canonical=canonical_code,canonical_sha256=hashlib.sha256(encoded).hexdigest(),
  required_semantic_fields={k:(dict(hex=c[k].hex(' ')) if isinstance(c[k],bytes) else c[k]) for k in ['argcount','posonlyargcount','kwonlyargcount','stacksize','flags','names','consts','localsplusnames','localspluskinds','exceptiontable'] if k in c},
  synthetic_checks=dict(all_available_specializations_and_nonzero_cache_payload_preserve_fingerprint=specialized,unsupported_opcodes_rejected=rejections),
  execution='target bytecode parsed as data only; no target code execution',
  warning='canonical opcode hash alone is insufficient: compare names/constants/signature/closure/defaults and reject custom descriptor or unsupported dispatch resolution')
 (O/'baseline-is-enemy.json').write_text(json.dumps(out,indent=2));print(out['canonical_sha256'],out['code_units'],len(canonical_code),len(specialized));print(out['required_semantic_fields'])

if __name__=='__main__':main()
