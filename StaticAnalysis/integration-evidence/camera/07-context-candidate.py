exec((__import__('pathlib').Path(__file__).parent/'01-callers.py').read_text().split('res=[]')[0])
rr=rows(0x7593e0);save('context-candidate-7593e0.json',rr)
for x in rr:
 if int(x['rva'],16)<0x759440 or 0x759480<int(x['rva'],16)<0x759590:print(x['rva'],x['text'],x.get('rip_target_string') or '')
