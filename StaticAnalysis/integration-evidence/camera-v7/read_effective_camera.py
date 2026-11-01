"""Reference reader for the V7 route. Reads supplied recordings only by default.

No process APIs, engine calls or input. Caller supplies an independently
validated module identity and a fresh read adapter for each observation.
Projection convention/final-pixel equivalence is deliberately not claimed.
"""
import math
import struct

PINNED_SHA256 = 'ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747'
VPTR = {'client':0x4e632f0, 'viewport':0x52f0498,
        'perspective':0x4ebf848, 'orthographic':0x4ebfaa0, 'aurora':0x4ec0658}
PROJECTION = {'perspective':0x2d8, 'aurora':0x6b4}

def capture_effective_camera(reader_factory, module):
    if module.sha256 != PINNED_SHA256:
        raise ValueError('unsupported module identity')
    def once():
        reader = reader_factory()
        observations = []
        def raw(address,size):
            if type(address) is not int or address < 0x10000 or address+size > 1<<47:
                raise ValueError('invalid user address')
            value = bytes(reader.read(address,size))
            if len(value)!=size: raise ValueError('short recording read')
            observations.append((address,value))
            return value
        def pointer(address):
            value,=struct.unpack('<Q',raw(address,8))
            if not 0x10000 <= value < 1<<47 or value&7:
                raise ValueError('null, unaligned or noncanonical pointer')
            return value
        def exact_type(address,label):
            if pointer(address) != module.address(VPTR[label],8):
                raise ValueError('unsupported '+label+' vptr')
        state=pointer(module.address(0x80f3840,8))
        client=pointer(state+8);exact_type(client,'client')
        viewport=pointer(client+0x18);exact_type(viewport,'viewport')
        if pointer(viewport+0x740)!=client:raise ValueError('viewport/client alias changed')
        camera=pointer(viewport+0x50)
        if camera!=client+0x80:raise ValueError('camera is not the embedded render input')
        vptr=pointer(camera)
        kind=next((k for k in ['aurora','perspective','orthographic'] if vptr==module.address(VPTR[k],8)),None)
        if kind not in PROJECTION:raise ValueError('unsupported stored projection type')
        width,height=struct.unpack('<HH',raw(viewport+0x18,4))
        if not 1<=width<=8192 or not 1<=height<=8192:raise ValueError('unsupported viewport dimensions')
        projection=struct.unpack('<16f',raw(camera+PROJECTION[kind],64))
        if not all(map(math.isfinite,projection)):raise ValueError('nonfinite projection')
        return dict(state=state,client=client,viewport=viewport,camera=camera,
                    native_type=kind,width=width,height=height,projection=projection,
                    final_pixel_convention_validated=False), observations
    first,before=once();second,after=once()
    if before!=after:raise ValueError('effective camera changed across observations')
    return second
