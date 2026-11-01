exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
for m in re.finditer(rb'[ -~]{4,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if any(t in s for t in ['initProperty','init_property','getProperty','regist_class','asiocore.','PropContainer','EntityProperty']):out.append(dict(rva=hex(pe.rva(m.start())),string=s))
(O/'property-literals.json').write_text(json.dumps(out,indent=2));print(json.dumps(out[:95],indent=2))
rows=[pe.row(i) for i in pe.decode(0x5a0f10)];(O/'regist-class.json').write_text(json.dumps(rows,indent=2));print('\n'.join(x['rva']+' '+x['text'] for x in rows[:100]))
