exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out=[]
for m in re.finditer(rb'[ -~]{4,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if any(t in s for t in ['prop_desc','property_desc','set_prop','regist_prop','server_hp']):out.append(dict(rva=hex(pe.rva(m.start())),string=s))
(O/'descriptor-name-literals.json').write_text(json.dumps(out,indent=2));print(json.dumps(out[:70],indent=2))
