# Python | ExternalCore/render_camera.py | Python 3.12+ | pinned MainRenderViewport camera input acquisition.
"""Read the native render input, without virtual calls or matrix conventions.

The returned matrix is a projection matrix, not a combined view-projection.
No final pixel mapping, jitter/scaling equivalence or temporal freshness is implied.
Evidence: integration-evidence/camera-v7/effective-camera-contract.json.
"""
from dataclasses import dataclass
import math
import struct

from .memory import read_exact
from .registry import _pointer

RENDER_STATE_RVA=0x80F3840
SCENE_CLIENT_VPTR=0x4E632F0
MAIN_VIEWPORT_VPTR=0x52F0498
CAMERAS={0x4EC0658:('aurora',0x6B4),0x4EBF848:('perspective',0x2D8),
         0x4EBFAA0:('orthographic',None)}


@dataclass(frozen=True,slots=True)
class RenderCamera:
    state: int
    client: int
    viewport: int
    camera: int
    kind: str
    width: int
    height: int
    projection: tuple[float,...] | None
    source_copy_matched: bool
    projection_convention: str = 'unresolved_native_projection_only'
    presented_pixels_validated: bool = False


def render_camera_pass(reader,module,*,source_camera=None):
    trace=[]
    def read(address,size):
        raw=read_exact(reader,address,size);trace.append((address,raw));return raw
    def pointer(address,label):return _pointer(struct.unpack('<Q',read(address,8))[0],label)
    def expect(obj,rva,label):
        if struct.unpack('<Q',read(obj,8))[0]!=module.address(rva):
            raise ValueError(f'unsupported {label} vptr')
    state=pointer(module.address(RENDER_STATE_RVA,8),'render state')
    client=pointer(state+8,'scene viewport client');expect(client,SCENE_CLIENT_VPTR,'scene client')
    viewport=pointer(client+0x18,'main render viewport');expect(viewport,MAIN_VIEWPORT_VPTR,'main viewport')
    if pointer(viewport+0x740,'viewport provider')!=client:
        raise ValueError('main viewport provider alias disagrees')
    camera=pointer(viewport+0x50,'effective render camera')
    if camera!=client+0x80:raise ValueError('main viewport camera alias disagrees')
    vptr=struct.unpack('<Q',read(camera,8))[0]
    matches=[case for rva,case in CAMERAS.items() if vptr==module.address(rva)]
    if len(matches)!=1:raise ValueError('unsupported effective render camera vptr')
    kind,offset=matches[0]
    width,height=struct.unpack('<2H',read(viewport+0x18,4))
    if not 1<=width<=8192 or not 1<=height<=8192:raise ValueError('invalid render viewport dimensions')
    projection=None
    if offset is not None:
        projection=struct.unpack('<16f',read(camera+offset,64))
        if not all(math.isfinite(value) for value in projection):raise ValueError('nonfinite render projection')
    copied=False
    if source_camera is not None:
        _pointer(source_camera,'source ICamera')
        ortho=read(source_camera+0x418,1)[0]
        aurora=read(source_camera+0x450,1)[0]
        selected='aurora' if aurora else 'orthographic' if ortho else 'perspective'
        if selected!=kind:raise ValueError('source and render camera modes disagree')
        if struct.unpack('<2H',read(source_camera+0x408,4))!=(width,height):
            raise ValueError('source and main render viewport dimensions disagree')
        if read(source_camera+0x41C,48)!=read(client+0xEE0,48):
            raise ValueError('render camera source view copy differs')
        copied=True
    return RenderCamera(state,client,viewport,camera,kind,width,height,projection,copied),tuple(trace)
