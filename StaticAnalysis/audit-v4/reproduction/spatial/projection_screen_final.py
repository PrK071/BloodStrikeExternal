exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'projection';v,a=pe.unpack('<QQ',0x4f6a0c8);r=v-pe.base;rows=[pe.row(i) for i in pe.decode(r)];res={'cell_rva':'0x4f6a0c8','bytes':struct.pack('<QQ',v,a).hex(' '),'target_rva':hex(r),'adjustment':a,'instructions':rows};(out/'screen-getter-concrete.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
