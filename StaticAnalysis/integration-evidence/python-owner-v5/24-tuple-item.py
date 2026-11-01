exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x7a15170,0x7a18ce0]:
 out[hex(r)]={'name':pe.string(pe.unpack('<Q',r+0x18)[0]-pe.base),'header_qwords':[hex(x) for x in pe.unpack('<6Q',r)],'flags':hex(pe.unpack('<Q',r+0xa8)[0])}
m=pe.unpack('<Q',0x7a18ce0+0x68)[0]-pe.base;f=pe.unpack('<Q',m+0x18)[0]-pe.base
out['tuple_sq_item']={'sequence_rva':hex(m),'function_rva':hex(f),'rows':[pe.row(i) for i in pe.decode(f)]}
(O/'tuple-type-and-item.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='tuple_sq_item'},indent=2));print('\n'.join(x['rva']+' '+x['text'] for x in out['tuple_sq_item']['rows'][:45]))
