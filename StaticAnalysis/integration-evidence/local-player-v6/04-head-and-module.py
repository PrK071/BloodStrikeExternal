exec((__import__('pathlib').Path(__file__).parent/'01-runtime-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent
targets={0x925f328,0x925f330,0x7a1b1f0};refs=[]
for s in pe.sections:
 if not s['flags']&0x20000000:continue
 data=pe.d[s['raw_offset']:s['raw_offset']+s['raw_size']]
 for m in re.finditer(rb'[\x48\x4c][\x8b\x8d\x89][\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',data,re.S):
  r=s['rva']+m.start();t=r+7+struct.unpack_from('<i',m.group(),3)[0]
  if t not in targets:continue
  f=pe.function(r)
  if not f:continue
  ins=next((i for i in pe.decode(f[0]) if i.ip-pe.base==r),None)
  if not ins or not ins.is_ip_rel_memory_operand or ins.ip_rel_memory_address-pe.base!=t:continue
  rows=[pe.row(i) for i in pe.decode(f[0])]
  refs.append(dict(target=hex(t),instruction=hex(r),function=hex(f[0]),rows=rows))
  print(hex(t),hex(f[0]),len(rows))
table=pe.unpack('<96Q',0x925f000)
fields=['cookie','version','free_threaded','runtime.size','runtime.finalizing','runtime.interpreters_head','interpreter.size','interpreter.id','interpreter.next','interpreter.threads_head','interpreter.threads_main','interpreter.gc','interpreter.imports_modules','interpreter.sysdict','interpreter.builtins','interpreter.ceval_gil','interpreter.gil_runtime_state','interpreter.gil_runtime_state_enabled','interpreter.gil_runtime_state_locked','interpreter.gil_runtime_state_holder','interpreter.code_object_generation','interpreter.tlbc_generation','thread.size','thread.prev','thread.next','thread.interp']
out=dict(refs=refs,section=pe.section(0x925f000),debug_offsets={f:dict(table_rva=hex(0x925f000+i*8),value=hex(table[i]),bytes=struct.pack('<Q',table[i]).hex(' ')) for i,f in enumerate(fields)},module_type=dict(rva='0x7a1b1f0',qwords=[hex(x) for x in pe.unpack('<8Q',0x7a1b1f0)]))
(O/'head-and-module.json').write_text(json.dumps(out,indent=2))
