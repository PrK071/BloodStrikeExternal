exec((__import__('pathlib').Path(__file__).parent/'01-types.py').read_text().split('O=')[0])
O=Path(__file__).parent
ids={name:int(n) for name,n in re.findall(r'^#define\s+(\w+)\s+(\d+)\s*$',(O/'Include_opcode_ids.h').read_text(),re.M)}
meta=(O/'Include_internal_pycore_opcode_metadata.h').read_text();out={}
for table in ['_PyOpcode_Caches','_PyOpcode_Deopt']:
 body=meta.split(f'const uint8_t {table}[256] = {{')[1].split('};')[0]; values=[0]*256
 for name,value in re.findall(r'\[(\w+)\]\s*=\s*(\w+)',body):values[int(name) if name.isdigit() else ids[name]]=int(value) if value.isdigit() else ids[value]
 raw=bytes(values);matches=[];p=0
 while (p:=pe.d.find(raw,p))>=0:
  matches.append(dict(rva=hex(pe.rva(p)),file_offset=hex(p),section=pe.section(pe.rva(p))['name']));p+=1
 out[table]=dict(values=values,bytes=raw.hex(' '),native_exact_matches=matches)
 print(table,matches)
out['ids']=ids
(O/'opcode-tables.json').write_text(json.dumps(out,indent=2))
