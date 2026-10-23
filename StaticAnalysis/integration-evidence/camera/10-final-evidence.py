exec((__import__('pathlib').Path(__file__).parent/'01-callers.py').read_text().split('res=[]')[0])
vt=0x4e549a8;col=pe.unpack('<Q',vt-8)[0]-pe.base;fields=pe.unpack('<6I',col);td=fields[3]
def blob(r,n):
 o=pe.offset(r,n);return {'rva':hex(r),'file_offset':hex(o),'bytes':pe.d[o:o+n].hex(' ')}
e={'vtable':blob(vt-8,40),'col':blob(col,24),'col_fields':fields,'type_descriptor':blob(td,64),'name':pe.string(td+16),'slot18':{'rva':hex(vt+0x18),'pointer':hex(pe.unpack('<Q',vt+0x18)[0])}}
save('vulkan-shader-rtti.json',e);print(json.dumps(e))
# Selected store candidates inspected but unlinked: preserve complete function evidence separately.
sel=[0x7593e0,0x7823b0,0xc43fb0,0xc562d0,0xc56500,0xc57650,0xc579f0,0xc610d0]
save('selected-unlinked-functions.json',{hex(r):rows(r) for r in sel})
