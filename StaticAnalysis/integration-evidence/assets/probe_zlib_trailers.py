# Python | probe_zlib_trailers.py | Python 3.12 standard library | static follow-up of strict-decoder rejections.
import hashlib,json,re,struct,zlib
from pathlib import Path
from index_script_candidates import read_entry,INDEX_HASH

def main():
 out=Path(__file__).parent;install=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
 index=(install/'Resources.mpkinfo').read_bytes();assert hashlib.sha256(index).hexdigest()==INDEX_HASH
 old=json.loads((out/'script-candidate-index.json').read_text());results=[]
 for error in old['errors']:
  assert error['error']=='unexpected bytes after zlib stream'
  raw,info=read_entry(install,index,error['index']);b=bytearray(raw)
  prefix=min(128-((len(b)-8)%37),len(b))
  for i in range(prefix):b[i]^=0x9a
  end=len(b) if prefix==len(b) else len(b)-8
  d=zlib.decompressobj();value=d.decompress(bytes(b[:end]),8*1048576+1)
  assert d.eof and not d.unconsumed_tail and len(value)<=8*1048576
  paths=sorted(set(x.decode('ascii') for x in re.findall(rb'(?:gclient|gserver|gcommon|common|client|engine)/[A-Za-z0-9_./-]{1,220}\.py',value)))
  results.append(dict(**info,compressed_sha256=hashlib.sha256(raw).hexdigest(),decoded_sha256=hashlib.sha256(value).hexdigest(),
   decoded_size=len(value),head=value[:32].hex(' '),filename_candidates=paths,unused_bytes=len(d.unused_data),
   unused_head=d.unused_data[:32].hex(' '),unused_sha256=hashlib.sha256(d.unused_data).hexdigest()))
 result=dict(status='ZLIB_EOF_CHECKSUM_PASS_WITH_TRAILERS',index_sha256=INDEX_HASH,entries=len(results),results=results,
  interpretation='Original index rejected these because the zlib input contains extra bytes. Valid stream CRC and EOF do not explain the trailer; decoded payload metadata is separate evidence.')
 (out/'zlib-trailer-probe.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(entries=len(results),trailer_lengths=sorted(set(x['unused_bytes'] for x in results)),
  heads=[dict(index=x['index'],head=x['head'][:24],paths=x['filename_candidates']) for x in results[:12]]),indent=2))

if __name__=='__main__':main()
