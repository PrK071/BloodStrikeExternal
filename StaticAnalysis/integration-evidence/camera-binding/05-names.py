exec((__import__('pathlib').Path(__file__).parent/'04-native-bindings.py').read_text().split('O=')[0])
O=Path(__file__).parent
rs=[]
for m in re.finditer(rb'[ -~]{4,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if s.endswith('.Camera') or ('Gameplay' in s and 'Get' in s):rs.append(dict(rva=hex(pe.rva(m.start())),string=s))
(O/'native-player-camera-names.json').write_text(json.dumps(rs,indent=2));print(rs)
print('GETGAMEPLAY CONTEXT',pe.d[pe.offset(0x5bb9e18)-64:pe.offset(0x5bb9e18)+128])

