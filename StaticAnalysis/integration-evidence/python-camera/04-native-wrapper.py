exec((__import__('pathlib').Path(__file__).parent/'02-native-names.py').read_text().split('res=[]')[0])
out=Path(__file__).parent;res={}
for r in [0x1d87570,0x1d87a90,0x1d880c0,0x1d84e70]:
 res[hex(r)]=[pe.row(i) for i in pe.decode(r)]
 print('\n',hex(r));print('\n'.join(x['rva']+' '+x['text'] for x in res[hex(r)]))
(out/'native-wrapper-code.json').write_text(json.dumps(res,indent=2))
