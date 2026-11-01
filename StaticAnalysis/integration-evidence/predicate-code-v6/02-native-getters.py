exec((__import__('pathlib').Path(__file__).parent/'01-types.py').read_text().split('O=')[0])
O=Path(__file__).parent
out={}
for r in [0x2a19c60,0x2a19cb0,0x2a19e70,0x2a19f10,0x2b23240]:
 rows=[pe.row(i) for i in pe.decode(r)];out[hex(r)]=rows
 print(hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:100]))
j=json.loads((O.parent/'local-player-v6'/'head-and-module.json').read_text())
fields=['size','filename','name','qualname','linetable','firstlineno','argcount','localsplusnames','localspluskinds','co_code_adaptive','co_tlbc']
# code_object begins after 3+3+16+9+8 uint64 fields in _Py_DebugOffsets.
start=3+3+16+9+8
debug={name:dict(rva=hex(0x925f000+(start+i)*8),value=hex(pe.unpack('<Q',0x925f000+(start+i)*8)[0])) for i,name in enumerate(fields)}
(O/'native-getters.json').write_text(json.dumps(dict(functions=out,code_debug_offsets=debug),indent=2));print(debug)
