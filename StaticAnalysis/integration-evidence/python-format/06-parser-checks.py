from pathlib import Path
import runpy,json,struct
OUT=Path(__file__).parent;Reader=runpy.run_path(str(OUT/'03-static-marshal.py'))['Reader']
tests=[]
for name,b in [('truncated_code',b'c'+b'\x00'*10),('invalid_reference',b'r'+struct.pack('<i',99)),('negative_length',b's'+struct.pack('<i',-1)),('excess_length',b's'+struct.pack('<i',5000000)),('unknown_tag',b'?')]:
 try:Reader(b'\x00'*8+b).obj();tests.append({'test':name,'status':'UNEXPECTED_ACCEPT'})
 except (ValueError,IndexError,struct.error) as e:tests.append({'test':name,'status':'REJECTED_AS_EXPECTED','error':str(e)})
r=Reader(b'\x00'*8+b')\x02i'+struct.pack('<i',42)+b'z\x03abc');v=r.obj();assert v==[42,'abc'];tests.append({'test':'typed_data_control','status':'PASS'})
decoder=runpy.run_path(str(OUT/'05-opcodes-selected.py'))
assert decoder['ops'][43]=='WITH_EXCEPT_START'
assert decoder['ops'][129]=='BINARY_OP_ADD_FLOAT'
assert decoder['ops'][234]=='INSTRUMENTED_END_FOR'
assert decoder['instructions']([{'opcode':43,'arg_byte':0}])[0]['opname']=='WITH_EXCEPT_START'
tests.append({'test':'opcode_markers_excluded_43_129_234','status':'PASS'})
(OUT/'parser-negative-tests.json').write_text(json.dumps(tests,indent=2));print(tests)
