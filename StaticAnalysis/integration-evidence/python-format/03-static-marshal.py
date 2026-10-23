"""Bounded marshal data parser: no marshal.loads, CodeType, import, eval, or target execution."""
import struct,json,hashlib,zlib,re
from pathlib import Path
OUT=Path(__file__).parent;INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
class Reader:
 def __init__(self,b):self.b=b;self.p=8;self.refs=[];self.nodes=0;self.codes=[]
 def take(self,n):
  if n<0 or n>4*1024*1024 or self.p+n>len(self.b):raise ValueError('bounds')
  v=self.b[self.p:self.p+n];self.p+=n;return v
 def i(self):return struct.unpack('<i',self.take(4))[0]
 def obj(self,depth=0):
  self.nodes+=1
  if depth>150 or self.nodes>500000:raise ValueError('budget')
  start=self.p;t=self.take(1)[0];flag=t&128;t=chr(t&127);idx=None
  if flag:idx=len(self.refs);self.refs.append(None)
  def sub():return self.obj(depth+1)
  if t=='r':
   n=self.i()
   if not 0<=n<len(self.refs) or self.refs[n] is None:raise ValueError('bad ref')
   return self.refs[n]
  if t=='0':return NULL
  if t in 'NFTS.':v={'N':None,'F':False,'T':True,'S':{'special':'StopIteration'},'.':{'special':'Ellipsis'}}[t]
  elif t=='i':v=self.i()
  elif t=='I':v=struct.unpack('<q',self.take(8))[0]
  elif t=='l':
   n=self.i();v=sum(struct.unpack('<H',self.take(2))[0]<<(15*j) for j in range(abs(n)));v=-v if n<0 else v
  elif t in 'g':v=struct.unpack('<d',self.take(8))[0]
  elif t=='y':v={'complex':list(struct.unpack('<dd',self.take(16)))}
  elif t in 'f':v=float(self.take(self.take(1)[0]))
  elif t in 'sutaAzZ':
   n=self.take(1)[0] if t in 'zZ' else self.i();b=self.take(n);v=b if t=='s' else b.decode('utf8' if t in 'ut' else 'ascii')
  elif t in '()[<>':
   n=self.take(1)[0] if t==')' else self.i()
   if n<0 or n>100000:raise ValueError('container budget')
   v=[]
   if idx is not None:self.refs[idx]=v
   v.extend(sub() for _ in range(n))
  elif t=='{':
   v=[]
   if idx is not None:self.refs[idx]=v
   while True:
    k=sub()
    if k is NULL:break
    v.append([k,sub()])
  elif t==':':v={'slice':[sub(),sub(),sub()]}
  elif t=='c':
   v={'kind':'code','marshal_offset':start}
   if idx is not None:self.refs[idx]=v
   for k in ['argcount','posonlyargcount','kwonlyargcount','stacksize','flags']:v[k]=self.i()
   for k in ['code','consts','names','localsplusnames','localspluskinds','filename','name','qualname']:v[k]=sub()
   v['firstlineno']=self.i();v['linetable']=sub();v['exceptiontable']=sub();v['marshal_end']=self.p;self.codes.append(v)
   if not isinstance(v['code'],bytes) or not isinstance(v['names'],list) or not all(isinstance(x,str) for x in v['names']):raise ValueError('code field types')
  else:raise ValueError(f'unsupported tag {t!r} at {start}')
  if idx is not None:self.refs[idx]=v
  return v
NULL=object()
def safe(v):
 if isinstance(v,bytes):return {'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest(),'head_hex':v[:80].hex(' ')}
 if isinstance(v,list):return [safe(x) for x in v]
 if isinstance(v,dict):return {k:safe(x) for k,x in v.items()}
 return v

def main():
 proof=json.loads((OUT.parent/'assets'/'wrapped-zlib-probe.json').read_text());results=[]
 optext=(OUT/'cpython314-Include_opcode_ids.h').read_text();ops={int(n):name for name,n in re.findall(r'^#define\s+(\w+)\s+(\d+)\s*$',optext,re.M) if name not in {'HAVE_ARGUMENT','MIN_SPECIALIZED_OPCODE','MIN_INSTRUMENTED_OPCODE'}}
 for row in proof['results']:
  try:
   p=INSTALL/('Resources'+('' if row['package']==0 else str(row['package']))+'.mpk')
   with p.open('rb') as f:f.seek(row['offset']);original=f.read(row['size'])
   assert hashlib.sha256(original).hexdigest()==row['compressed_sha256']
   b=bytearray(original);prefix=row['xor_prefix_bytes']
   for j in range(prefix):b[j]^=0x9a
   dec=zlib.decompressobj();data=dec.decompress(bytes(b[:row['decoder_input_bytes']]),4194305);assert dec.eof and len(data)<=4194304
   assert hashlib.sha256(data).hexdigest()==row['decoded_sha256']
   reader=Reader(data);root=reader.obj();assert reader.p==len(data)
   codes=[]
   for c in reader.codes:
    cb=c['code'];assert len(cb)%2==0
    cr={k:safe(v) for k,v in c.items() if k not in ['consts','linetable','exceptiontable']}
    cr['consts_summary']=[safe(v) if not isinstance(v,dict) or v.get('kind')!='code' else {'code_ref_offset':v['marshal_offset'],'name':v['name']} for v in c['consts']]
    cr['wordcode']=[{'offset':i,'opcode':cb[i],'opname_314':ops.get(cb[i],'UNKNOWN'),'arg_byte':cb[i+1]} for i in range(0,len(cb),2)]
    codes.append(cr)
   result={'index':row['index'],'status':'PARSED_TO_EOF','header8':data[:8].hex(' '),'decoded_sha256':row['decoded_sha256'],'bytes':len(data),'nodes':reader.nodes,'code_count':len(codes),'codes':codes};results.append(result)
  except Exception as e:results.append({'index':row['index'],'status':'REJECTED','error':str(e)})
 (OUT/'marshal-static-results.json').write_text(json.dumps(results,indent=2,ensure_ascii=True));print(json.dumps([{'index':x['index'],'status':x['status'],'code_count':x.get('code_count'),'error':x.get('error')} for x in results]))
if __name__=='__main__':main()
