from pathlib import Path
import urllib.request,hashlib,json
out=Path(__file__).parent;res=[]
for rel in ['Python/marshal.c','Include/opcode_ids.h','Include/internal/pycore_magic_number.h','Include/internal/pycore_opcode_metadata.h','Lib/importlib/_bootstrap_external.py']:
 u='https://raw.githubusercontent.com/python/cpython/v3.14.0/'+rel
 try:
  d=urllib.request.urlopen(u,timeout=30).read();name='cpython314-'+rel.replace('/','_');(out/name).write_bytes(d);res.append({'url':u,'file':name,'sha256':hashlib.sha256(d).hexdigest()})
 except Exception as e:res.append({'url':u,'error':str(e)})
(out/'primary-sources.json').write_text(json.dumps(res,indent=2));print(res)
