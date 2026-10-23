# Python | verify_assets_v4.py | Python 3.12, standard library | disk-only MPK header reproduction.
import argparse, collections, hashlib, json, struct
from pathlib import Path

ROOT=Path(__file__).parent
def label(b):
 if b.startswith(b'META'):return 'META marker'
 if b.startswith(b'ZZZ4'):return 'ZZZ4 raw prefix (compressed candidate)'
 if b.startswith(b'.MES'):return '.MESSIAH model marker (4-byte prefix)'
 if b.startswith(b'\x02\x02\x02\x01'):return '02 02 02 01 resource marker'
 if b.startswith(b'BKHD'):return 'BKHD (Wwise bank marker)'
 if b.startswith(b'\xe2\x06'):return 'E2 06 prefix (encoding/compression unknown)'
 t=b.removeprefix(b'\xef\xbb\xbf').lstrip()
 if t.startswith((b'{',b'[')):return 'JSON/text-like prefix'
 if t.startswith(b'<'):return 'XML/text-like prefix'
 return 'other'

def main():
 p=argparse.ArgumentParser();p.add_argument('--install',type=Path,required=True);a=p.parse_args()
 old=json.loads((ROOT/'audit-v4/assets/payload-inventory.json').read_text())
 signatures=collections.Counter(Lua_bytecode_1b4c7561=0,shebang_2321=0,CPython_magic_then_CRCRLF=0)
 results=[]
 for reference in old:
  if 'index_file' not in reference:continue
  name=Path(reference['index_file']).stem;f=a.install/(name+'.mpkinfo');raw=f.read_bytes()
  assert hashlib.sha256(raw).hexdigest()==reference['index_sha256']
  ver,count=struct.unpack_from('<II',raw);assert ver==4 and len(raw)==8+count*24+16
  packages=collections.defaultdict(list)
  for i in range(count):
   ident,off,n,flags=struct.unpack_from('<QQII',raw,8+i*24)
   if n and not flags&1:packages[flags>>1].append((off,n))
  counts=collections.Counter();sampled=0
  for k,entries in packages.items():
   data=a.install/(name+('' if k==0 else str(k))+'.mpk')
   with data.open('rb') as h:
    for off,n in sorted(entries):
     h.seek(off);head=h.read(min(n,32));assert len(head)==min(n,32)
     counts[label(head)]+=1;sampled+=1
     signatures['Lua_bytecode_1b4c7561']+=head.startswith(b'\x1bLua')
     signatures['shebang_2321']+=head.startswith(b'#!')
     signatures['CPython_magic_then_CRCRLF']+=head[1:4]==b'\r\r\n'
  assert sampled==reference['non_directory_nonzero_entries_with_32_byte_head']
  comparison=counts.copy()
  # The delegated Resource inventory groups XML with other text-like prefixes.
  if 'XML/text-like prefix' not in reference['payload_magic_counts_normalized'] and comparison['XML/text-like prefix']:
   comparison['JSON/text-like prefix']+=comparison.pop('XML/text-like prefix')
  assert dict(comparison)==reference['payload_magic_counts_normalized'],(name,dict(comparison),reference['payload_magic_counts_normalized'])
  results.append(dict(index=f.name,sha256=reference['index_sha256'],headers=sampled,prefix_counts=dict(counts),
   comparison_note='Resources text-like group from delegated inventory is split here into four JSON-like and one XML-like headers.'))
 expected=next(x for x in old if x.get('scope')=='signature_check')
 assert dict(signatures)==expected['signatures_tested_at_offset_0']
 result=dict(status='PASS_ASSET_HEADER_REPRODUCTION',indexes=results,headers=sum(r['headers'] for r in results),
  signatures_at_offset_zero=dict(signatures),maximum_payload_bytes_read=32,
  limits='Reproduces candidate header counts only; does not execute, decompress, or search payload interiors; not proof of script absence.')
 (ROOT/'audit-v4/assets/header-reproduction.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='indexes'},indent=2))

if __name__=='__main__':main()
