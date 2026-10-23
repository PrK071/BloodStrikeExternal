# Python | probe_wrapped_zlib.py | Python 3.12 standard library | bounded disk-only payload decoding.
import contextlib,hashlib,json,re,struct,zlib
from pathlib import Path
INSTALL=Path(r'E:\SteamLibrary\steamapps\common\BLOODSTRIKE')
OUT=Path(__file__).parent
SOURCE='https://raw.githubusercontent.com/fangfang1984/netease-messiah-tools/main/mpk/src/lib.rs'
MAX_INPUT=65536;MAX_OUTPUT=4*1024*1024;SAMPLES=32

def main():
 index=(INSTALL/'Resources.mpkinfo').read_bytes()
 expected='bb3782da03b95d66451a598add8fe0923405be0dde53a8844b2f8bc107a6ced3'
 assert hashlib.sha256(index).hexdigest()==expected
 version,count=struct.unpack_from('<II',index);assert version==4
 candidates=[];results=[]
 with contextlib.ExitStack() as stack:
  packages={}
  for i in range(count):
   ident,off,size,flags=struct.unpack_from('<QQII',index,8+i*24)
   if flags&1 or not 8<=size<=MAX_INPUT:continue
   pkg=flags>>1
   if pkg not in packages:packages[pkg]=stack.enter_context((INSTALL/('Resources'+('' if pkg==0 else str(pkg))+'.mpk')).open('rb'))
   f=packages[pkg];f.seek(off);head=f.read(2)
   if head==b'\xe2\x06':candidates.append((i,ident,off,size,pkg))
  # Evenly sample the index-ordered candidates, preserving deterministic entry IDs.
  selected=[candidates[(j*(len(candidates)-1))//(min(SAMPLES,len(candidates))-1)] for j in range(min(SAMPLES,len(candidates)))] if len(candidates)>1 else candidates
  for i,ident,off,size,pkg in selected:
   f=packages[pkg];f.seek(off);original=f.read(size);assert len(original)==size
   buf=bytearray(original);prefix=min(128-((size-8)%37),size)
   for j in range(prefix):buf[j]^=0x9a
   end=size if prefix==size else size-8
   row=dict(index=i,opaque_id=hex(ident),package=pkg,offset=off,size=size,compressed_sha256=hashlib.sha256(original).hexdigest(),
    original_head=original[:16].hex(' '),transformed_head=bytes(buf[:16]).hex(' '),xor_prefix_bytes=prefix,decoder_input_bytes=end)
   try:
    decoder=zlib.decompressobj();decoded=decoder.decompress(bytes(buf[:end]),MAX_OUTPUT+1)
    assert len(decoded)<=MAX_OUTPUT and decoder.eof and not decoder.unconsumed_tail
    row.update(status='ZLIB_EOF_CHECKSUM_PASS',decoded_size=len(decoded),decoded_sha256=hashlib.sha256(decoded).hexdigest(),
     decoded_head=decoded[:64].hex(' '),unused_bytes=len(decoder.unused_data),
     ascii_examples=[x.decode('ascii')[:160] for x in re.findall(rb'[ -~]{8,}',decoded)[:10]],
     python_like_magic=len(decoded)>=4 and decoded[2:4]==b'\r\n')
   except Exception as e:row.update(status='DECODE_REJECTED',error=str(e))
   results.append(row)
 result=dict(source_reference=SOURCE,index_sha256=expected,source_transform_is_hypothesis_until_checksum_pass=True,
  bounded_candidate_count=len(candidates),samples=len(results),input_limit=MAX_INPUT,output_limit=MAX_OUTPUT,results=results,
  limits='No extraction or bytecode execution. Does not prove all wrapped payloads share a format, filename identity, or gameplay meaning.')
 (OUT/'wrapped-zlib-probe.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(candidates=len(candidates),samples=len(results),passes=sum(x['status']=='ZLIB_EOF_CHECKSUM_PASS' for x in results),
  heads=[dict(index=x['index'],status=x['status'],size=x.get('decoded_size'),head=x.get('decoded_head','')[:48],strings=x.get('ascii_examples',[])[:2]) for x in results]),indent=2))

if __name__=='__main__':main()
