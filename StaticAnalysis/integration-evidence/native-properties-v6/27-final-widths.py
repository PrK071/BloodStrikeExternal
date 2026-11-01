exec((__import__('pathlib').Path(__file__).parent/'01-names.py').read_text().split('O=')[0])
O=Path(__file__).parent;out={}
for r in [0x547b240,0x4eeb3e4,0x4eeac18,0x4eeb060,0x4eeac58]:
 off=pe.offset(r,32);out[hex(r)]={'bytes32':pe.d[off:off+32].hex(' '),'qwords':[hex(v) for v in pe.unpack('<4Q',r)],'string':pe.string(r)}
(O/'type-names-and-size-constant.json').write_text(json.dumps(out,indent=2));print(out['0x547b240']);print([(hex(r),pe.string(r)) for r in [0x4eeb3e4,0x4eeac18,0x4eeb060,0x4eeac58]])
